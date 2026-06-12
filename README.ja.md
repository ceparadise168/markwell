# Markwell

[English](README.md) · [中文（台灣）](README.zh-TW.md) · **日本語** · [한국어](README.ko.md)

> *読んだ言葉を、心に刻む。* Kobo のハイライトをバックアップ・エクスポートして、完全にあなたのものとして手元に残します。

[![CI](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml/badge.svg)](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/github/downloads/ceparadise168/markwell/total)](https://github.com/ceparadise168/markwell/releases)
[![PyPI](https://img.shields.io/pypi/v/markwell)](https://pypi.org/project/markwell/)

[Kobo](https://www.kobo.com/) のハイライトとメモを安全にバックアップして、
読んで、書き出せます。ブラウザでそのまま読めるページに加えて、Markdown・
JSON・CSV・Anki フラッシュカード・印刷できる HTML ライブラリも。すべては
あなたのコンピュータの中だけで完結します。アカウントなし、クラウドサービス
なし、ネットワーク接続も一切なし。クロスプラットフォームで、依存ゼロ
（Python 標準ライブラリのみ）です。

![ライブラリ画面：本がカードで並び、すべてのハイライトを検索できます](docs/screenshots/03-library.png)

## Markwell を入手する

[最新リリース](https://github.com/ceparadise168/markwell/releases/latest)から、
お使いのコンピュータ向けのアプリをダウンロードしてください。

- **macOS** — [`Markwell-macOS.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-macOS.zip)
- **Windows** — [`Markwell-Windows.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-Windows.zip)

解凍してアプリを開くと、Markwell がブラウザで開きます。動作はすべて、
あなた自身のコンピュータの中だけです。

<details>
<summary><strong>初回起動でコンピュータが戸惑ったら</strong> — ダウンロードは未署名です</summary>

Markwell はフリーソフトウェアで、ダウンロードにはコード署名証明書が付いて
いません。そのため、初回起動時に OS がもう一度だけ確認を求めます。

- **macOS** — **Markwell** を右クリック（または Control キーを押しながら
  クリック）して「**開く**」を選び、ダイアログでもう一度「**開く**」を
  クリックします。macOS は選択を覚えるので、必要なのは最初の一度だけです。
- **Windows** — SmartScreen のウィンドウが表示されたら、「**詳細情報**」を
  クリックし、続けて「**実行**」をクリックします。

未署名のバイナリを実行したくない場合は、下の Python パッケージをインストール
してください。同じアプリで、同梱の実行ファイルはありません。

</details>

コマンドラインがお好みなら、Markwell は Python パッケージでもあります
（Python 3.9 以上）。

```bash
pipx install markwell    # または: pip install markwell
markwell                 # コマンドラインツール
markwell-gui             # デスクトップ版と同じアプリ
```

## なぜ Markwell なのか

ハイライトとメモは、あなたの読書の中で何にも代えがたい部分です。Markwell は：

- **端末には決して書き込みません。** Kobo のデータベースを*読み取る*だけで、
  ファイルをローカルの保存コピーに複製します。SQLite の内部処理さえ、
  何ひとつ端末には触れません。
- **すべての保存コピーを、変更されない履歴として残します。** 実行のたびに
  タイムスタンプ付きの `KoboReader-<stamp>.sqlite` を保存し、決して上書き
  しません。読書データベースの完全な履歴が積み重なっていきます。
- **持ち運べる形で出力します。** 読みやすい Markdown、仕様が文書化された
  JSON、表計算向けの CSV、Anki フラッシュカード、1 ファイルで完結する HTML
  ライブラリ。Obsidian・Anki・Excel・Readwise、あるいは自作のスクリプトに
  渡せます。

エクスポートが映すのは常に**最新**の保存コピーだけです。1 つのデータベース
の新しい投影であって、積み上がっていくアーカイブではありません。端末で
ハイライトを削除すると、次のエクスポートからは消えます。取り戻すには、
日付付きの保存コピーから書き出し直してください。

```bash
markwell --db backups/KoboReader-<stamp>.sqlite
```

## アプリ（ターミナル不要）

上のデスクトップ版を開けば、そのままこのアプリです。ターミナルからは：

```bash
markwell-gui          # または:  python3 -m markwell.gui
```

ブラウザで開き、わかりやすい言葉で操作できます。

- **バックアップ** — ボタン 1 つで Kobo の保存コピーを取り、ハイライトを
  読めるページに変えます。進行が逐次表示され、結果がはっきり示されます。
- **ライブラリ** — 落ち着いた、本のような画面でハイライトとメモを読み、
  検索できます（本ごとに 1 ファイル、読書の順番どおり、メモ付き）。
- **振り返り** — 毎日、あなたのハイライトから一句が戻ってきます。
  シャッフルも、本ごとの絞り込みもできます。
- **履歴** — すべての保存コピーを一覧し、古いコピーからファイルを再作成し、
  すべてが入っているフォルダを開けます。
- **設定** — ライブラリの置き場所を選べます（お好みでクラウドフォルダにも）。
  すべてを 1 つの ZIP アーカイブにまとめることもできます。

![バックアップ画面：ボタン1つ、明確な約束、リアルタイムの進行](docs/screenshots/01-backup.png)

コマンドラインと同じ安全なコアを使っているので、**Kobo には決して書き込み
ません**。アプリは完全にローカルです。`127.0.0.1` だけにサービスし、
ネットワーク接続を一切行わず、すべてのリクエストに起動ごとのトークンを
要求します（[`SECURITY.md`](SECURITY.md) 参照）。ファイルの置き場所は標準で
`~/Markwell` — **設定**から移動するか `--data-dir` で指定でき、アプリは
置き場所を常に表示します。必要なのは Python 標準ライブラリだけで、追加の
依存もビルドもありません。

## 振り返りとシェアカード

**振り返り**は毎日、あなた自身のハイライトから一句を連れてきます。今日は
その一句のまま、明日には新しい一句に。もっと読みたければシャッフルでき、
本ごとに絞り込むこともできます。そして、どのハイライトも**シェアカード**に
できます。3 つのサイズと 3 つのスタイル、日中韓の文字組みに配慮した
タイポグラフィ、オン／オフできる透かし。カードはローカルのキャンバスで
描かれ、何ひとつあなたのマシンの外へは出ません。

![本のページ：ハイライトが読書順に並び、メモがその下に](docs/screenshots/04-book-detail.png)

## あなたのデータを、あなたの言語で

インターフェイス全体が **English・繁體中文・日本語・한국어** を話します。
サイドバーから切り替えられ、選択は記憶されます。エクスポートもローカライズ
されます。Markdown と HTML ファイルの骨組み — タイトル、件数、表の見出し —
があなたの言語で書かれます。アプリはインターフェイスの言語を自動で引き継ぎ、
コマンドラインでは `--lang en|zh-TW|ja|ko` で指定します。ハイライトとメモ
そのものは常に原文のまま。翻訳されることはありません。

## クラウドにバックアップ

Markwell が保存するものはすべて、1 つの普通のフォルダに入っています。
**設定**を開いて iCloud Drive・Google ドライブ・Dropbox・OneDrive を選ぶと、
Markwell がライブラリをそこへコピーします。何も削除されませんし、Markwell
自身は 1 バイトもアップロードしません。同期するのはお使いのクラウドアプリで、
他のフォルダと同じように扱うだけです。同じ画面から、すべてを 1 つの ZIP
アーカイブにまとめることもできます。新しいコンピュータへの引っ越しを含む
手順は、[クラウドバックアップガイド](docs/cloud-backup.ja.md)をご覧ください。

## コマンドライン

Kobo をつないで、次を実行します。

```bash
markwell                 # 端末の保存コピーを取り、すべての形式で書き出す
markwell --format md     # 形式を1つ: md, json, csv, anki, html
markwell --format md,csv # カンマ区切りで複数指定（"all" = すべての形式）
markwell --lang ja       # 書き出しラベルの言語: en, zh-TW, ja, ko
markwell --snapshot-only # データベースのバックアップのみ（書き出しなし）
markwell --db PATH       # 既存の保存コピーから書き出す（端末は読まない）
markwell --device PATH   # Kobo のマウントポイントまたは KoboReader.sqlite のパス（自動検出より優先）
markwell --require-device # 端末がないとき、最新のローカルコピーに頼らず失敗させる
markwell --out DIR       # 出力ディレクトリ（標準: output/、カレントディレクトリ基準）
markwell --debug         # エラー時に完全なトレースバックを表示
markwell --version       # バージョンを表示して終了
```

進行・状態メッセージは **stderr** に出力され、エクスポートされたデータと
JSON は `--out` 以下のファイルに書かれます。成功すると出力ディレクトリの
絶対パスを表示するので、ファイルがどこに置かれたか常にわかります。

出力（`backups/` と `output/` はカレントディレクトリ基準で作られます）：

```
backups/
└── KoboReader-YYYYMMDD-HHMMSS.sqlite   タイムスタンプ付き、決して上書きされない
output/
├── index.md            すべての本、件数、リンク
├── <book>.md           本ごとに1ファイル、ハイライトは読書順
├── highlights.json     機械可読エクスポート（schema "markwell/1"）
├── highlights.csv      ハイライト1件につき1行。Excel / Numbers / Notion 向け
├── anki.tsv            そのまま Anki にインポートできるカード
└── library.html        ライブラリ全体を1枚の自己完結ページに
```

## 仕組み

`端末を検出 → 一度だけ保存コピー（読み取り専用） → コピーを読む → 選んだ形式で書き出す`

端末は 1 回の実行で多くても 1 度しか読まれず、決して変更されません。
エクスポートは最新の保存コピーの投影にすぎません。すべてを守っているのは
**保存コピーの履歴**です。端末で消したハイライトも、それが最後に収められた
日付付きの `.sqlite` から取り戻せます（[なぜ Markwell なのか](#なぜ-markwell-なのか)参照）。

## JSON フォーマット（開発者向け）

`highlights.json` は、バージョンが約束された機械可読エクスポートです。
schema は `markwell/1` で、同じメジャーバージョン内の変更は追加のみ —
既存のフィールドが壊れることはありません（読み取り側は未知のフィールドを
無視してください）。フィールド定義と互換性の規約は開発者向けの契約であり、
英語版が正となります。英語版の [JSON format](README.md#json-format) を
ご覧ください。

### 終了コード

| コード | 意味 |
|--:|---|
| `0` | 成功 |
| `2` | 端末が見つからず、使える保存コピー／ソースもない |
| `3` | データベースは読み取れたが、ハイライトもメモも含まれていない |
| `4` | ソースを読み取れない、またはスキーマが未対応 |

## 注意事項と互換性

- `Bookmark` テーブルと `content` テーブルを持つ Kobo ファームウェアの
  スキーマでテストしています。ファームウェア更新でスキーマが変わった場合は、
  issue でお知らせください。
- メモ（注釈）は `Bookmark.Annotation` から読み取ります。ハイライトにメモを
  書いていれば、各ハイライトの下に表示されます。
- **エクスポートされたテキストは原文のままで、信頼できないデータとして
  扱ってください。** ハイライトとメモは書かれたとおりに再現されます。
  Markdown／JSON は*データ*であって、信頼できるマークアップではありません。
  `=`・`+`・`-`・`@` で始まる値は、表計算や CSV に取り込むと数式として解釈
  されることがあります。気になる場合は取り込み時にサニタイズしてください。
  [SECURITY.md](SECURITY.md) を参照。

## 開発

```bash
pip install -e ".[dev]"
pytest
```

アーキテクチャの不変条件とプロジェクトのルールは
[CONTRIBUTING.md](CONTRIBUTING.md)、変更履歴は [CHANGELOG.md](CHANGELOG.md)、
脆弱性の報告方法は [SECURITY.md](SECURITY.md) をご覧ください（これらの
開発者向けドキュメントは英語です）。

## メンテナー

Eric Tu（[@ceparadise168](https://github.com/ceparadise168)）が開発・維持して
います — ceparadise168@gmail.com。Markwell は無料で、当面、寄付は受け付けて
いません。あなたの読書を残す役に立ったなら、リポジトリにスターを付けるか、
引用カードをシェアしていただけたら嬉しいです。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。
