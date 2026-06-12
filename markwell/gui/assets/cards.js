/* Markwell GUI — share cards. A highlight becomes an image worth posting:
   three sizes (square / story / wide), three styles (paper / ink / spotlight),
   CJK-aware line breaking with simple kinsoku, drawn on <canvas> with the same
   serif the reading views use. No fonts are loaded and nothing leaves the
   machine: the canvas renders entirely from local system fonts and local text.

   Script contract (classic globals, no modules): loads AFTER i18n.js (uses
   t() / currentLocale() at call time) and BEFORE app.js, which calls
   openCardModal(hl, book) from its views. esc(), toast() and ICON are app.js
   globals — referenced only inside handlers that run long after every script
   has loaded, so the load order is safe in both directions.

   Taste decisions (documented per the design pass):
   * Ornament — the ❊ fleuron, not a typographic quote mark. ❊ is already
     Markwell's mark (book-end, Review card), and unlike “ it is script-neutral:
     a card set from 道德經 or 진달래꽃 carries no Western quote convention.
   * Quote set LEFT-aligned, regular weight — the printed-page look. Canvas has
     no text-wrap:balance, so centered ragged lines would wobble; a left edge
     with kinsoku stays book-like at any length and in any script.
   * Note defaults OFF — a note is the reader's private marginalia; putting it
     on a shareable image is an explicit opt-in, every time (privacy-first).
   * Watermark defaults ON (product decision), one click off; the choice is
     remembered for the session only, and resets to ON next launch. */

"use strict";

/* ---------- geometry & palette ---------- */

// Export sizes in CSS-free device pixels. The preview canvas is drawn at these
// exact sizes and CSS-scaled down to fit the modal — at >=1080px wide that is
// already 2x+ supersampling for any normal display, so no devicePixelRatio
// juggling is needed, and exports are pixel-exact by construction.
const CARD_SIZES = {
  square: [1080, 1080],   // feeds, 1:1
  story: [1080, 1920],    // stories, 9:16
  wide: [1200, 630],      // link/OG, ~1.9:1
};

/* Three fixed palettes, deliberately independent of the app theme: an exported
   image must look the same no matter which theme it was made in. Every hex is
   pulled verbatim from style.css custom properties (same provenance discipline
   as render/html.py):
     paper     — the light :root family: --bg #faf8f3, --ink #221f1b,
                 --ink-soft #57514a, --ink-faint #6f685e, --accent #2e7d6b,
                 --line #e8e1d5
     ink       — the [data-theme="dark"] family: --bg #15130f, --ink #ece6dc,
                 --ink-soft #b7afa3, --ink-faint #9a9286, --accent-ink #8ad6c4,
                 --line #322c24
     spotlight — the accent family: gradient from light --accent-ink #205a4d
                 down to dark --accent-soft #1d2a26, with a glow of --accent
                 #2e7d6b; text in light --bg #faf8f3 / light --accent-soft
                 #e4f0ec; meta in dark --accent-ink #8ad6c4 */
const CARD_STYLES = {
  paper: { bg: "#faf8f3", ink: "#221f1b", soft: "#57514a", faint: "#6f685e",
           accent: "#2e7d6b", frame: "#e8e1d5" },
  ink: { bg: "#15130f", ink: "#ece6dc", soft: "#b7afa3", faint: "#9a9286",
         accent: "#8ad6c4", frame: "#322c24" },
  spotlight: { gradient: ["#205a4d", "#1d2a26"], glow: "rgba(46, 125, 107, .5)",
               ink: "#faf8f3", soft: "#e4f0ec", faint: "#8ad6c4",
               accent: "#8ad6c4" },
};

// Per-size metrics (px at export scale). maxSize stays within the 18–72 fit
// range; pads are generous so a hanging punctuation glyph never nears the edge.
const CARD_LAYOUT = {
  square: { pad: 100, frame: 26, maxSize: 64, fleuron: 40, noteSize: 26,
            noteGap: 30, footerGap: 40, titleSize: 30, dateSize: 20,
            wmSize: 16, wmPad: 26 },
  story: { pad: 110, frame: 28, maxSize: 72, fleuron: 44, noteSize: 28,
           noteGap: 34, footerGap: 44, titleSize: 32, dateSize: 21,
           wmSize: 16, wmPad: 28 },
  wide: { pad: 72, frame: 20, maxSize: 52, fleuron: 30, noteSize: 22,
          noteGap: 22, footerGap: 28, titleSize: 25, dateSize: 17,
          wmSize: 16, wmPad: 22 },
};

