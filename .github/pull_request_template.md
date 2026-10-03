## Summary

<!-- What does this PR change, and why? One or two sentences. -->

Closes #

## How tested

<!-- Commands you ran and what you saw. CI runs the same checks. -->

- [ ] `uvx ruff check . && uvx ruff format --check .`
- [ ] `uv run --no-project --with jsonschema python scripts/validate_outputs.py`
- [ ] `uv run python -m navigator selfcheck` (if outputs changed)
- [ ] Web app checked locally (if `web/` changed)

## Scoring impact

<!-- Which part of the challenge does this move? Module A (extraction), B (address lookup),
     C (change tracking), citations, plain-language / Spanish view, demo. Before/after numbers
     from the selfcheck are ideal (e.g. "T3 conflict flags 140/90 -> 90/90"). -->

## Screenshots

<!-- UI changes only. Delete this section otherwise. -->

---

- [ ] Every new rule or answer is tied to a source document and quoted span (no invented rules or citations)
- [ ] No LLM call needed to reproduce this change in CI (cached responses only)
- [ ] User-facing text still says "Not legal advice"
