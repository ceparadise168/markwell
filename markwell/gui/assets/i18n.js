/* Markwell GUI — locale table + tiny i18n runtime. Loads BEFORE app.js (both
   classic scripts sharing globals), so app.js can call t() / currentLocale()
   at any point and the language switcher works with no app.js involvement.

   The I18N table below is strict JSON — double quotes, no trailing commas, no
   comments inside — so the test suite can json.loads it and hold zh-TW / ja /
   ko to key parity with en. Keys are flat ("nav.backup"); values may carry
   {param} placeholders filled by t(key, {param: value}). Dictionary strings
   only ever reach the page through textContent / setAttribute — never
   innerHTML (see SECURITY.md). */
const I18N = {
  "en": {
    "app.title": "Markwell",
    "app.tagline": "Mark well what you read.",
    "chrome.skip": "Skip to content",
    "chrome.to_top": "Back to top",
    "nav.main_label": "Main",
    "nav.backup": "Back up",
    "nav.library": "Library",
    "nav.history": "History",
    "footer.safety": "Markwell only reads your Kobo. It never changes anything on your device.",
    "switcher.label": "Language",
    "theme.toggle": "Day / night",
    "theme.toggle_label": "Switch between day and night",
    "quit.label": "Quit Markwell",
    "quit.confirm": "Markwell is quitting.",
    "toast.copied": "Highlight copied.",
    "toast.copy_failed": "Couldn't copy — you can select the text and copy it manually."
  },
  "zh-TW": {
    "app.title": "Markwell",
    "app.tagline": "把讀過的，好好記下。",
    "chrome.skip": "跳到主要內容",
    "chrome.to_top": "回到頂端",
    "nav.main_label": "主選單",
    "nav.backup": "備份",
    "nav.library": "書櫃",
    "nav.history": "歷史紀錄",
    "footer.safety": "Markwell 只會讀取你的 Kobo，絕不修改裝置上的任何內容。",
    "switcher.label": "語言",
    "theme.toggle": "日／夜",
    "theme.toggle_label": "切換日夜模式",
    "quit.label": "結束 Markwell",
    "quit.confirm": "Markwell 正在結束。",
    "toast.copied": "已複製這段劃線。",
    "toast.copy_failed": "無法複製，你可以選取文字後手動複製。"
  },
  "ja": {
    "app.title": "Markwell",
    "app.tagline": "読んだ言葉を、心に刻む。",
    "chrome.skip": "本文へスキップ",
    "chrome.to_top": "ページの先頭へ",
    "nav.main_label": "メイン",
    "nav.backup": "バックアップ",
    "nav.library": "ライブラリ",
    "nav.history": "履歴",
    "footer.safety": "Markwell はあなたの Kobo を読み取るだけで、端末の内容を変更することは一切ありません。",
    "switcher.label": "言語",
    "theme.toggle": "昼／夜",
    "theme.toggle_label": "昼／夜モードを切り替える",
    "quit.label": "Markwell を終了",
    "quit.confirm": "Markwell を終了しています。",
    "toast.copied": "ハイライトをコピーしました。",
    "toast.copy_failed": "コピーできませんでした。テキストを選択して手動でコピーしてください。"
  },
  "ko": {
    "app.title": "Markwell",
    "app.tagline": "읽은 문장을 오래 간직하세요.",
    "chrome.skip": "본문으로 건너뛰기",
    "chrome.to_top": "맨 위로",
    "nav.main_label": "메인",
    "nav.backup": "백업",
    "nav.library": "서재",
    "nav.history": "기록",
    "footer.safety": "Markwell은 Kobo를 읽기만 할 뿐, 기기의 어떤 내용도 절대 변경하지 않습니다.",
    "switcher.label": "언어",
    "theme.toggle": "낮/밤",
    "theme.toggle_label": "낮/밤 모드 전환",
    "quit.label": "Markwell 종료",
    "quit.confirm": "Markwell을 종료하는 중입니다.",
    "toast.copied": "하이라이트를 복사했습니다.",
    "toast.copy_failed": "복사할 수 없습니다. 텍스트를 선택해 직접 복사해 주세요."
  }
};

const LOCALE_KEY = "markwell-locale";
let _locale = "en";

function _hasLocale(loc) {
  return Object.prototype.hasOwnProperty.call(I18N, loc);
}

/* Translate: active locale → en fallback → the key itself (a missing key is a
   bug, but the reader should see "nav.backup", never a blank control). `params`
   fills {x} placeholders; unknown placeholders stay intact. */
function t(key, params) {
  let s = I18N[_locale][key];
  if (s === undefined) s = I18N.en[key];
  if (s === undefined) return key;
  if (params) {
    s = s.replace(/\{(\w+)\}/g, (whole, name) =>
      Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : whole);
  }
  return s;
}

/* The reader's locale: a valid stored choice → exact navigator.language match
   → language-prefix match → English. */
function detectLocale() {
  let stored = null;
  try { stored = localStorage.getItem(LOCALE_KEY); } catch (_) { /* private mode */ }
  if (stored && _hasLocale(stored)) return stored;
  const nav = navigator.language || "";
  if (_hasLocale(nav)) return nav;
  if (/^zh/i.test(nav)) return "zh-TW";
  if (/^ja/i.test(nav)) return "ja";
  if (/^ko/i.test(nav)) return "ko";
  return "en";
}

function currentLocale() {
  return _locale;
}

/* Native-name labels for the switcher. Never translated: a reader stuck in the
   wrong language must still be able to find their own. */
function localeNames() {
  return { "en": "English", "zh-TW": "中文（台灣）", "ja": "日本語", "ko": "한국어" };
}

/* Switch locale: persist (an explicit pick — even of the auto-detected locale —
   pins the choice), reflect it on <html lang>, tell live views, re-label chrome. */
function setLocale(loc) {
  if (!_hasLocale(loc)) return;
  _locale = loc;
  try { localStorage.setItem(LOCALE_KEY, loc); } catch (_) { /* private mode: session-only */ }
  document.documentElement.lang = loc;
  document.dispatchEvent(new CustomEvent("markwell:locale", { detail: { locale: loc } }));
  applyI18nChrome();
}

/* Re-label the static chrome in the active locale: data-i18n → textContent,
   data-i18n-aria → aria-label, data-i18n-title → title. Also (re)fills the
   language switcher's options and keeps document.title in step. */
function applyI18nChrome() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.setAttribute("title", t(el.dataset.i18nTitle));
  });
  const select = document.getElementById("locale-select");
  if (select) {
    const names = localeNames();
    select.textContent = "";                 // drop any previous options
    Object.keys(I18N).forEach((loc) => {
      const opt = document.createElement("option");
      opt.value = loc;
      opt.textContent = names[loc] || loc;
      if (loc === _locale) opt.selected = true;
      select.appendChild(opt);
    });
    select.value = _locale;
  }
  document.title = t("app.title");
}

/* ---------- init (module level: runs before app.js) ---------- */
_locale = detectLocale();
document.documentElement.lang = _locale;

function _initI18nChrome() {
  applyI18nChrome();
  const select = document.getElementById("locale-select");
  if (select) select.addEventListener("change", () => setLocale(select.value));
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", _initI18nChrome);
} else {
  _initI18nChrome();   // deferred scripts run with the DOM already parsed
}