// Font stacks copied verbatim from style.css --font-read / --font-ui, so a
// card is typeset exactly like the reading views (and the HTML export).
const CARD_FONT_READ = '"Iowan Old Style", "Palatino Linotype", Palatino, ' +
  'Georgia, "Songti TC", "Songti SC", "Noto Serif CJK TC", ' +
  '"Source Han Serif", serif';
const CARD_FONT_UI = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ' +
  '"Helvetica Neue", "PingFang TC", "PingFang SC", "Microsoft JhengHei", ' +
  '"Noto Sans CJK TC", sans-serif';

const CARD_WATERMARK = "Made with Markwell";   // brand signature, never translated
const CARD_LINE_HEIGHT = 1.6;                  // CJK-comfortable leading
const CARD_MIN_SIZE = 18;                      // below this we trim, not shrink

/* ---------- CJK-aware wrapping ---------- */

// Break-anywhere scripts: Han (incl. radicals + ext-A), kana, hangul, CJK
// punctuation, compatibility ideographs, vertical/compat forms, fullwidth
// forms. Anything else groups into Latin-style word runs. (Wider than the
// quoteLength set in app.js: that one weighs display length; this one
// decides where a line may BREAK, so it must catch every CJK character.)
const CARD_CJK_RE = /[\u2E80-\u303F\u3040-\u30FF\u31C0-\u9FFF\uAC00-\uD7AF\uF900-\uFAFF\uFE30-\uFE4F\uFF00-\uFFEF]/;

// Simple kinsoku (line-break prohibition): closing punctuation must not start
// a line; opening brackets must not end one.
const CARD_NO_START = "。．，、！？：；…‥）」』】〉》〕］｝ゝゞ々ー’”!?,.:;)]}";
const CARD_NO_END = "（「『【〈《〔［｛‘“([{";

/* Split text into wrap units: every CJK character stands alone (break-anywhere),
   Latin runs hold together (word-boundary), whitespace separates, and \n forces
   a break. Array.from walks code points, so surrogate pairs never split. */
function cardTokens(text) {
  const tokens = [];
  const chars = Array.from(String(text == null ? "" : text));
  let run = "";
  const flushRun = () => { if (run) { tokens.push({ text: run }); run = ""; } };
  for (const c of chars) {
    if (c === "\n") { flushRun(); tokens.push({ br: true }); continue; }
    if (/\s/.test(c)) { flushRun(); tokens.push({ space: true }); continue; }
    if (CARD_CJK_RE.test(c)) { flushRun(); tokens.push({ text: c, cjk: true }); continue; }
    run += c;
  }
  flushRun();
  return tokens;
}

/* Wrap `text` to `maxWidth` using ctx's CURRENT font. Returns the lines.
   Greedy fill, then a kinsoku pass:
   * a line starting with closing punctuation pulls it back onto the previous
     line as hanging punctuation (burasage) — bounded to ~one em of overhang so
     a stack of closers can never reach the canvas edge;
   * a line ending with an opening bracket pushes it down to the line it opens
     (only when the receiving line still fits — never trades a kinsoku
     violation for clipped text). */
function wrapQuote(ctx, text, maxWidth) {
  const lines = [];
  let line = "";
  for (const tok of cardTokens(text)) {
    if (tok.br) { lines.push(line.trimEnd()); line = ""; continue; }
    if (tok.space) { if (line) line += " "; continue; }
    if (line && ctx.measureText(line + tok.text).width > maxWidth) {
      lines.push(line.trimEnd());
      line = "";
    }
    if (!tok.cjk && ctx.measureText(tok.text).width > maxWidth) {
      // a single Latin run wider than the box (a URL, say): break by character
      for (const ch of Array.from(tok.text)) {
        if (line && ctx.measureText(line + ch).width > maxWidth) { lines.push(line); line = ""; }
        line += ch;
      }
      continue;
    }
    line += tok.text;
  }
  if (line) lines.push(line.trimEnd());
  return cardKinsoku(ctx, lines, maxWidth);
}

