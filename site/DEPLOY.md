# Markwell 官網部署（Cloudflare Pages）

`site/` 是純靜態網站：四個語言頁面（`/`、`/zh-tw/`、`/ja/`、`/ko/`）+ 一份
`site.css` + 圖片。styling 全部走 `site.css`，沒有 build step；唯一的外部資源是
Cloudflare Web Analytics 的 beacon（cookieless），其餘零 JS。`_headers` 的 CSP 以
`default-src 'none'` 打底、只額外放行那支 beacon。部署 = 把這個資料夾交給
Cloudflare Pages。

## ① 建立 Pages 專案（Eric 手動）

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** →
   **Connect to Git**。
2. 選 repo `ceparadise168/markwell`，production branch 選 `main`。
3. Build 設定：
   - **Build command**：留空（什麼都不填）
   - **Build output directory**：`site`
4. **Save and Deploy**。完成後會拿到 `<project>.pages.dev` 網址，先用它確認
   四頁都正常。

## ② 綁定自訂網域（Eric 手動）

1. Pages 專案 → **Custom domains** → **Set up a custom domain**。
2. 輸入網域。DNS 已在 Cloudflare 的話會自動建 CNAME；不在的話照畫面指示，把
   CNAME 指到 `<project>.pages.dev`。
3. 等憑證簽發完成（通常幾分鐘），用 https 開一次確認。

## ③ origin = `markwell.page`（已完成）

四頁 head 的 canonical / hreflang / `og:image` 已全部指向 `https://markwell.page`，
原本的 `MARKWELL_SITE_ORIGIN` placeholder 已替換完畢。

**將來若換網域**，在 **repo 根目錄**跑一次（macOS 用 `sed -i ''`，Linux 用 `sed -i`）：

```bash
grep -rl 'markwell.page' site/ | xargs sed -i '' 's|https://markwell.page|https://新網域|g'
```

改完 `git add site && git commit && git push`，Pages 會自動重新部署。

## ④ Web Analytics（已接好）

Cloudflare Web Analytics 已經接上：beacon script 已嵌在四頁的 `<head>`，
`site/_headers` 的 CSP 也已放寬，**只**額外允許 Cloudflare Insights：

```
script-src https://static.cloudflareinsights.com; connect-src https://cloudflareinsights.com
```

其餘維持 `default-src 'none'`（cookieless、不蒐集個資）。部署後流量資料就會進
Pages 專案的 **Web Analytics**，不必再動 CSP。要關掉：把上面兩段從 `_headers`
移除，並刪掉四頁 head 裡的 beacon `<script>`。

## ⑤ 上線檢查清單

- [ ] 四頁都開得起來：`/`、`/zh-tw/`、`/ja/`、`/ko/`；右上語言切換互連正常。
- [ ] 下載連結指向 `…/releases/latest/download/Markwell-macOS.zip`（和 Windows
      版）；v0.2.0 已發佈，連結生效中。
- [ ] `https://markwell.page/img/og.png` 開得起來（OG 預覽圖）。
- [ ] footer 的「☕ 請我喝咖啡」連到 `https://ko-fi.com/erictu`，頁面正常。
- [ ] `_headers` 有生效：

  ```bash
  curl -sI https://markwell.page/ | grep -i 'content-security-policy\|x-content-type\|referrer-policy'
  ```

- [ ] 拿網址到 LINE / X / Slack 貼一次，確認 OG 卡片（標題、描述、圖）有出現。
