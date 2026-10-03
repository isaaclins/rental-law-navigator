"""CLI: python -m navigator <command>   (Not legal advice.)"""

from __future__ import annotations

import argparse
import sys

from .config import DEFAULT_AS_OF


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="navigator", description="Rental Housing Law Navigator (not legal advice)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="LLM rule extraction over the corpus -> output/rules.json")
    e.add_argument("--docs", nargs="*", help="only these doc ids (stage 1 only, for debugging)")
    e.add_argument(
        "--no-review", action="store_true", help="skip the per-jurisdiction consolidation pass"
    )

    v = sub.add_parser("evaluate", help="address lookups -> output/lookups.json")
    v.add_argument("--as-of", default=DEFAULT_AS_OF)
    v.add_argument("--out", default=None)

    sub.add_parser("changes", help="change tests T1-T5 (+ ingested docs) -> output/changes.json")

    n = sub.add_parser(
        "ingest-new", help="ingest a new law text file, extract it and report affected addresses"
    )
    n.add_argument("file")
    n.add_argument(
        "--jurisdiction", default=None, help='e.g. "Cambridge, MA" (default: let the model decide)'
    )
    n.add_argument("--url", default="")
    n.add_argument("--test-id", default="T6")

    lk = sub.add_parser("lookup", help="print the rules for one address id")
    lk.add_argument("address_id")
    lk.add_argument("--as-of", default=DEFAULT_AS_OF)

    sub.add_parser(
        "selfcheck", help="schema, verbatim spans, coverage matrix, T1-T5 and open questions"
    )
    sub.add_parser(
        "extend",
        help="add a jurisdiction: NAVIGATOR_EXTENSION=new_docs/<slug> -> output/extension/<slug>/",
    )
    sub.add_parser("fetch-supplementary", help="one-time polite fetch of link-only sources")
    sub.add_parser("run-all", help="extract (cached) + evaluate + changes + selfcheck")

    a = p.parse_args(argv)
    if a.cmd == "extract":
        from . import extract
        from .corpus import get_doc

        docs = [get_doc(d) for d in a.docs] if a.docs else None
        extract.run(docs=docs, review=not a.no_review and not a.docs)
    elif a.cmd == "evaluate":
        from . import evaluate

        evaluate.run(as_of=a.as_of, out=a.out)
    elif a.cmd == "changes":
        from . import changes

        changes.run()
    elif a.cmd == "ingest-new":
        from . import changes

        changes.ingest_new(a.file, jurisdiction=a.jurisdiction, url=a.url, test_id=a.test_id)
    elif a.cmd == "lookup":
        import json

        from . import api

        print(json.dumps(api.lookup(a.address_id, a.as_of), indent=1, ensure_ascii=False))
    elif a.cmd == "selfcheck":
        from . import selfcheck

        return selfcheck.run()
    elif a.cmd == "extend":
        from . import extend

        extend.run()
    elif a.cmd == "fetch-supplementary":
        from .supplementary import fetch_all

        for r in fetch_all():
            print(*r)
    elif a.cmd == "run-all":
        from . import changes, evaluate, extract, selfcheck

        extract.run()
        evaluate.run()
        changes.run()
        return selfcheck.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