function cardKinsoku(ctx, lines, maxWidth) {
  const fontPx = /(\d+(?:\.\d+)?)px/.exec(ctx.font);
  const maxHang = fontPx ? Number(fontPx[1]) * 1.1 : 24;   // ~one em of overhang
  for (let i = 1; i < lines.length; i++) {
    const prev = lines[i - 1];
    if (!prev || !lines[i]) continue;
    const opener = prev[prev.length - 1];
    if (CARD_NO_END.indexOf(opener) >= 0 &&
        ctx.measureText(opener + lines[i]).width <= maxWidth) {
      lines[i] = opener + lines[i];
      lines[i - 1] = prev.slice(0, -1).trimEnd();
    }
    let pulled = 0;
    while (lines[i] && pulled < 2 && CARD_NO_START.indexOf(lines[i][0]) >= 0 &&
           ctx.measureText(lines[i - 1] + lines[i][0]).width <= maxWidth + maxHang) {
      lines[i - 1] += lines[i][0];
      lines[i] = lines[i].slice(1);
      pulled++;
    }
    if (pulled && !lines[i]) { lines.splice(i, 1); i--; }   // the pull emptied it
  }
  return lines;
}

/* ---------- auto-fit ---------- */

function cardQuoteFont(size) { return "400 " + size + "px " + CARD_FONT_READ; }
function cardNoteFont(size) { return "400 " + size + "px " + CARD_FONT_UI; }

// Trim a line to fit maxWidth with a trailing ellipsis (code-point safe).
function truncateLine(ctx, line, maxWidth) {
  const chars = Array.from(String(line).replace(/[\s。、，．！？]+$/, ""));
  while (chars.length && ctx.measureText(chars.join("") + "…").width > maxWidth) chars.pop();
  return chars.join("") + "…";
}

/* Find the largest font size in [18, box.maxSize] whose wrapped lines fit
   box.height (binary search; width is honoured inside wrapQuote). If even 18px
   overflows, keep what fits, end on an ellipsis, and say so via `truncated`
   (the modal shows a quiet hint). Leaves ctx.font at the chosen size. */
function fitQuote(ctx, text, box) {
  let lo = CARD_MIN_SIZE, hi = box.maxSize || 72, best = null;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    ctx.font = cardQuoteFont(mid);
    const lines = wrapQuote(ctx, text, box.width);
    if (lines.length * mid * CARD_LINE_HEIGHT <= box.height) {
      best = { size: mid, lines };
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  if (best) {
    ctx.font = cardQuoteFont(best.size);
    return { size: best.size, lines: best.lines, truncated: false };
  }
  ctx.font = cardQuoteFont(CARD_MIN_SIZE);
  const lines = wrapQuote(ctx, text, box.width);
  const keep = Math.max(1, Math.floor(box.height / (CARD_MIN_SIZE * CARD_LINE_HEIGHT)));
  const kept = lines.slice(0, keep);
  kept[kept.length - 1] = truncateLine(ctx, kept[kept.length - 1], box.width);
  return { size: CARD_MIN_SIZE, lines: kept, truncated: true };
}

/* ---------- the card itself ---------- */

// "2024-05-02" → a long localized date; anything unparseable passes through.
function cardDate(iso, locale) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
  if (!m) return String(iso || "");
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  try {
    return new Intl.DateTimeFormat(locale || undefined, { dateStyle: "long" }).format(d);
  } catch (_) {
    return String(iso);
  }
}

/* Render one card. opts = {text, note, title, author, date, style, size,
   showNote, watermark, locale}. Pure function of opts — the preview and every
   export draw through here, so they can never disagree. Returns the quote fit
   ({size, lines, truncated}) so the modal can surface the trimmed-quote hint.
   All untrusted text is drawn with fillText (no DOM, inherently inert). */
