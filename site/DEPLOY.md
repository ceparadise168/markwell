# Markwell 官網部署（Cloudflare Pages）

`site/` 是純靜態網站：四個語言頁面（`/`、`/zh-tw/`、`/ja/`、`/ko/`）+ 一份
`site.css` + 圖片。**零 JavaScript、零外部資源**——styling 全部走 `site.css`，
`_headers` 鎖了 `default-src 'none'` 的 CSP。部署 = 把這個資料夾交給
Cloudflare Pages，沒有 build step。

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

## ③ 換掉 origin placeholder（網域確定後跑一次）

四個頁面 head 裡的 canonical / hreflang / `og:image` 都寫著字面 placeholder
`https://MARKWELL_SITE_ORIGIN`。網域確定後，在 **repo 根目錄**跑：

```bash
grep -rl 'MARKWELL_SITE_ORIGIN' site/ | xargs sed -i '' 's|https://MARKWELL_SITE_ORIGIN|https://你的網域|g'
```

- macOS 的 sed 是 `sed -i ''`（空字串參數必填）；Linux 改成 `sed -i`（不帶 `''`）。
- 本檔（DEPLOY.md）裡的 placeholder 也會被一併替換，屬預期行為。
- 改完 `git add site && git commit && git push`，Pages 會自動重新部署。

## ④ 開啟 Web Analytics（Eric 手動）

Pages 專案 → **Metrics** tab → 啟用 **Web Analytics**（免費、無 cookie、
不蒐集個資）。

> **取捨先講**：Web Analytics 靠 Cloudflare 在頁面注入一支 beacon script，
> 而目前 `_headers` 的 CSP 是 `default-src 'none'`（沒有 script-src），瀏覽器
> 會把 beacon 擋掉——dashboard 大概率看不到數據。要看數據就得放寬 CSP，把
> `site/_headers` 的 CSP 行改成：
>
> ```
> Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'self'; script-src https://static.cloudflareinsights.com; connect-src https://cloudflareinsights.com; base-uri 'none'; form-action 'none'
> ```
>
> 「零外部資源」承諾 vs 流量數據，這條由你拍板；不改 CSP 的話 Analytics
> 開了也只是擺著。

## ⑤ 上線檢查清單

- [ ] 四頁都開得起來：`/`、`/zh-tw/`、`/ja/`、`/ko/`；右上語言切換互連正常。
- [ ] 下載連結：第一個公開 release 發佈前，
      `…/releases/latest/download/Markwell-macOS.zip`（和 Windows 版）會
      404——**預期行為**，release 一發佈就自動生效，不用改網站。
- [ ] ③ 跑完後，`https://你的網域/img/og.png` 開得起來（OG 預覽圖）。
- [ ] `_headers` 有生效：

  ```bash
  curl -sI https://你的網域/ | grep -i 'content-security-policy\|x-content-type\|referrer-policy'
  ```

- [ ] 拿網址到 LINE / X / Slack 貼一次，確認 OG 卡片（標題、描述、圖）有出現。
