# Clause & Effect: design language

Redesigned 2026-10-03 after Isaac's review ("way too bloated", "looks like AI slop"). The goal is how Apple would
ship it: the answer first, once, in plain words; every detail one tap away; nothing decorative.
Checklist this follows: `~/share/hacknation/qa/anti-slop-checklist.md` (not in the repo).

## Principles
- **One question per screen.** The address page answers "which rules apply here?" with one row per topic: the topic,
  a one-line answer (the governing rule's key figure), the place it comes from, and a status word.
- **Say it once.** The key figure appears in the row. The opened row shows the rule in plain words, then *Source*
  (verbatim quote, citation, link, "Read in full text"), *Why it applies* (the engine's facts as bullets),
  *Changes*, *Overrides* and *Open question*. The engine explanation is split into those pieces (`parseWhy` in
  `app.js`), so no sentence is repeated. Other rules of the topic sit under "Also at this address", collapsed.
- **Progressive disclosure:** `<details>` rows inline on every screen size. Dialogs only for full source texts and the
  rule table.
- **Quiet chrome.** Header: wordmark, text links (active = semibold ink, no pill), search icon, one as-of control
  ("As of Oct 1, 2026 ▾", accent-coloured with a × reset when it is not the default), EN/ES as two words.
  Phones get a bottom tab bar instead of the links.

## Typography
System stack: `-apple-system, BlinkMacSystemFont, "SF Pro Text", InterVariable, system-ui` (Inter is bundled for
non-Apple systems). Hierarchy comes from weight, not colour. Sizes: 48 (home headline only), 32 page titles, 17 body
and rows, 14 secondary text. Phones: 34 / 28 / 17 / 14. No serif, no uppercase eyebrows, no italics for emphasis.

## Colour
| Token | Value | Use |
|---|---|---|
| `--label` / `--label-2` / `--label-3` | `#1d1d1f` / `#6e6e73` / `#8e8e93` | text, secondary text, tertiary |
| `--sep` / `--sep-2` / `--fill` | `#d2d2d7` / `#e8e8ed` / `#f5f5f7` | input borders, hairlines, footer and skeletons |
| `--accent` | `#0066cc` | links and the primary action only |
| `--applies` / `--unknown` / `--soon` / `--pending` | green / orange / indigo / purple | status words and dots only |

Status is a coloured word (`.badge.st-<result>`), never a tinted pill. Superseded, failed, no rule and exempt are grey.

## Shape, depth, spacing
Hairline rows (`.group`, `.topic`, `.kv`) instead of cards. No nested boxes. Shadows only on floating layers
(dialogs, search suggestions, the account menu). Radius 10-14px. 8-pt spacing; content column 760px, page 980px.

## Motion
Opacity and short translate only: main fades in (180 ms), dialogs rise 8px. No blur, no stagger, no count-ups, no
auto-advancing carousel, no pulsing dots. `prefers-reduced-motion` shortens every animation to ~0.

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
  `badge st-<status>`, `addr-meta`. Old names (`pill primary|line|ghost`) still render as buttons.
- Entry points go into the slots, as plain text links: `[data-slot="address-actions"]` (under the address header),
  `.topic-actions[data-slot="topic-actions"][data-cat=<id>]` (end of each opened topic), `[data-tour-slot="home"]`
  (under the home examples) and `[data-tour-slot="footer"]` (in the footer links). No new nav items.
- Stable hooks for the tour: `data-tour="search|answer|rule|source|asof|changes|properties"`; topic rows carry
  `data-cat`, rule rows `data-rule`.
- Mobile layout lives in `mobile.css`.

## Mobile navigation (≤ 640px)
- `.tabs` becomes the fixed bottom tab bar (icons from CSS masks per `data-route`, short labels via `data-short`),
  with safe-area padding and exactly one active tab (accent icon and label).
- The header must never get `transform`, `filter`, `backdrop-filter` or `will-change`: the bar is `position: fixed`
  inside it. Its own blur lives on the bar.
- The footer and toasts get `--tabbar-h` of bottom room, so content is never covered.