function drawCard(canvas, opts) {
  const dims = CARD_SIZES[opts.size] || CARD_SIZES.square;
  const S = CARD_STYLES[opts.style] || CARD_STYLES.paper;
  const L = CARD_LAYOUT[opts.size] || CARD_LAYOUT.square;
  const W = dims[0], H = dims[1];
  canvas.width = W;            // assignment resets the bitmap and all ctx state
  canvas.height = H;
  const ctx = canvas.getContext("2d");

  // background
  if (S.gradient) {
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, S.gradient[0]);
    g.addColorStop(1, S.gradient[1]);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    const glow = ctx.createRadialGradient(W / 2, H * 0.16, 0,
                                          W / 2, H * 0.16, Math.max(W, H) * 0.7);
    glow.addColorStop(0, S.glow);
    glow.addColorStop(1, "rgba(46, 125, 107, 0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);
  } else {
    ctx.fillStyle = S.bg;
    ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = S.frame;   // hairline inner frame: the printed-plate look
    ctx.lineWidth = 2;
    ctx.strokeRect(L.frame, L.frame, W - 2 * L.frame, H - 2 * L.frame);
  }

  const pad = L.pad;
  const boxW = W - pad * 2;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";

  // footer reserve (bottom-anchored; the quote group centers above it)
  const hasDate = !!opts.date;
  const footerH = L.titleSize * 1.25 + (hasDate ? L.dateSize * 1.8 : 0);
  const footerTop = H - pad - footerH;

  // note block — fixed size, capped at three lines, measured before the quote
  // fit so the quote takes exactly the space that remains
  const note = (opts.showNote && opts.note) ? String(opts.note) : "";
  const labelSize = Math.round(L.noteSize * 0.82);
  const noteLabelH = note ? labelSize * 1.7 : 0;
  const noteLineH = L.noteSize * 1.55;
  let noteLines = [];
  if (note) {
    ctx.font = cardNoteFont(L.noteSize);
    noteLines = wrapQuote(ctx, note, boxW);
    if (noteLines.length > 3) {
      noteLines = noteLines.slice(0, 3);
      noteLines[2] = truncateLine(ctx, noteLines[2], boxW);
    }
  }
  const noteH = note ? L.noteGap + noteLabelH + noteLines.length * noteLineH : 0;

  // quote group = fleuron + quote + note, centered in the space above the footer
  const fleurH = L.fleuron * 1.9;
  const groupTopMin = pad * 0.9;
  const avail = footerTop - L.footerGap - groupTopMin;
  const fit = fitQuote(ctx, String(opts.text || ""), {
    width: boxW,
    height: Math.max(CARD_MIN_SIZE * CARD_LINE_HEIGHT, avail - fleurH - noteH),
    maxSize: L.maxSize,
  });
  const quoteLineH = fit.size * CARD_LINE_HEIGHT;
  const quoteH = fit.lines.length * quoteLineH;
  let y = groupTopMin + Math.max(0, (avail - (fleurH + quoteH + noteH)) / 2);

  // opening ornament — Markwell's fleuron (see the header for why not “)
  ctx.fillStyle = S.accent;
  ctx.font = "400 " + L.fleuron + "px " + CARD_FONT_READ;
  ctx.fillText("❊", pad, y + L.fleuron);
  y += fleurH;

  // the quote (half-leading above each line, ascent ≈ .78em)
  ctx.fillStyle = S.ink;
  ctx.font = cardQuoteFont(fit.size);
  fit.lines.forEach((ln, i) => {
    ctx.fillText(ln, pad,
      y + i * quoteLineH + (quoteLineH - fit.size) / 2 + fit.size * 0.78);
  });
  y += quoteH;

  // the reader's note — sans voice, label in accent, body in the soft ink
  if (note) {
    y += L.noteGap;
    ctx.fillStyle = S.accent;
    ctx.font = "600 " + labelSize + "px " + CARD_FONT_UI;
    ctx.fillText(t("book.note_label"), pad, y + labelSize);
    y += noteLabelH;
    ctx.fillStyle = S.soft;
    ctx.font = cardNoteFont(L.noteSize);
    noteLines.forEach((ln, i) => {
      ctx.fillText(ln, pad,
        y + i * noteLineH + (noteLineH - L.noteSize) / 2 + L.noteSize * 0.78);
    });
  }

  // footer: title — author, then the date in small italics
  const title = String(opts.title || "");
  const author = String(opts.author || "");
  const titleBase = hasDate ? H - pad - L.dateSize * 1.8 : H - pad;
  ctx.font = "600 " + L.titleSize + "px " + CARD_FONT_READ;
  let titleText = title;
  const maxTitleW = author ? boxW * 0.62 : boxW;
  if (ctx.measureText(titleText).width > maxTitleW) {
    titleText = truncateLine(ctx, titleText, maxTitleW);
  }
  ctx.fillStyle = S.ink;
  ctx.fillText(titleText, pad, titleBase);
  if (author) {
    const tw = ctx.measureText(titleText).width;
    ctx.font = "400 " + L.titleSize + "px " + CARD_FONT_READ;
    ctx.fillStyle = S.soft;
    let authorText = " — " + author;
    if (ctx.measureText(authorText).width > boxW - tw) {
      authorText = truncateLine(ctx, authorText, boxW - tw);
    }
    ctx.fillText(authorText, pad + tw, titleBase);
  }
  if (hasDate) {
    ctx.font = "italic 400 " + L.dateSize + "px " + CARD_FONT_READ;
    ctx.fillStyle = S.faint;
    ctx.fillText(cardDate(opts.date, opts.locale), pad, H - pad);
  }

  // watermark — a whisper in the corner, outside the content padding
  if (opts.watermark) {
    ctx.font = "500 " + L.wmSize + "px " + CARD_FONT_UI;
    ctx.fillStyle = S.ink;
    ctx.globalAlpha = 0.4;
    ctx.textAlign = "right";
    ctx.fillText(CARD_WATERMARK, W - L.wmPad, H - L.wmPad);
    ctx.globalAlpha = 1;
    ctx.textAlign = "left";
  }

  return fit;
}

