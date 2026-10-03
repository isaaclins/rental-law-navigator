"""Sample multifamily parcels for one LA County city from the public LA County eGIS parcel layer.

Same source as the starter's LA rows (source_dataset "LA County eGIS parcels"), same columns as
starter/data/sample_addresses.csv. No owner fields are requested. Two requests in total: the object ids
of the city's 5+ unit apartment parcels (use code 05xx), then the attributes of 2N evenly spaced ids, of which
N evenly spaced parcels with 5+ units (sum over the parcel's buildings, as in the starter's LA rows) are kept.

Run:  python3 geo/lacounty_parcels.py "SANTA MONICA" new_docs/santa-monica/addresses.csv --n 40 --prefix SM
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import urllib.parse
import urllib.request

LAYER = "https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0/query"
UA = "RentalHousingLawNavigator/0.1 (Hack-Nation hackathon prototype; contact via GitHub isaaclins)"
FIELDS = (
    "OBJECTID,SitusAddress,SitusCity,SitusZIP,UseCode,UseDescription,YearBuilt1,TaxRateCity,"
    + ",".join(f"Units{i}" for i in range(1, 6))
)
COLUMNS = [
    "address_id",
    "street_address",
    "postal_city",
    "state",
    "zip",
    "year_built",
    "units",
    "use_code",
    "use_description",
    "source_dataset",
    "retrieved_at",
]


def _get(params: dict) -> dict:
    url = f"{LAYER}?{urllib.parse.urlencode({**params, 'f': 'json'})}"
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60
    ) as r:
        return json.loads(r.read().decode())


def sample(tax_rate_city: str, n: int) -> tuple[list[dict], int]:
    where = f"TaxRateCity='{tax_rate_city.upper()}' AND UseCode LIKE '05%'"
    ids = sorted(_get({"where": where, "returnIdsOnly": "true"})["objectIds"])
    step = max(1, len(ids) // (2 * n))
    pick = ids[::step][: 2 * n]
    feats = _get(
        {
            "objectIds": ",".join(map(str, pick)),
            "outFields": FIELDS,
            "returnGeometry": "false",
        }
    )["features"]
    rows = sorted((f["attributes"] for f in feats), key=lambda a: a["OBJECTID"])
    for r in rows:
        r["units"] = sum(r.get(f"Units{i}") or 0 for i in range(1, 6))
    rows = [r for r in rows if r["units"] >= 5]
    return rows[:: max(1, len(rows) // n)][:n], len(ids)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tax_rate_city", help='LA County TaxRateCity value, e.g. "SANTA MONICA"')
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--prefix", default="X")
    a = ap.parse_args()
    rows, total = sample(a.tax_rate_city, a.n)
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%MZ")
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows, 1):
            city = (r.get("SitusCity") or "").removesuffix(" CA").strip().title()
            yb = (r.get("YearBuilt1") or "").strip()
            w.writerow(
                {
                    "address_id": f"{a.prefix}{i:03d}",
                    "street_address": (r.get("SitusAddress") or "").strip(),
                    "postal_city": city,
                    "state": "CA",
                    "zip": (r.get("SitusZIP") or "")[:5],
                    "year_built": yb if yb.strip("0") else "",
                    "units": r["units"],
                    "use_code": r.get("UseCode") or "",
                    "use_description": r.get("UseDescription") or "",
                    "source_dataset": "LA County eGIS parcels",
                    "retrieved_at": now,
                }
            )
    print(f"{len(rows)} of {total} parcels -> {a.out}")


if __name__ == "__main__":
    main()
