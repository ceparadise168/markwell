# Markwell GUI — Reading Experience Integration

Date: 2026-06-02
Status: Approved (design)

## Goal

Fold the reading-experience strengths of the prototype reader (`output/index.html`,
a hand-built "warm-paper commonplace book") into Markwell's in-app localhost GUI.
This is a GUI beautification, not a new export format and not a rebrand: the green
brand identity (`#2E7D6B`) stays, and we add the prototype's *interactions* plus a
layer of reading atmosphere.

Decided during brainstorming:

- Integrate into the GUI (not a standalone HTML export renderer).
- Ambition tier: **surgical wins + reading atmosphere** (not a full bookshelf rebuild).
- Keep the green identity; do not adopt the prototype's amber palette or Fraunces.
- Search becomes highlight-level (prototype's hybrid model). This replaces the
  current book-card filter when a query is present.

## Non-negotiable constraints

- **Local-first / no network**: no CDN assets. Use the existing system serif stack;
  do **not** add Fraunces or any web font. Markwell must make zero outbound requests.
- **CSP-safe**: all behavior ships in the existing external `app.js` / `style.css`;
  no inline scripts or styles. Decorative layers are CSS-only.
- **XSS**: highlight text, notes, and titles are verbatim, untrusted book content.
  Every new render path uses `esc()`. Search term highlighting escapes the full
  string first, then wraps matched terms in `<mark>` — never inject unescaped text.
- **No backend, no new dependencies**: all changes live in `markwell/gui/assets/`.
  No `/api` changes, no new Python runtime deps (core stays stdlib-only).
- **Accessibility parity**: every new animation has a `prefers-reduced-motion`
  fallback; every new control is keyboard-reachable with an `aria-label`; reuse the
  existing `sr-only` live region for search announcements; preserve focus handling.

## Baseline (current GUI)

- Vanilla JS, no build step, hash router, one `view.innerHTML` per route, `esc()`
  used throughout. Data comes from `GET /api/books?source=…` →
  `books[].highlights[]` with `{ text, note, date, chapter_index }`.
- **Library** (`renderLibrary` / `refreshGrid`): page title, subtitle, a toolbar
  with a search box, and a grid of book cards. Search is a **book-level filter**
  (`bookMatches`) that narrows the card grid; it does not surface matching lines,
  mark terms, or jump to a highlight.
- **Book detail** (`renderBook`): back link, header, chapters rendered as
  `<h2>Chapter N</h2><ul>`, each highlight an `<li>` with text / optional note /
  optional date. **No copy button.**
- **Theme**: dark mode is `@media (prefers-color-scheme: dark)` only — **no toggle**.
- Already present and kept: sample-library banner, dark palette, a11y live regions.

## Components and changes

### A. Shared flat highlight index
Build once per library load from `state.lib.books[].highlights[]`, each entry:
`{ text, note, date, bookIdx, hlIdx, bookTitle, chapterIndex }`. Powers both the
hero and search. Rebuilt when `state.source` changes (alongside `loadLibrary`).

### B. Resurface-a-line hero (Library landing)
- Renders at the top of the Library view, above the search toolbar; shown only when
  the library is non-empty **and** there is no active query.
- Picks a "punchy, complete" highlight: prefer single-line entries within a length
  window (tunable; start ~16–80 chars to suit mixed zh/en), fall back to any entry.
- Large serif quote with a **green** marker emphasis on the opening clause (reuse the
  prototype's `linear-gradient` marker idea tinted with `--accent`/`--accent-soft`),
  the book title (click → jump to source highlight), the date, and a "Reshuffle"
  control. Hero quote and reshuffle are `<button>`s with `aria-label`s.
- Hidden during search. Fade-on-reshuffle is gated by `prefers-reduced-motion`.

### C. Highlight-level search (hybrid)
- No query → current book grid (unchanged).
- Query present → hide grid + hero, show **highlight results**: AND-match query terms
  across `text` + `note`; render each hit as a clamped line with matched terms in
  `<mark>` (escape-first), plus book title + date; clicking a result jumps to that
  highlight. Cap at 200 results with a "showing first 200" note.
- Reuse the existing `#q` input, `state.q`, and `announceSearch` live region.
- **Tradeoff (accepted)**: this replaces the book-card filter while typing. A query
  that matches only a book *title/author* (not any line) returns no results, matching
  the prototype's highlight-only model. Documented; revisit only if it bites.

### D. Per-highlight copy (reader)
- Each highlight gets a copy `<button>` (hover/focus-reveal; always faintly visible on
  touch), `aria-label="Copy this highlight"`.
- Copies `"<text>\n\n—《<title>》"` via `navigator.clipboard.writeText` with a
  hidden-`textarea` + `execCommand('copy')` fallback; confirms with the existing toast.

### E. Reader atmosphere
- **Reading progress bar**: a fixed element at the top whose width tracks scroll
  position; shown only in the book view; `aria-hidden` (decorative).
- **Scroll-to-top FAB**: appears after scrolling in book/search views; `aria-label`.
- **Book-end ornament** (`❊`) + back-to-library button appended in `renderBook`.
- **Reveal-on-scroll**: `IntersectionObserver` with the prototype's fail-open safety
  nets (anything on-screen or after a short timeout reveals); a no-op under
  `prefers-reduced-motion`.
- **Paper warmth**: a subtle CSS radial wash (and optional very-low-opacity grain)
  behind content, built from the existing `--bg` tones — no new palette, green stays.

### F. Day/night toggle
- Refactor `style.css`: keep `:root` light; keep `@media (prefers-color-scheme: dark)`
  applying the dark tokens as the system default; add `[data-theme="dark"]` /
  `[data-theme="light"]` overrides that win over the media query.
- A toggle button in the sidebar foot (near version/quit) with a sun/moon icon and
  `aria-label`; sets `data-theme` on `<html>` and persists to `localStorage`. When no
  stored choice exists, leave `data-theme` unset so the system preference governs.
- **FOUC vs CSP (accepted tradeoff)**: the cleanest no-flash fix — an inline head
  script that applies the stored theme before first paint — is blocked by CSP, and a
  dedicated early `theme-init.js` would need a new entry in the server's static-asset
  allowlist (a backend change we ruled out). So theme is applied by the deferred
  `app.js`. A brief flash is therefore possible **only** for a user who has toggled to
  a theme that differs from their OS setting; the common case (no override, or override
  matching the OS) paints correctly from the CSS media query. This is accepted; a
  zero-flash version is a one-line `_STATIC` follow-up if it ever bites.

## Data flow and routing

- **Jump to highlight**: set `state.jumpTo = { bookIdx, hlIdx }`, navigate to
  `#/book/{bookIdx}`; `renderBook` reads `state.jumpTo`, scrolls the anchor into view,
  flashes it, then clears `state.jumpTo`. No change to router grammar.
- **Anchors**: each highlight element gets `id="hl-{bookIdx}-{hlIdx}"`.
- No `/api` changes; the flat index and all features derive from the existing
  `/api/books` payload.

## Files touched

- `markwell/gui/assets/app.js` — flat index, hero, search upgrade, copy button,
  reader atmosphere, theme toggle, jump-to-highlight.
- `markwell/gui/assets/style.css` — theme refactor to `[data-theme]`, hero, search
  results, copy button, progress bar, FAB, reveal, paper warmth, book-end.
- `markwell/gui/assets/index.html` — theme toggle control, progress-bar element.

## Verification

The project's automated tests are Python (`pytest`); there is no JS test harness, and
adding one would mean a new build/dev dependency, which is out of scope. Verification
is therefore a Playwright/manual smoke against the **sample library** (no Kobo needed),
plus confirmation that the unchanged backend tests still pass.

Acceptance checklist:

- Library landing shows a hero highlight; "Reshuffle" swaps it; clicking the book name
  opens that book scrolled to the source highlight with a flash.
- Typing in search shows matching **highlights** (lines, marked terms, book + date);
  clicking a result jumps to that highlight; clearing returns to the book grid + hero.
- Each highlight in the reader has a copy button that copies the line + book and toasts.
- Reading progress bar tracks scroll in a book; scroll-to-top works; book ends with the
  ornament + back control.
- Theme toggle switches day/night and persists across reload; with no stored choice the
  OS preference is honored.
- `prefers-reduced-motion` disables reveal/fade/progress transitions.
- No outbound network requests occur (DevTools/Playwright network panel is clean).
- XSS: a highlight containing `<script>`/`</mark>`-like text renders as inert text in
  hero, search results, and reader.

## Out of scope

- Cross-book synthesis essay (hand-curated; not present in Kobo export).
- Standalone HTML export renderer.
- Brand color change / Fraunces / amber palette.
- Donation placement (Ko-fi primary, GitHub Sponsors secondary) — a separate task that
  also needs the Ko-fi handle.