/* ---------- export ---------- */

// One offscreen canvas, reused for every export (single allocation; the bitmap
// is overwritten per call). Exports are always at the nominal CARD_SIZES.
let _cardExportCanvas = null;
function cardBlob(opts) {
  if (!_cardExportCanvas) _cardExportCanvas = document.createElement("canvas");
  drawCard(_cardExportCanvas, opts);
  return new Promise((resolve, reject) => {
    _cardExportCanvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error("toBlob produced no image"))),
      "image/png");
  });
}

function cardFilename() {
  return "markwell-card-" + cardState.style + "-" + cardState.size + ".png";
}

/* ---------- modal ---------- */

const cardState = {
  open: false,
  style: "paper",     // style/size persist for the session — set once, share many
  size: "square",
  watermark: true,    // default ON (product decision); session-remembered after a toggle
  showNote: false,    // privacy: the note is opt-in on EVERY open, never sticky
  data: null,         // {text, note, title, author, date}
  opener: null,       // focus returns here on close
  canvas: null,
};

function cardOpts() {
  const d = cardState.data || {};
  return {
    text: d.text || "", note: d.note || "", title: d.title || "",
    author: d.author || "", date: d.date || "",
    style: cardState.style, size: cardState.size,
    showNote: cardState.showNote, watermark: cardState.watermark,
    locale: currentLocale(),
  };
}

/* Entry point (called from app.js views): hl carries the highlight
   {text, note, date} — flat-index entries also carry bookTitle, used when no
   book object is at hand; book carries {title, author}. */
function openCardModal(hl, book) {
  if (!hl || !hl.text) return;
  if (cardState.open) closeCardModal();
  const b = book || {};
  cardState.data = {
    text: hl.text || "",
    note: hl.note || "",
    title: b.title || hl.bookTitle || "",
    author: b.author || "",
    date: hl.date || "",
  };
  cardState.showNote = false;
  cardState.opener = document.activeElement;
  buildCardModal();
  cardState.open = true;
  document.body.style.overflow = "hidden";    // the page behind must not scroll
  document.addEventListener("keydown", cardKeydown, true);
  const close = document.getElementById("card-close");
  if (close) close.focus();
  drawCardPreview();
  // CJK display faces can activate lazily; redraw once the font set settles so
  // the first paint is never stuck on a fallback face.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => { if (cardState.open) drawCardPreview(); });
  }
}

