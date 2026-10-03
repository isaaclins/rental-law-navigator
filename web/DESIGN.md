# Clause & Effect: design language

Visual language borrowed from **america.gov**. Interaction feel borrowed from **Luma** (luma.com).
Studied on 2026-10-03:
- america.gov: the live site serves a bot challenge to headless browsers, so we studied the Internet Archive
  snapshot of 2026-10-02. That covered desktop and mobile screenshots, 250 ms load frames, scroll frames, and the
  compiled CSS and JS (tokens, keyframes, easing).
- Luma: /zurich and an event page, captured live with Playwright.

We imitate **style, not identity**. This is not a government site, and it must never look like one:
- no seals, flags, agency badges or the "official website" banner;
- none of their photos, illustrations, logo or copy text.

The fonts are openly licensed (SIL OFL) and bundled locally in `static/fonts/`, so no CDN is used.

## Typography
| Role | america.gov | Ours (OFL) | Why |
|---|---|---|---|
| Display (H1, section titles, wordmark, big numbers) | Rhymes Display 400, tight tracking, line-height ~1 | **Instrument Serif 400** (`InstrumentSerif-*.woff2`) | High-contrast editorial serif. It gives the "civic, trustworthy, calm" voice that a grotesk alone lacks. |
| UI, body, labels | Helvetica Now Text / Display (they also ship an `--font-inter` token) | **Inter Variable** | Neutral, very legible at 13-16px, tabular numbers for dates and counts. |
| Code, ids | system mono | system mono | Rule ids and doc ids only. |

The type scale follows their fluid `clamp()` tokens:
- `--fs-hero: clamp(3rem, 2.1rem + 3.6vw, 5.5rem)`, tracking -0.035em, line-height 0.98.
- `--fs-h1: clamp(2.25rem, 1.7rem + 2.2vw, 3.75rem)`. Serif page titles.
- `--fs-h2: clamp(1.5rem, 1.3rem + .8vw, 2rem)`. Serif section titles.
- Inter body is 15-17px. Secondary text uses **alpha on the ink colour** (Luma) instead of separate grey hexes.

## Colour
Tokens are taken from their compiled CSS:
- **Ink:** `#000c1f` (their `--color-blue-900`). Text and borders are alpha mixes of it:
  - secondary `/.65`, tertiary `/.45`;
  - hairline `/.10`, quaternary `/.05`.
- **Accent:** federal navy `#002664` (`--color-blue-700`). Used for primary pills, the submit arrow, focus and the
  active nav item. Links use `#0066c5`.
- **Surfaces:**
  - the canvas is pure white;
  - the hero panel is a soft radial grey (`#f2f3f4` → white), like their `--page-top-color`;
  - muted panels are `#f7f7f7`; the footer is `#fbfbfb`.
