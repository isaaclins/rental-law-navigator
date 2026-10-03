# Contributing

Thanks for helping build the Rental Housing Law Navigator. This is a 24-hour hackathon project, so the
process is light, but every change goes through a pull request with green checks.

> **Not legal advice.** Every user-facing surface must keep saying so.

## Workflow

1. Pick or open an issue (templates: **Feature**, **Bug**). Label it with an `area:*` and `priority:*`.
2. Branch off `main`:

   | Prefix | Use for | Example |
   |---|---|---|
   | `feat/` | new capability | `feat/spanish-view` |
   | `fix/` | wrong answer, crash, broken check | `fix/t3-conflict-flags` |
   | `ci/` | workflows, tooling | `ci/github-actions` |
   | `docs/` | README, demo script, notes | `docs/architecture` |
   | `test/` | tests, scorers | `test/qa-scorer` |
   | `chore/` | dependencies, housekeeping | `chore/bump-fastapi` |

3. Commit with [Conventional Commits](https://www.conventionalcommits.org/):
   `type(scope): summary` in the imperative, e.g.

   ```
   feat(extract): verify quoted spans against the corpus before writing rules.json
   fix(evaluate): report unknown for buildings in the certificate-of-occupancy cutoff year
   ci: add lint, validation and smoke-test workflow
   ```

   Types: `feat`, `fix`, `docs`, `test`, `ci`, `chore`, `refactor`, `perf`. Scopes follow the
   areas: `extract`, `evaluate`, `changes`, `geo`, `web`, `submission`.
4. Open a pull request to `main`. Fill in the template, including `Closes #<issue>` and the
   scoring impact. Keep PRs small and focused.
5. CI must be green before merging. Squash-merge with a Conventional Commit title.

## Checks

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs on every pull request and on every
push to `main`. Run the same checks locally before pushing:

| Check | Command | What it verifies |
|---|---|---|
| Lint | `uvx ruff check . && uvx ruff format --check .` | Style and common bugs ([`ruff.toml`](ruff.toml), line length 100). Fix with `uvx ruff check --fix . && uvx ruff format .` |
| Validate | `uv run --no-project --with jsonschema python scripts/validate_outputs.py` | `output/rules.json` records match [`rule_record.schema.json`](starter/schema/rule_record.schema.json), ids are unique, every `quoted_span` appears verbatim (whitespace-normalized) in its source document; `lookups.json` covers all 500 sample addresses with valid results; `changes.json` has T1-T5 with known address ids |
| Selfcheck | `uv run python -m navigator selfcheck` | Coverage matrix, recall against the brief, change tests T1-T5 and the known open questions |
| Web smoke | `uv run uvicorn web.app:app --port 8765` | The app starts and the main `/api/*` endpoints answer 200 |

Jobs skip (and stay green) while the part they check is not on `main` yet, e.g. the selfcheck
waits for `navigator/` and `output/rules.json`, and the validator reports missing output files as
`SKIP`. Pass `--require` to the validator to treat missing files as errors.

### No LLM calls in CI

CI must be reproducible and free. The selfcheck and web jobs run with `NAVIGATOR_OFFLINE=1`, no API
key, and stub `claude` / `codex` binaries that fail on use. The extractor reads cached model
responses only; if a change needs new extraction output, run the extractor locally and commit the
resulting `output/*.json` files, so CI validates exactly what the demo shows.

## Ground rules

- Rules come from the system reading the supplied corpus, never hand-coded; every rule carries a
  citation, a source document and a verbatim quoted span.
- Say `unknown` instead of guessing when the data does not decide coverage.
- Public data only. No secrets in the repository: API keys live in local environment variables.
- Do not edit `starter/`: it is the organizers' starter pack, copied verbatim.