/* The modal is rebuilt from scratch on every open (innerHTML template into the
   #card-modal-root container — the same render style as app.js views) and torn
   down to nothing on close. CSP forbids inline handlers, so all wiring is
   addEventListener/onclick below. XSS contract: every t() string that enters
   this innerHTML is esc()-wrapped; the quote/title/author never enter the DOM
   at all — they exist only as fillText on the canvas. */
function buildCardModal() {
  const root = document.getElementById("card-modal-root");
  if (!root) return;
  const sizes = [
    ["square", t("card.size_square")],
    ["story", t("card.size_story")],
    ["wide", t("card.size_wide")],
  ];
  const styles = [
    ["paper", t("card.style_paper")],
    ["ink", t("card.style_ink")],
    ["spotlight", t("card.style_spotlight")],
  ];
  const seg = (group, options, picked, label) =>
    `<div class="seg" role="group" aria-label="${esc(label)}">` +
    options.map(([id, name]) =>
      `<button type="button" data-${group}="${id}" aria-pressed="${id === picked}">${esc(name)}</button>`
    ).join("") + `</div>`;

  // feature detection: unsupported actions are simply absent, never broken
  const canCopy = !!(navigator.clipboard && navigator.clipboard.write && window.ClipboardItem);
  let canShare = false;
  if (navigator.share && navigator.canShare) {
    try {
      canShare = navigator.canShare(
        { files: [new File([""], "card.png", { type: "image/png" })] });
    } catch (_) { canShare = false; }
  }

  const noteToggle = cardState.data.note ? `
        <label class="card-toggle"><input type="checkbox" id="card-note">
          <span>${esc(t("card.show_note"))}</span></label>` : "";

  root.innerHTML = `
  <div class="card-modal" id="card-modal">
    <div class="card-dialog" role="dialog" aria-modal="true" aria-labelledby="card-modal-title">
      <div class="card-dialog-head">
        <h2 id="card-modal-title">${esc(t("card.title"))}</h2>
        <button class="card-close" id="card-close" type="button" aria-label="${esc(t("card.close"))}">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6 6 18"/></svg>
        </button>
      </div>
      <div class="card-preview"><canvas id="card-canvas"></canvas></div>
      <p class="card-hint" id="card-hint" hidden>${esc(t("card.too_long"))}</p>
      <div class="card-controls">
        ${seg("size", sizes, cardState.size, t("card.size_label"))}
        ${seg("style", styles, cardState.style, t("card.style_label"))}
      </div>
      <div class="card-toggles">${noteToggle}
        <label class="card-toggle"><input type="checkbox" id="card-wm" ${cardState.watermark ? "checked" : ""}>
          <span>${esc(t("card.watermark"))}</span></label>
      </div>
      <div class="btn-row card-actions">
        <button class="btn btn-primary" id="card-download" type="button">${ICON.down}<span>${esc(t("card.download"))}</span></button>
        ${canCopy ? `<button class="btn" id="card-copy" type="button">${ICON.copy}<span>${esc(t("card.copy"))}</span></button>` : ""}
        ${canShare ? `<button class="btn" id="card-share" type="button">${ICON.share}<span>${esc(t("card.share"))}</span></button>` : ""}
      </div>
    </div>
  </div>`;

  cardState.canvas = document.getElementById("card-canvas");
  // mousedown, not click: a text-selection drag that ends on the backdrop
  // would otherwise read as a backdrop click and close the modal
  document.getElementById("card-modal").addEventListener("mousedown", (e) => {
    if (e.target === e.currentTarget) closeCardModal();
  });
  document.getElementById("card-close").onclick = closeCardModal;
  root.querySelectorAll("[data-size]").forEach((b) => {
    b.onclick = () => { cardState.size = b.dataset.size; syncCardSeg("size"); drawCardPreview(); };
  });
  root.querySelectorAll("[data-style]").forEach((b) => {
    b.onclick = () => { cardState.style = b.dataset.style; syncCardSeg("style"); drawCardPreview(); };
  });
  const noteBox = document.getElementById("card-note");
  if (noteBox) noteBox.onchange = () => { cardState.showNote = noteBox.checked; drawCardPreview(); };
  const wmBox = document.getElementById("card-wm");
  wmBox.onchange = () => { cardState.watermark = wmBox.checked; drawCardPreview(); };
  document.getElementById("card-download").onclick = downloadCard;
  const copyBtn = document.getElementById("card-copy");
  if (copyBtn) copyBtn.onclick = copyCard;
  const shareBtn = document.getElementById("card-share");
  if (shareBtn) shareBtn.onclick = shareCard;
}

