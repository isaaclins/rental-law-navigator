"""Resolve each sample address to its *legal* jurisdiction (Module B, part 1).

postal_city is the USPS mailing city, not the city whose ordinances apply.
"Van Nuys" is inside the City of Los Angeles, "Dorchester" is Boston, but a
"Los Angeles" mailing address can sit in West Hollywood or in unincorporated
county land. We therefore ask the US Census Geocoder which *incorporated place*
the address point falls in.

Pipeline (every raw response is cached under cache/geo/ so reruns are offline):
  1. Normalise street strings (ranges "1031-1035 X ST" -> "1031 X ST", unit
     suffixes, trailing dots, "AV" -> "AVE") and drop ZIPs that cannot belong to
     the postal city (the NJ extract has many wrong ZIPs, e.g. Newark + 11219).
  2. Census batch geocoder (geographies/addressbatch): coordinates for all rows.
  3. Census geographies/coordinates for every matched point: Incorporated Place,
     County, County Subdivision.
  4. Non-matches: single-line Census queries over address variants, then
     OpenStreetMap Nominatim (polite, 1 req/s, cached) -> Census coordinates.
  5. Last resort: postal_city, with a note and low confidence.

Output: data/addresses_resolved.csv = all original columns + resolution columns.
Run:   python3 geo/resolve.py            (stdlib only)
       python3 geo/resolve.py --extension new_docs/<slug>   (extension jurisdiction, docs/NEW_JURISDICTION.md:
       reads <slug>/addresses.csv, adds the cities of <slug>/jurisdiction.json to the in-scope places and writes
       output/extension/<slug>/addresses_resolved.csv)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "starter" / "data" / "sample_addresses.csv"
OUT = ROOT / "data" / "addresses_resolved.csv"
CACHE = ROOT / "cache" / "geo"

CENSUS = "https://geocoding.geo.census.gov/geocoder"
BENCHMARK = "Public_AR_Current"
VINTAGE = "Current_Current"
LAYERS = "Incorporated Places,Counties,County Subdivisions,States"
UA = "RentalHousingLawNavigator/0.1 (Hack-Nation hackathon prototype; contact via GitHub isaaclins)"

# The nine in-scope cities, keyed by (state, Census incorporated-place name).
IN_SCOPE = {
    ("CA", "Los Angeles city"): "Los Angeles",
    ("CA", "San Francisco city"): "San Francisco",  # consolidated city-county
    ("CA", "San Diego city"): "San Diego",
    ("CA", "Berkeley city"): "Berkeley",
    ("NJ", "Jersey City city"): "Jersey City",
    ("NJ", "Hoboken city"): "Hoboken",
    ("NJ", "Newark city"): "Newark",
    ("MA", "Boston city"): "Boston",
    ("MA", "Cambridge city"): "Cambridge",
}
STATE_FIPS = {"06": "CA", "34": "NJ", "25": "MA"}

# Reference data used only to judge whether a supplied ZIP is plausible for the
# postal city and to name the county when every geocoder fails.
CITY_ZIP_PREFIX = {
    ("NJ", "Hoboken"): ("07030",),
    ("NJ", "Jersey City"): ("0730", "07097", "07399"),
    ("NJ", "Newark"): ("071",),
}
STATE_ZIP_PREFIX = {"CA": ("9",), "NJ": ("07", "08"), "MA": ("01", "02")}
FALLBACK_CITY = {  # postal city -> (legal city it most likely is, county)
    ("CA", "Los Angeles"): ("Los Angeles", "Los Angeles County"),
    ("CA", "San Francisco"): ("San Francisco", "San Francisco County"),
    ("CA", "San Diego"): ("San Diego", "San Diego County"),
    ("CA", "San Ysidro"): ("San Diego", "San Diego County"),
    ("CA", "Berkeley"): ("Berkeley", "Alameda County"),
    ("NJ", "Jersey City"): ("Jersey City", "Hudson County"),
    ("NJ", "Hoboken"): ("Hoboken", "Hudson County"),
    ("NJ", "Newark"): ("Newark", "Essex County"),
    ("MA", "Cambridge"): ("Cambridge", "Middlesex County"),
}
BOSTON_NEIGHBORHOODS = {
    "Boston",
    "Allston",
    "Brighton",
    "Charlestown",
    "Dorchester",
    "East Boston",
    "Hyde Park",
    "Jamaica Plain",
    "Mattapan",
    "Roslindale",
    "Roxbury",
    "South Boston",
    "West Roxbury",
}
for _n in BOSTON_NEIGHBORHOODS:
    FALLBACK_CITY[("MA", _n)] = ("Boston", "Suffolk County")

SUFFIX_FIX = {"AV": "AVE", "BLV": "BLVD", "STR": "ST", "PKY": "PKWY"}


# ---------------------------------------------------------------- caching --
def _cache_path(kind: str, key: str, ext: str = "json") -> Path:
    h = hashlib.sha256(key.encode()).hexdigest()[:20]
    return CACHE / kind / f"{h}.{ext}"


def http_get_json(kind: str, url: str, pause: float = 0.0) -> dict | list | None:
    p = _cache_path(kind, url)
    if p.exists():
        return json.loads(p.read_text())["response"]
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            break
        except Exception as e:  # network hiccups: retry with backoff
            if attempt == 3:
                print(f"  ! GET failed {url[:100]}: {e}", file=sys.stderr)
                return None
            time.sleep(2 * (attempt + 1))
    if pause:
        time.sleep(pause)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "url": url,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "response": data,
            }
        )
    )
    return data


# ---------------------------------------------------------- normalisation --
def normalise_street(raw: str) -> str:
    s = raw.upper().strip()
    s = re.sub(r"\s+(APT|UNIT|STE|#)\s*\S+$", "", s)  # unit designators
    s = s.split("/")[0]  # "600 JACKSON/601 HARRISON"
    s = re.sub(r"\.", " ", s)  # "AVE." / "322.5"
    s = re.sub(r"^(\d+)[A-Z]?\s*(?:-|&)\s*[\d\s&-]*\s+(?=[A-Z])", r"\1 ", s)  # ranges
    s = re.sub(r"^(\d+)\s+\d+\s+(?=[A-Z])", r"\1 ", s)  # "322 5 WESTERN" left by "322-322.5"
    s = re.sub(r"\b0+(\d+(?:ST|ND|RD|TH))\b", r"\1", s)  # "05TH AV" -> "5TH AV"
    s = re.sub(r"\s+(LOT|BLDG)\s+\S+$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split(" ")
    if parts and parts[-1] in SUFFIX_FIX:
        parts[-1] = SUFFIX_FIX[parts[-1]]
    return " ".join(parts)


def street_variants(raw: str) -> list[str]:
    base = normalise_street(raw)
    out = [base]
    m = re.match(r"^(\d+)([A-Z])\s+(.*)$", base)  # "38A GAUTIER AVE"
    if m:
        out.append(f"{m.group(1)} {m.group(3)}")
    # second number of a range ("157-155 CLERK ST" -> 155)
    m = re.match(r"^\d+[A-Z]?\s*[-&]\s*(\d+)\s+(.*)$", raw.upper().replace(".", " ").strip())
    if m:
        out.append(normalise_street(f"{m.group(1)} {m.group(2)}"))
    if not re.search(
        r"\b(ST|AVE|BLVD|DR|PL|CT|RD|WAY|TER|LN|PKWY|SQ|CIR|HWY|AVENUE|STREET|BOULEVARD|DRIVE|PLACE|ROAD|COURT|TERRACE|LANE|PLAZA|ROW|PARK)$",
        base,
    ):
        out.append(base + " ST")  # "600 JACKSON" -> "600 JACKSON ST"
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def plausible_zip(row: dict) -> str:
    z = (row["zip"] or "").strip()
    if not z:
        return ""
    z = z.zfill(5)
    st, city = row["state"], row["postal_city"]
    if not z.startswith(STATE_ZIP_PREFIX[st]):
        return ""
    pref = CITY_ZIP_PREFIX.get((st, city))
    if pref and not z.startswith(pref):
        return ""
    return z


# ------------------------------------------------------------ census calls --
def census_batch(rows: list[dict]) -> dict[str, dict]:
    """POST all rows to the Census batch geocoder. Returns id -> parsed result."""
    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(
            [
                r["address_id"],
                normalise_street(r["street_address"]),
                r["postal_city"],
                r["state"],
                plausible_zip(r),
            ]
        )
    body_csv = buf.getvalue()
    p = _cache_path("batch", body_csv, "csv")
    if p.exists():
        text = p.read_text()
    else:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (("benchmark", BENCHMARK), ("vintage", VINTAGE)):
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
            )
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="addressFile"; filename="addresses.csv"\r\n'
            f"Content-Type: text/csv\r\n\r\n{body_csv}\r\n--{boundary}--\r\n"
        )
        req = urllib.request.Request(
            f"{CENSUS}/geographies/addressbatch",
            data="".join(parts).encode(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA},
        )
        print(f"  POST Census batch ({len(rows)} rows) ...", file=sys.stderr)
        with urllib.request.urlopen(req, timeout=600) as r:
            text = r.read().decode()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        p.with_suffix(".input.csv").write_text(body_csv)
    out = {}
    for rec in csv.reader(io.StringIO(text)):
        if not rec:
            continue
        rid = rec[0]
        res = {"match": rec[2] if len(rec) > 2 else "No_Match"}
        if res["match"] == "Match":
            lon, lat = rec[5].split(",")
            res.update(
                match_type=rec[3],
                matched_address=rec[4],
                lon=float(lon),
                lat=float(lat),
                state_fips=rec[8] if len(rec) > 8 else "",
                county_fips=rec[9] if len(rec) > 9 else "",
            )
        out[rid] = res
    return out


def census_coords(lon: float, lat: float) -> dict | None:
    q = urllib.parse.urlencode(
        {
            "x": f"{lon:.6f}",
            "y": f"{lat:.6f}",
            "benchmark": BENCHMARK,
            "vintage": VINTAGE,
            "layers": LAYERS,
            "format": "json",
        }
    )
    d = http_get_json("coords", f"{CENSUS}/geographies/coordinates?{q}")
    if not d or "result" not in d:
        return None
    return d["result"]["geographies"]


def census_oneline(address: str) -> dict | None:
    q = urllib.parse.urlencode(
        {
            "address": address,
            "benchmark": BENCHMARK,
            "vintage": VINTAGE,
            "layers": LAYERS,
            "format": "json",
        }
    )
    d = http_get_json("oneline", f"{CENSUS}/geographies/onelineaddress?{q}")
    if not d or "result" not in d:
        return None
    m = d["result"].get("addressMatches") or []
    return m[0] if m else None


def nominatim(street: str, city: str, state: str, street_level: bool = False) -> dict | None:
    q = urllib.parse.urlencode(
        {
            "street": street,
            "city": city,
            "state": state,
            "country": "USA",
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{q}"
    cached = _cache_path("nominatim", url).exists()
    d = http_get_json("nominatim", url, pause=0 if cached else 1.1)  # usage policy: <= 1 req/s
    if d and isinstance(d, list) and d:
        hit = d[0]
        # require a house-level hit, not a street centroid
        if hit.get("addresstype") in ("building", "place", "house") or (
            hit.get("address") or {}
        ).get("house_number"):
            return hit
        if street_level and hit.get("addresstype") in ("road", "street"):
            return hit
    return None


# ----------------------------------------------------------- interpretation --
def interpret(geos: dict, state: str) -> dict:
    places = geos.get("Incorporated Places") or []
    counties = geos.get("Counties") or []
    subdiv = geos.get("County Subdivisions") or []
    states = geos.get("States") or []
    st = STATE_FIPS.get(states[0]["GEOID"], state) if states else state
    place = places[0]["NAME"] if places else ""
    return {
        "resolved_state": st,
        "county": counties[0]["NAME"] if counties else "",
        "county_subdivision": subdiv[0]["NAME"] if subdiv else "",
        "census_place": place,
        "census_place_geoid": places[0]["GEOID"] if places else "",
        "resolved_city": IN_SCOPE.get((st, place), ""),
    }


def note_for(row: dict, info: dict, how: str) -> str:
    pc, rc = row["postal_city"], info["resolved_city"]
    if not rc:
        where = (
            info["census_place"]
            or f"unincorporated {info['county']} ({info['county_subdivision']})"
        )
        return f"{how}; point lies in {where}, outside the 9 in-scope cities, so no city ordinance applies (postal city '{pc}' is only the mailing name)"
    if rc != pc:
        return f"{how}; postal city '{pc}' is a mailing name, legal city is {rc} ({info['census_place']})"
    extra = ""
    if rc == "San Francisco":
        extra = " (consolidated City and County of San Francisco)"
    return f"{how}; inside {info['census_place']}{extra}"


def resolve() -> list[dict]:
    rows = list(csv.DictReader(SRC.open()))
    print(f"Resolving {len(rows)} addresses ...", file=sys.stderr)
    batch = census_batch(rows)

    results: dict[str, dict] = {}

    def from_point(row, lon, lat, method, conf, matched, how):
        geos = census_coords(lon, lat)
        if not geos:
            return None
        info = interpret(geos, row["state"])
        note = note_for(row, info, how)
        mm = re.search(r",\s*([A-Z][A-Z .]+),\s*[A-Z]{2},", matched or "")
        if (
            mm
            and info["resolved_city"]
            and mm.group(1).strip().title() not in (row["postal_city"], info["resolved_city"])
        ):
            note += f"; USPS name '{mm.group(1).strip().title()}' is a neighborhood of {info['resolved_city']}, same city rules"
        info.update(
            lat=round(lat, 6),
            lon=round(lon, 6),
            resolution_method=method,
            resolution_confidence=conf,
            matched_address=matched,
            resolution_note=note,
        )
        return info

    def stage_batch(row):
        b = batch.get(row["address_id"], {})
        if b.get("match") != "Match":
            return None
        conf = 0.95 if b["match_type"] == "Exact" else 0.85
        how = f"Census batch geocoder {b['match_type'].lower()} match '{b['matched_address']}'"
        return from_point(row, b["lon"], b["lat"], "census_batch", conf, b["matched_address"], how)

    def stage_oneline(row):
        zips = [plausible_zip(row), ""] if plausible_zip(row) else [""]
        for street in street_variants(row["street_address"]):
            for z in zips:
                addr = f"{street}, {row['postal_city']}, {row['state']} {z}".strip()
                m = census_oneline(addr)
                if m:
                    c = m["coordinates"]
                    how = f"Census single-line match for normalised '{addr}' -> '{m['matchedAddress']}'"
                    return from_point(
                        row, c["x"], c["y"], "census_oneline", 0.8, m["matchedAddress"], how
                    )
        return None

    def stage_osm(row):
        for street in street_variants(row["street_address"]):
            if not re.match(r"^\d", street):
                continue
            hit = nominatim(street, row["postal_city"], row["state"])
            if hit:
                label = hit.get("display_name", "")[:90]
                how = f"Census had no match; OpenStreetMap Nominatim house-level hit '{label}', place from Census coordinates"
                return from_point(
                    row,
                    float(hit["lon"]),
                    float(hit["lat"]),
                    "osm_nominatim+census_coords",
                    0.7,
                    label,
                    how,
                )
        street = normalise_street(row["street_address"])
        if not re.match(r"^\d", street):  # no house number in the source record: street-level only
            hit = nominatim(street, row["postal_city"], row["state"], street_level=True)
            if hit:
                label = hit.get("display_name", "")[:90]
                how = (
                    f"source record has no house number; OpenStreetMap street-level point '{label}' "
                    f"used, place from Census coordinates (street could cross a city line: check)"
                )
                return from_point(
                    row,
                    float(hit["lon"]),
                    float(hit["lat"]),
                    "osm_street_level+census_coords",
                    0.55,
                    label,
                    how,
                )
        return None

    def run_stage(fn, todo, workers):
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for row, res in zip(todo, ex.map(fn, todo), strict=True):
                if res:
                    results[row["address_id"]] = res

    run_stage(stage_batch, rows, 4)
    todo = [r for r in rows if r["address_id"] not in results]
    print(
        f"  batch matched {len(rows) - len(todo)}; retrying {len(todo)} with single-line variants",
        file=sys.stderr,
    )
    run_stage(stage_oneline, todo, 3)
    todo = [r for r in rows if r["address_id"] not in results]
    print(f"  {len(todo)} left; trying OpenStreetMap Nominatim (1 req/s)", file=sys.stderr)
    run_stage(stage_osm, todo, 1)

    out = []
    for row in rows:
        res = results.get(row["address_id"])
        if res is None:
            city, county = FALLBACK_CITY.get((row["state"], row["postal_city"]), ("", ""))
            res = {
                "resolved_city": city,
                "resolved_state": row["state"],
                "county": county,
                "county_subdivision": "",
                "census_place": "",
                "census_place_geoid": "",
                "lat": "",
                "lon": "",
                "resolution_method": "postal_city_fallback",
                "resolution_confidence": 0.5,
                "matched_address": "",
                "resolution_note": (
                    f"No geocoder could place '{row['street_address']}' (incomplete or misspelled street); "
                    f"assumed legal city = postal city '{row['postal_city']}'. Needs human check."
                ),
            }
        # Sanity flag: geocoded state must equal the record's state
        if res["resolved_state"] != row["state"]:
            res["resolution_note"] += (
                f"; WARNING geocoded state {res['resolved_state']} != record state {row['state']}"
            )
            res["resolution_confidence"] = min(float(res["resolution_confidence"]), 0.4)
        z = (row["zip"] or "").strip()
        if z and not plausible_zip(row):
            res["resolution_note"] += (
                f"; source ZIP {z} is not a {row['postal_city']} ZIP and was ignored"
            )
        out.append({**row, **res})
    return out


COLUMNS_EXTRA = [
    "resolved_city",
    "resolved_state",
    "county",
    "lat",
    "lon",
    "resolution_method",
    "resolution_confidence",
    "resolution_note",
    "census_place",
    "census_place_geoid",
    "county_subdivision",
    "matched_address",
]


def use_extension(ext_dir: Path) -> None:
    """Point the resolver at an extension jurisdiction's addresses and add its cities to the in-scope places."""
    global SRC, OUT
    ext = json.loads((ext_dir / "jurisdiction.json").read_text())
    for j in ext["jurisdictions"]:
        city = j["name"].split(",")[0]
        IN_SCOPE[(j["state"], j["census_place"])] = city
        for pc in j.get("postal_cities", [city]):
            FALLBACK_CITY[(j["state"], pc)] = (city, j.get("county", ""))
    SRC = ext_dir / "addresses.csv"
    OUT = ROOT / "output" / "extension" / ext_dir.name / "addresses_resolved.csv"