- **Status:** these are the only other hues, and each one carries a meaning:
  - applies = green;
  - unknown = amber;
  - superseded = slate;
  - not yet effective = blue;
  - pending = violet;
  - failed = grey;
  - flagged for review = orange.

  They appear only as tinted pills with a dot (Luma's "LIVE" and "Waitlist" chips), never as large fills.

## Shape and depth
- **Corner radius:** pills are `9999px`. Cards are 20-28px. The hero panel is 48px on desktop and 32px on mobile.
  Their radius tokens are multiplied by `--corner-scale: 1.194`; we use the scaled values.
- **Shadows** are long, soft and low-alpha:
  - america.gov's elevation is `0 10px 40px #010e2414`;
  - Luma cards use a layered stack (`0 0 0 1px ink/.06, 0 3px 3px ink/.03, 0 8px 7px ink/.04, 0 17px 14px ink/.05`).

  Resting cards get the hairline plus a faint stack. Hover lifts them 2px and deepens the stack.
- **Spacing** uses a 4px base and their 24/48/96 section rhythm. The container is 1200px, with a 24px page inset
  (16px on mobile).

## Motion
Tokens:
- `--ease-out-quint: cubic-bezier(.22,1,.36,1)`. Entrances and reveals (america.gov's main curve).
- `--ease-entrance: cubic-bezier(.16,1,.3,1)`. Staggered entrances, 0.9 s (their `.stagger-entrance`).
- `--ease-standard: cubic-bezier(.4,0,.2,1)`. Hover and colour changes, 200-300 ms (Luma's `--transition-fn`).
- `--ease-drawer: cubic-bezier(.32,.72,0,1)`. Command palette and sheet open.
- `--ease-pop: cubic-bezier(.34,1.56,.64,1)`. Toast pill-in only (their `toast-pill-in`); everything else has no
  overshoot.
- `--press-scale: .98`. The `:active` scale on every pressable (their `--scale-press`).

Patterns:
1. **Staggered blur-in entrance** (america.gov `stagger-entrance-in`): opacity 0 → 1, blur 12px → 0,
   translateY 24px → 0, scale .97 → 1, 0.9 s, 80-150 ms per item.
   - Used for the hero words, the landing sections, rule cards and timeline items.
   - Below-the-fold items are revealed by an IntersectionObserver as they scroll in.
2. **Rotating prompt** (their "Try 'How do I…'" marquee): the search placeholder cycles real sample addresses with a
   vertical slide and blur. The preview card behind the search cross-fades to that address's live verdicts.
3. **View transitions:** route changes use the View Transitions API (cross-fade plus an 8px rise, 280 ms). Browsers
   without it get a CSS fade-in of `<main>`.
4. **Command search** (Luma ⌘K): `/` or ⌘K opens a centred palette from anywhere, with a drawer ease, a scrim with a
   12px backdrop blur, and keyboard navigation.
5. **Skeleton loading:** shimmer placeholders (`text-shimmer`, 1.6 s linear) while an address loads.
6. **Toasts:** a pill toast at the bottom when the as-of date or language changes, with pill-in and blur-out
   (their `toast-pill-in` and `toast-pill-out`).
7. **Status badges:** the dot pops in, and dots on "applies" and "pending" breathe softly once. Badges stagger with
   their card.
8. **As-of timeline:** the fill bar eases to the date, and event nodes light up in sequence as the date passes them.
   The big date counter cross-fades.
9. **Micro-interactions:** card hover lift (translateY -2px, deeper shadow, 300 ms standard). Pills tint on hover and
   scale .98 on press. Focus is a 3px navy ring with a 2px offset.
10. **Scroll-aware header:** the nav becomes a frosted floating pill once you scroll (backdrop blur 25px, their
    `--blur-frost`).

`prefers-reduced-motion: reduce` turns all of this off: no transforms, no blur, no stagger and no view-transition
animation. Content still appears immediately and nothing is hidden.

## Responsible-design constraints kept
- "Not legal advice" stays visible on every view:
  - a top strip in the place where america.gov shows its official-site notice;
  - a chip in the sticky nav;
  - the footer.
- Every answer shows its as-of date. Enacted and pending law stay visually separated, with pending shown on a dashed
  violet panel.
- Colour is never the only signal: every badge has a text label.
- Motion never delays content by more than about 300 ms, and it is never needed to understand the answer.

## Performance
- No framework and no build step. The fonts are about 0.4 MB total, preloaded.
- Animations use `transform`, `opacity` and `filter` only.
- The IntersectionObserver is shared, and reveal classes are removed after they run.

## `window.CE`: API for feature modules
Feature modules (`web/static/features/*`) reuse the app shell through `window.CE` instead of copying markup.
`app.js` sets it up before the first render. When everything is ready it fires `document` event `ce:ready`.
Signatures are stable (`CE.version === 1`).

| Member | What it does |
|---|---|
| `CE.renderAnswers(container, lookupResult)` | Renders the answer column into `container` (element or selector): as-of tag, category chips, cards grouped in the 6 categories, and the separate "Not law" panel for pending and failed proposals. It accepts either shape:<br>• the `/api/address/<id>` response (`{as_of, categories: [...]}`);<br>• a flat lookup `{as_of, results: [{team_rule_id, result, explanation, conflict_flag, category, title, requirement, key_value, citation, quoted_span, source_url, ...}], no_rule_findings?}`, i.e. the shape of `navigator.api.lookup()`.<br>Returns the container. |
| `CE.addRoute(name, render)` | Registers a view at `#/<name>[/<arg>]`. `render(mainEl, arg)` may be async; reveal animations are armed after it runs. |
| `CE.navigate(route)` | `CE.navigate("a/A0016")` or `CE.navigate("#/changes")`. |
| `CE.toast(msg)` | Pill toast at the bottom (above the mobile tab bar). |
| `CE.openModal(title, html)` / `CE.openSearch()` | Shared dialog / ⌘K address palette. |
| `CE.api(path)` | Cached `fetch(...).json()`. |
| `CE.t(key)`, `CE.lang()`, `CE.asOf()`, `CE.fmtDate(d)` | i18n (EN/ES), current language, current as-of date, localized dates. |
| `CE.badge(result)`, `CE.icons`, `CE.escape(s)` | Status badge HTML, the SVG icon set, HTML escaping. |

Events on `document`:
- `ce:ready`
- `ce:route` (`{view, arg}`)
- `ce:asof` (`{asOf}`)
- `ce:lang` (`{lang}`)

Rules for feature markup:
- Use the existing classes (`card`, `panel`, `pill primary|ghost|line`, `chip`, `badge <status>`, `reveal`, `page-head`, `kpis`/`kpi`, `table-card`). Feature pages then match the rest of the app automatically.
- Keep "Not legal advice" visible. The shell already shows it on every route.
- Mobile layout lives in `mobile.css`.

## Mobile navigation (≤ 640px)
- On phones, `mobile.css` turns `.tabs` into the fixed bottom tab bar. It has icons, safe-area padding, and exactly one active tab (navy icon and label on a light pill).
- The desktop navy pill is switched off there.
- The footer and toasts get `--tabbar-h` of bottom room, so content is never covered.
