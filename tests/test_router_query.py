"""Router: a query after the hash path ("#/a/A0001?topic=rent_increase_limits") is never read as part of an id."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "web" / "static"
APP = (STATIC / "app.js").read_text()


def _hash_parts_src() -> str:
    m = re.search(r"function hashParts\(\) \{.*?\n\}", APP, re.S)
    assert m, "hashParts() missing from app.js"
    return m.group(0)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize(
    "hash,path,query",
    [
        ("#/a/A0001?topic=rent_increase_limits", "a/A0001", {"topic": "rent_increase_limits"}),
        ("#/check/A0023?x=1", "check/A0023", {"x": "1"}),
        ("#/check/A0023/letter?lang=es", "check/A0023/letter", {"lang": "es"}),
        ("#/rules/CA?y=2", "rules/CA", {"y": "2"}),
        ("#/changes?from=share", "changes", {"from": "share"}),
        ("#/a/A0001", "a/A0001", {}),
        ("#/", "", {}),
        ("", "", {}),
    ],
)
def test_hash_is_cut_at_the_query(hash, path, query):
    js = (
        f"const location = {{ hash: {json.dumps(hash)} }};\n{_hash_parts_src()}\n"
        "const p = hashParts(); console.log(JSON.stringify({ path: p.path, query: Object.fromEntries(p.query) }));"
    )
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == {"path": path, "query": query}


def test_route_and_views_use_the_cut_path():
    route = APP[APP.index("async function route(") :][:1200]
    assert "hashParts()" in route and 'query.get("topic")' in route and '"ce.open"' in route
    assert 'const currentView = () => { const v = hashParts().path.split("/")[0];' in APP
    assert (
        'location.hash.slice(2) : "").split("/")' not in APP
    )  # the old split that kept "?topic=" in the id
    check = (STATIC / "features" / "check.js").read_text()
    assert r"letter\/?(?:\?.*)?$" in check
