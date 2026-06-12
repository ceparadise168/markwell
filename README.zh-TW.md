# Markwell

[English](README.md) · **中文（台灣）** · [日本語](README.ja.md) · [한국어](README.ko.md)

> *把讀過的，好好記下。* 備份並匯出你的 Kobo 劃線，留下一份完全屬於你的收藏。

[![Website](https://img.shields.io/badge/Website-markwell.page-2e7d6b)](https://markwell.page)
[![CI](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml/badge.svg)](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/github/downloads/ceparadise168/markwell/total)](https://github.com/ceparadise168/markwell/releases)
[![PyPI](https://img.shields.io/pypi/v/markwell)](https://pypi.org/project/markwell/)
[![PyPI downloads](https://img.shields.io/pypi/dm/markwell)](https://pypistats.org/packages/markwell)

安全地備份、閱讀並匯出你的 [Kobo](https://www.kobo.com/) 劃線與筆記——在瀏覽器
裡直接閱讀，另有 Markdown、JSON、CSV、Anki 字卡，以及可列印的 HTML 書櫃。一切
都留在你的電腦上：不用帳號、不靠雲端服務、沒有任何網路連線。跨平台、零相依
（只用 Python 標準函式庫）。

![書櫃畫面：書籍以卡片排列，每段劃線都能搜尋](docs/screenshots/03-library.png)

## 取得 Markwell

到[最新版本](https://github.com/ceparadise168/markwell/releases/latest)下載適合
你電腦的 App：

- **macOS** — [`Markwell-macOS.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-macOS.zip)
- **Windows** — [`Markwell-Windows.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-Windows.zip)

解壓縮後打開 App，Markwell 會在你的瀏覽器中開啟，完全在你自己的電腦上運作。

<details>
<summary><strong>第一次打開時電腦猶豫了一下？</strong>——因為下載檔未經簽署</summary>

Markwell 是自由軟體，下載檔沒有程式碼簽署憑證，所以第一次啟動時作業系統會
多向你確認一次：

- **macOS（Sonoma / macOS 14 以前）** — 在 **Markwell** 上按右鍵（或按住
  Control 點一下），選擇**打開**，然後在對話框中再按一次**打開**。macOS 會
  記住你的選擇，這個步驟只需要做一次。
- **macOS（Sequoia / macOS 15 以後）** — 已經沒有右鍵這條路：先打開
  **Markwell** 一次（會被擋下），再到**系統設定 → 隱私權與安全性**，按
  **強制打開**。
- **Windows** — 出現 SmartScreen 視窗時，點選**其他資訊**，再點**仍要執行**。

如果你不想執行未簽署的程式，可以改用下面的 Python 套件安裝——同一個 App，
沒有打包的執行檔。

</details>

比較喜歡命令列？Markwell 也是一個 Python 套件（Python 3.9 以上）：

```bash
pipx install markwell    # 或：pip install markwell
markwell                 # 命令列工具
markwell-gui             # 與桌面版下載相同的 App
```

### 解除安裝

不喜歡嗎？隨時都能移除——Markwell 不會在背景安裝任何東西：沒有常駐服務、
不需要帳號、不寫入登錄檔，也從不連線。

- **macOS / Windows** — 把（解壓縮出來的）**Markwell** App 拖到垃圾桶或資源
  回收筒就好，不會留下任何殘留。
- **Python 套件** — `pipx uninstall markwell`（或 `pip uninstall markwell`）。

你的書櫃與副本存放在另一個資料夾（預設 `~/Markwell`，可在**設定**中看到），
解除安裝完全不會碰到它們。想清得乾乾淨淨？把那個資料夾、連同存放設定的
`~/.markwell/` 一併刪除即可——兩個都是完全由你掌握的普通資料夾。

## 為什麼選 Markwell

劃線與筆記，是你的閱讀裡無可取代的部分。Markwell：

- **絕不寫入你的裝置。** 它只會*讀取* Kobo 的資料庫，把檔案複製成一份本機
  副本。任何東西——連 SQLite 的例行整理——都不會碰到裝置。
- **每份副本都是不可變的歷史。** 每次執行都會保存一份帶時間戳記的
  `KoboReader-<stamp>.sqlite`，絕不覆寫，你的閱讀資料庫因此累積出完整的
  歷史。
- **給你帶得走的輸出。** 可閱讀的 Markdown、有文件規範的 JSON、給試算表用的
  CSV、Anki 字卡，以及單檔自足的 HTML 書櫃——餵給 Obsidian、Anki、Excel、
  Readwise，或你自己的程式都行。

匯出檔永遠只對應**最新**的那份副本——它們是單一資料庫的全新投影，而不是
不斷累積的檔案庫。所以如果你在裝置上刪除一段劃線，下次匯出它就不見了。要找
回來，從帶日期的副本重新匯出即可：

```bash
markwell --db backups/KoboReader-<stamp>.sqlite
```

## 圖形介面 App（不需要終端機）

上面下載的桌面版打開就是它；從終端機啟動則是：

```bash
markwell-gui          # 或：python3 -m markwell.gui
```

它會在你的瀏覽器中開啟，用平實的語言讓你：

- **備份** —— 一顆按鈕完成 Kobo 快照，把劃線變成可閱讀的頁面，過程即時顯示、
  結果清楚明白。
- **書櫃** —— 在安靜、像書一樣的版面裡閱讀與搜尋你的劃線和筆記（每本書一個
  檔案，依閱讀順序，附上你的筆記）。
- **複習** —— 每天從你的劃線裡帶回一句話，可以換一句，也可以只看某本書。
- **歷史紀錄** —— 檢視每一份保存的副本、從舊副本重新產生檔案，並開啟存放這
  一切的資料夾。
- **設定** —— 決定書櫃放在哪裡（想要的話，放進雲端資料夾），並把所有資料
  打包成一個 ZIP 壓縮檔。

![備份畫面：一顆按鈕、清楚的承諾、即時的進度](docs/screenshots/01-backup.png)

它使用與命令列相同的安全核心，所以**絕不寫入你的 Kobo**。這個 App 完全在
本機運作：只服務 `127.0.0.1`、不建立任何網路連線，每個請求都需要當次啟動
產生的權杖（見 [`SECURITY.md`](SECURITY.md)）。檔案預設放在 `~/Markwell`——
可以在**設定**裡搬移，或用 `--data-dir` 指定——App 永遠會告訴你檔案在哪裡。
它只需要 Python 標準函式庫——沒有額外相依套件，也不需要建置步驟。

## 複習與分享圖卡

**複習**每天從你自己的劃線裡帶回一句話——今天都是這一句，明天換上新的——
想多讀幾句可以隨時換，也可以只從某本書裡挑。而任何一段劃線都能變成
**分享圖卡**：三種尺寸、三種樣式的圖片，排版顧及中日韓文字，浮水印可開可關。
圖卡完全在本機的畫布上繪製，什麼都不會離開你的電腦。

![複習畫面：每天一句，從你自己的劃線裡回來](docs/screenshots/11-review.png)

![書籍頁面：劃線依閱讀順序排列，筆記就在下方](docs/screenshots/04-book-detail.png)

## 你的資料，你的語言

整個介面會說 **English、繁體中文、日本語、한국어**——在側欄就能切換，選擇會
被記住。匯出檔也在地化：Markdown 與 HTML 檔案的框架文字——標題、數量、
表頭——用你的語言書寫。App 會自動帶上你的介面語言；命令列則用
`--lang en|zh-TW|ja|ko` 指定。你的劃線和筆記本身永遠原文照錄，絕不翻譯。

CSV 與 Anki 的欄位名稱（以及 JSON 的鍵）刻意保留英文：它們是給機器看的
識別字，Notion、Anki 這類工具靠這些名稱對應欄位——翻譯了反而會弄壞所有
匯入流程。

## 備份到你的雲端

Markwell 保存的所有東西，都放在一個普通資料夾裡。打開**設定**，選擇 iCloud
雲端硬碟、Google 雲端硬碟、Dropbox 或 OneDrive，Markwell 就會把你的書櫃複製
過去——不會刪除任何東西，Markwell 自己也絕不上傳任何一個位元組：同步是你的
雲端 App 在做，就像同步其他資料夾一樣。同一個畫面還能把所有資料打包成一個
ZIP 壓縮檔。一步一步的操作說明——包括換新電腦的做法——請見
[雲端備份指南](docs/cloud-backup.zh-TW.md)。

## 命令列

接上你的 Kobo，然後：

```bash
markwell                 # 備份裝置資料庫，接著匯出所有格式
markwell --format md     # 單一格式：md、json、csv、anki 或 html
markwell --format md,csv # 以逗號列出多種格式（"all" = 全部格式）
markwell --lang zh-TW    # 匯出檔的標籤語言：en、zh-TW、ja、ko
markwell --snapshot-only # 只備份資料庫，不匯出
markwell --db PATH       # 從既有的副本匯出（不讀取裝置）
markwell --device PATH   # Kobo 掛載點或 KoboReader.sqlite 路徑（覆寫自動偵測）
markwell --require-device # 找不到裝置時直接失敗，不回退到最新的本機副本
markwell --out DIR       # 輸出目錄（預設：output/，相對於目前目錄）
markwell --debug         # 發生錯誤時顯示完整 traceback
markwell --version       # 顯示版本後結束
```

進度與狀態訊息會送到 **stderr**；匯出的資料和 JSON 則寫入 `--out` 底下的
檔案。成功時工具會印出輸出目錄的絕對路徑，你永遠知道檔案落在哪裡。

輸出（`backups/` 與 `output/` 相對於目前目錄建立）：

```
backups/
└── KoboReader-YYYYMMDD-HHMMSS.sqlite   帶時間戳記，絕不覆寫
output/
├── index.md            所有書籍、數量與連結
├── <book>.md           每本書一個檔案，劃線依閱讀順序排列
├── highlights.json     機器可讀的匯出（schema "markwell/1"）
├── highlights.csv      每段劃線一列，適用 Excel／Numbers／Notion
├── anki.tsv            可直接匯入 Anki 的字卡
└── library.html        整個書櫃合成單一自足網頁
```

## 運作方式

`偵測裝置 → 保存一份副本（唯讀） → 讀取副本 → 輸出所選格式`

每次執行最多讀取裝置一次，而且絕不修改。匯出檔只是最新副本的投影；真正
保存一切的是**副本的歷史**，所以在裝置上刪掉的劃線，仍然可以從最後收錄它的
那份帶日期 `.sqlite` 中找回（見[為什麼選 Markwell](#為什麼選-markwell)）。

## JSON 格式（開發者）

`highlights.json` 是一份有版本承諾的機器可讀匯出：schema 為 `markwell/1`，
同一主版本內的變動只會新增欄位、絕不破壞既有欄位（讀取端應忽略不認識的
欄位）。完整的欄位定義與相容性規則屬於開發者合約，開發者文件以英文版為準：
請見英文版 [JSON format](README.md#json-format)。

### 結束代碼

| 代碼 | 意義 |
|--:|---|
| `0` | 成功 |
| `2` | 找不到裝置，也沒有可用的副本或來源 |
| `3` | 資料庫讀取正常，但其中沒有任何劃線或筆記 |
| `4` | 來源無法讀取，或其格式不受支援 |

## 注意事項與相容性

- 已針對含 `Bookmark` 與 `content` 資料表的 Kobo 韌體 schema 測試。如果韌體
  更新改變了 schema，請開 issue 回報。
- 筆記（annotation）支援讀取 `Bookmark.Annotation`；如果你在劃線上寫了
  筆記，它們會出現在對應的劃線下方。
- **匯出的文字原文照錄、不可信任。** 劃線與筆記一字不改地重現，所以請把
  Markdown／JSON 當成*資料*，而不是可信的標記——以 `=`、`+`、`-`、`@` 開頭
  的值匯入試算表／CSV 時可能被當成公式，在意的話請在匯入時先行處理。見
  [SECURITY.md](SECURITY.md)。

## 開發

```bash
pip install -e ".[dev]"
pytest
```

架構不變量與專案規範見 [CONTRIBUTING.md](CONTRIBUTING.md)，版本變動見
[CHANGELOG.md](CHANGELOG.md)，回報安全性問題的方式見
[SECURITY.md](SECURITY.md)（這幾份開發者文件為英文）。

## 維護者

由 Eric Tu（[@ceparadise168](https://github.com/ceparadise168)）打造與維護——
hi@markwell.page。Markwell 是免費軟體，目前不接受捐款——如果它幫你
留住了你的閱讀，歡迎給專案一顆星，或分享一張劃線圖卡。

## 致謝

Markwell 能存在，要謝謝 **Kobo**：他們把你的劃線存成開放、好讀的標準 SQLite
資料庫，接上 USB 就能直接讀取，對讀者和開發者都很友善。謝謝 Kobo 與
[@kobolabs](https://github.com/kobolabs)。

## 授權條款

MIT——見 [LICENSE](LICENSE)。