def main():
    if "--extension" in sys.argv:
        use_extension((ROOT / sys.argv[sys.argv.index("--extension") + 1]).resolve())
    out = resolve()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    orig = list(csv.DictReader(SRC.open()).fieldnames)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=orig + COLUMNS_EXTRA)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in orig + COLUMNS_EXTRA})

    # ---- summary
    print(f"\nWrote {OUT.relative_to(ROOT)} ({len(out)} rows)\n")
    tab = Counter(
        (r["state"], r["postal_city"], r["resolved_city"] or "(outside scope)") for r in out
    )
    print(f"{'state':5} {'postal_city':16} -> {'resolved_city':18} count")
    for (st, pc, rc), n in sorted(tab.items()):
        flag = "" if pc == rc else "   *"
        print(f"{st:5} {pc:16} -> {rc:18} {n:5}{flag}")
    print("\nPer resolved city:")
    for c, n in sorted(Counter(r["resolved_city"] or "(outside scope)" for r in out).items()):
        print(f"  {c:18} {n}")
    print("\nBy method:", dict(Counter(r["resolution_method"] for r in out)))
    outside = [r for r in out if not r["resolved_city"]]
    if outside:
        print("\nOutside the in-scope cities (no city rules):")
        for r in outside:
            print(
                f"  {r['address_id']} {r['street_address']}, {r['postal_city']} -> {r['census_place'] or 'unincorporated'} / {r['county']}"
            )
    fb = [r for r in out if r["resolution_method"] == "postal_city_fallback"]
    if fb:
        print("\nUnmatched (postal-city fallback, needs human check):")
        for r in fb:
            print(f"  {r['address_id']} {r['street_address']}, {r['postal_city']} {r['zip']}")


if __name__ == "__main__":
    main()
