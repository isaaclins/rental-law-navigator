# Clause & Effect: design language

Two passes on 2026-10-03. First the decluttering (Isaac: "way too bloated", "looks like AI slop"): the answer first,
once, in plain words; every detail one tap away. Then Isaac's correction ("too Apple-like"): keep that thinking, but in
our own look: Instrument Serif display, Inter text, navy on warm whites (america.gov-inspired), the § mark.
Checklist: `~/share/hacknation/qa/anti-slop-checklist.md` (not in the repo).

## Principles
- **One question per screen.** The address page answers "which rules apply here?" with one row per topic: the topic,
  a one-line answer (`web/headlines.py`, shared with Compare and Listen), the place it comes from, and a status pill
  only when the status is unusual (unknown, starts later, exempt, no rule, no limit). "Applies" is the norm and silent.
- **Say it once.** The opened row shows only what the quote doesn't already say, then the quote with one citation line
  (citation, effective date, source link, full text), then *Why it applies* and *Changes* / *Open question*. The engine
  explanation is split into those pieces (`parseWhy` in `app.js`). Other rules of the topic sit under "Also at this
  address", collapsed.
- **Progressive disclosure:** `<details>` rows inline on every screen size. Sheets only for source texts, the rule
  table and "How we found this address".

## Identity
- **Type:** Instrument Serif (`--display`) for the wordmark, page and address titles, section titles and big numbers;
  Inter (`--font`) for everything else. Sizes: `--fs-xl` home headline, `--fs-l` page/address titles, `--fs-h2`
  section titles, 16 body, 14 secondary.
- **Colour:** ink `#000c1f` with alpha greys; navy `#002664` (`--accent`) for primary actions, the active nav item and
  focus; links `#0a3a8c`; warm surfaces `#f2f3f5` (hero) and `#fbfbfb` (footer). Status: applies green, unknown amber,
  starts later blue, pending violet, the rest slate, as tinted pills with a dot, used sparingly.
- **Header:** § tile + serif wordmark, text nav with one navy pill for the active page, search, one as-of control
  ("As of Oct 1, 2026 ▾", navy when changed, × to reset), EN/ES. Below 900 px the nav becomes a bottom tab bar.
- **Surfaces:** one level only: the topic list and the example list are white cards (radius 22, hairline + soft
  shadow); everything inside is hairline rows. No cards in cards, no icon tiles, no uppercase eyebrows.
- **Motion:** the page rises in (opacity + 10 px, 0.45 s), topic rows follow with a short stagger; opacity/transform
  only, no blur; `prefers-reduced-motion` shortens everything to ~0.
- **Chart tokens** for feature modules: `--status-in-force`, `--status-soon`, `--status-pending`, `--status-failed`,
  `--chart-grid`.

## Responsible design kept
- "Not legal advice": one line next to every set of answers ("As of Oct 1, 2026. Not legal advice.") and in the
  footer of every page, with "About this information" opening the full note.
- Every answer shows its as-of date; enacted law and "Not law" (pending, failed) are separate lists.
- "Unknown" always names the missing fact. Exempt buildings say which local rule exists and why it doesn't cover them.
- Low-confidence extractions are flagged next to the source; the method (LLM extraction, verbatim quote check,
  deterministic engine) is explained on Sources.

## `window.CE`: API for feature modules
Feature modules (`web/static/features/*`) reuse the app shell through `window.CE` instead of copying markup.
`app.js` sets it up before the first render. When everything is ready it fires `document` event `ce:ready`.
Signatures are stable (`CE.version === 1`).

| Member | What it does |
|---|---|
| `CE.renderAnswers(container, lookupResult)` | Renders the answers into `container` (element or selector): the as-of note, one row per topic (the one-line answer, its status word, details one tap away) and the separate "Not law" list for pending and failed proposals. It accepts either shape:<br>• the `/api/address/<id>` response (`{as_of, categories: [...]}`);<br>• a flat lookup `{as_of, results: [{team_rule_id, result, explanation, conflict_flag, category, title, requirement, key_value, citation, quoted_span, source_url, ...}], no_rule_findings?}`, i.e. the shape of `navigator.api.lookup()`.<br>Returns the container. |
| `CE.addRoute(name, render)` | Registers a view at `#/<name>[/<arg>]`. `render(mainEl, arg)` may be async. |
| `CE.navigate(route)` | `CE.navigate("a/A0016")` or `CE.navigate("#/changes")`. |
| `CE.toast(msg)` | Short toast at the bottom (above the mobile tab bar). |
| `CE.setAsOf("YYYY-MM-DD")` | Sets the as-of date like the header control: re-renders the view and fires `ce:asof`. `#asof` stays an `<input type="date">` with a `change` listener too. |
| `CE.openModal(title, html)` / `CE.openSearch()` | Shared dialog / ⌘K address palette. |
| `CE.api(path)` | Cached `fetch(...).json()`. |
| `CE.t(key)`, `CE.lang()`, `CE.asOf()`, `CE.fmtDate(d)` | i18n (EN/ES), current language, current as-of date, localized dates. |
| `CE.badge(result, label?)`, `CE.icons`, `CE.escape(s)` | Status word in its status colour, the SVG icon set, HTML escaping. |

Events on `document`:
- `ce:ready`
- `ce:route` (`{view, arg}`)
- `ce:asof` (`{asOf}`)
- `ce:lang` (`{lang}`)

Rules for feature markup:
- Use the shared classes: `page-head`, `block`, `group` (hairline list), `kv`, `btn` / `btn primary`, `linkish`,
  `badge st-<status>`, `addr-meta`. Old names (`pill primary|line|ghost`) still render as buttons. Use the tokens
  (`--label`, `--accent`, `--display`, `--fill`, `--warm`, `--shadow-card`), never fixed colours.
- Entry points go into the slots, as plain text links: `[data-slot="address-actions"]` (under the address header),
  `.topic-actions[data-slot="topic-actions"][data-cat=<id>]` (end of each opened topic), `[data-tour-slot="home"]`
  (under the home examples), `[data-tour-slot="footer"]` (in the footer links) and `[data-slot="changes-top"]` (top of
  Changes). No new nav items. While Listen reads a topic it sets `.topic.is-speaking` (navy rule on the left).
- Stable hooks for the tour: `data-tour="search|answer|rule|source|asof|changes|properties"`; topic rows carry
  `data-cat`, rule rows `data-rule`.
- Mobile layout lives in `mobile.css`.

## Mobile navigation (≤ 640px)
- `.tabs` becomes the fixed bottom tab bar (icons from CSS masks per `data-route`, short labels via `data-short`),
  with safe-area padding and exactly one active tab (accent icon and label).
- The header must never get `transform`, `filter`, `backdrop-filter` or `will-change`: the bar is `position: fixed`
  inside it. Its own blur lives on the bar.
- The footer and toasts get `--tabbar-h` of bottom room, so content is never covered.