function syncCardSeg(group) {
  document.querySelectorAll("#card-modal [data-" + group + "]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset[group] === cardState[group]));
  });
}

function drawCardPreview() {
  if (!cardState.canvas) return;
  const fit = drawCard(cardState.canvas, cardOpts());
  const hint = document.getElementById("card-hint");
  if (hint) hint.hidden = !fit.truncated;
  // the preview reads to AT as an image of the line (setAttribute sink: raw ok)
  const d = cardState.data || {};
  cardState.canvas.setAttribute("role", "img");
  cardState.canvas.setAttribute("aria-label",
    d.text + (d.title ? " — " + d.title : ""));
}

/* Focus trap + Escape. Capture phase, so no view-level handler sees keys while
   the modal owns the page. Tab cycles within the modal's focusables; focus that
   somehow escaped (e.g. devtools) is herded back in. */
function cardKeydown(e) {
  if (!cardState.open) return;
  if (e.key === "Escape") { e.preventDefault(); closeCardModal(); return; }
  if (e.key !== "Tab") return;
  const modal = document.getElementById("card-modal");
  if (!modal) return;
  const focusables = Array.from(modal.querySelectorAll(
    'button, input, select, [href], [tabindex]:not([tabindex="-1"])'))
    .filter((el) => !el.disabled && el.offsetParent !== null);
  if (!focusables.length) return;
  const first = focusables[0], last = focusables[focusables.length - 1];
  const active = document.activeElement;
  if (e.shiftKey && (active === first || !modal.contains(active))) {
    e.preventDefault(); last.focus();
  } else if (!e.shiftKey && (active === last || !modal.contains(active))) {
    e.preventDefault(); first.focus();
  }
}

function closeCardModal() {
  if (!cardState.open) return;
  cardState.open = false;
  document.removeEventListener("keydown", cardKeydown, true);
  document.body.style.overflow = "";
  const root = document.getElementById("card-modal-root");
  if (root) root.innerHTML = "";
  cardState.canvas = null;
  const opener = cardState.opener;
  cardState.opener = null;
  if (opener && opener.isConnected && typeof opener.focus === "function") opener.focus();
}

/* ---------- actions ---------- */

function downloadCard() {
  cardBlob(cardOpts()).then((blob) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = cardFilename();
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);   // after the download starts
    toast(t("card.downloaded"));
  }).catch(() => toast(t("card.download_failed")));
}

/* Copy: Safari only honours a ClipboardItem built inside the user gesture with
   a Promise payload; some Chromium versions only accept a realized Blob. Try
   the promise form first, fall back to the awaited-blob form, and end on a
   calm toast either way — never a silent failure. */
function copyCard() {
  const blobPromise = cardBlob(cardOpts());
  let first;
  try {
    first = navigator.clipboard.write(
      [new ClipboardItem({ "image/png": blobPromise })]);
  } catch (_) {
    first = Promise.reject(new Error("promise-form ClipboardItem unsupported"));
  }
  first
    .catch(() => blobPromise.then((b) =>
      navigator.clipboard.write([new ClipboardItem({ "image/png": b })])))
    .then(() => toast(t("card.copied")))
    .catch(() => toast(t("card.copy_failed")));
}

function shareCard() {
  const d = cardState.data || {};
  cardBlob(cardOpts()).then((blob) => {
    const file = new File([blob], cardFilename(), { type: "image/png" });
    return navigator.share({ files: [file], title: d.title || "Markwell" });
  }).catch((err) => {
    if (err && err.name === "AbortError") return;   // the reader closed the OS sheet
    toast(t("card.share_failed"));
  });
}
