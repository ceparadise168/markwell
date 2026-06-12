# 把 Markwell 備份到你的雲端

[English](cloud-backup.md) · **中文（台灣）** · [日本語](cloud-backup.ja.md) · [한국어](cloud-backup.ko.md)

這份指南教你把 Markwell 書櫃放進 iCloud 雲端硬碟、Google 雲端硬碟、Dropbox
或 OneDrive，換新電腦時也能完整找回。不必註冊任何新帳號，只要點幾下。

## 為什麼這樣就行

Markwell 保存的所有東西，都是放在一個普通資料夾裡的普通檔案：保存的副本在
`backups/`、可閱讀的頁面與匯出檔在 `output/`，還有你打包的 ZIP 壓縮檔。雲端
服務本來就擅長同步資料夾——所以 Markwell 不需要你的密碼、不呼叫任何雲端
API，也不會要你註冊帳號。你只要把 Markwell 資料夾放進雲端 App 已經在同步的
資料夾*裡面*，剩下的交給雲端 App。

Markwell 自己絕不上傳任何東西。它完全不建立網路連線——同步全部由你本來就
信任、平常就在照顧其他檔案的那個雲端 App 完成（見
[SECURITY.md](../SECURITY.md)）。

## 把書櫃搬進雲端

先確認雲端服務的桌面 App 已安裝並登入——也就是 Apple、Google、Dropbox 或
Microsoft 提供、負責在你電腦上同步資料夾的那個程式。然後在 Markwell 裡：

1. 在側欄打開**設定**。
2. 在「**Markwell 資料夾的位置**」底下，這台電腦上找得到的雲端會列成
   選項——選你的那個。
3. 按下「**把書櫃放在這裡**」。
4. Markwell 會把接下來的事說清楚——所有檔案都是*複製*到新資料夾，原來的
   檔案留在原地。按下「**複製過去**」。

這樣就完成了。報告會告訴你複製了幾份保存副本、幾個檔案，以及原來的檔案還
留在哪裡——**絕不刪除任何東西**。從現在起，每次備份都會存進雲端資料夾，
你的雲端 App 會自動上傳。

Markwell 會把書櫃放在雲端資料夾最上層一個名為 `Markwell` 的資料夾裡，從你
的任何裝置都好找。

## 各家雲端的小提醒

在 Markwell 裡的步驟對每家雲端都一樣，差別只在需要安裝哪個桌面 App：

- **iCloud 雲端硬碟** —— macOS 內建：有在用 iCloud 的話，它已經在了。
  Windows 請從 Microsoft Store 安裝 **iCloud（Windows 版）**，並開啟 iCloud
  雲端硬碟。
- **Google 雲端硬碟** —— 安裝**電腦版 Google 雲端硬碟**並登入，電腦上就會
  出現同步的雲端硬碟位置。
- **Dropbox** —— 安裝 **Dropbox** 桌面 App 並登入。
- **OneDrive** —— Windows 內建：有在用 OneDrive 的話，它已經在同步了。
  macOS 請從 App Store 安裝 **OneDrive** 並登入。

如果你的雲端還是沒出現在設定裡，請看下面的常見問題。

## 換新電腦

你的書櫃會跟著你走。在新電腦上：

1. 安裝你的雲端桌面 App、登入，等它同步完成。
2. 安裝 Markwell——見[取得 Markwell](../README.zh-TW.md#取得-markwell)。
3. 打開**設定**，選同一個雲端，然後確認。

Markwell 會指向雲端裡同一個 `Markwell` 資料夾——你的書、劃線、筆記和每一
份保存副本都已經在裡面。打開**書櫃**開始閱讀，或到**歷史紀錄**查看保存的
副本。

## 常見問題

**設定裡沒有出現我的雲端。**
Markwell 只在這台電腦上找得到該雲端的同步資料夾時，才會把它列為選項。請先
確認該服務的桌面 App 已安裝並登入。如果你的雲端資料夾放在比較特別的位置，
請改選「**進階：自訂資料夾**」，輸入它裡面某個資料夾的完整路徑——例如
`/Users/you/Dropbox/Markwell`。

**到底會同步哪些東西？**
你的 Markwell 資料夾裡的一切：`backups/`（保存的副本）、`output/`（可閱讀
的頁面與匯出檔），以及你打包的 `Markwell-archive-….zip`。Markwell 的小小
設定檔放在書櫃之外（`~/.markwell/`），不會被同步，每台電腦各自保留——這是
刻意的設計。

**Markwell 會把我的劃線上傳到哪裡嗎？**
絕不會。Markwell 不建立任何網路連線；所有同步都由你的雲端服務自己的 App
完成，遵循那個 App 的帳號與規則。把雲端 App 關掉，資料夾就只是留在本機。

---

← [回到 README](../README.zh-TW.md)
