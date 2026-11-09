<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman のアイコン：再生マークの下にアラビア文字のター">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>どんな動画もアラビア語で。</strong><br>
  同期翻訳、自然なライブ吹き替え、吹き替え済み MP4、そしてブラウザ拡張機能。すべてあなたのパソコン上で動きます。
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="MIT ライセンス" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1F2E8C">
  <img alt="Vue 3" src="https://img.shields.io/badge/vue-3-1F2E8C">
  <img alt="Chrome MV3" src="https://img.shields.io/badge/chrome-MV3-F0922B">
</p>

<p align="center">
  <a href="../../README.md">English</a> ·
  <a href="README.ar.md">العربية</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.it.md">Italiano</a> ·
  <a href="README.pt.md">Português</a> ·
  <a href="README.tr.md">Türkçe</a> ·
  <a href="README.ru.md">Русский</a> ·
  <a href="README.ur.md">اردو</a> ·
  <a href="README.fa.md">فارسی</a> ·
  <a href="README.hi.md">हिन्दी</a> ·
  <a href="README.id.md">Bahasa Indonesia</a> ·
  <a href="README.zh.md">中文</a> ·
  <b>日本語</b> ·
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="アラビア語字幕付きで YouTube 動画を再生し、吹き替えパネルを開いた Tarjuman" width="900">
</p>

## できること

YouTube のリンクを貼り付けるか、パソコンから動画をアップロードするか、ほぼどのサイトのリンクでも渡すだけです。

- **同期字幕。** アラビア語の字幕が動画の上に一行ずつ表示され、必要なら元の言語をその下に表示できます。自動生成字幕は、翻訳の前に完全な文へと組み立て直されます。
- **人の声のように聞こえるライブ吹き替え。** ニューラル音声のアラビア語が、話し手のタイミングに合わせて一文ずつ読み上げます。エジプト、サウジアラビア、アラブ首長国連邦、シリア、ヨルダン、レバノン、モロッコ、イラクのアラビア語に対応しています。文が途中で切れたり飛ばされたりすることはなく、吹き替えが大きく遅れたときだけ動画が一時停止します。
- **吹き替え MP4。** アラビア語のボイスオーバー付きで動画を書き出せます。音楽や効果音を残したまま元の話し手の声を取り除いたり、話し手ごとに合った男性または女性の声を割り当てたり、字幕を埋め込んだり焼き込んだりできます。
- **字幕がなくても大丈夫。** Whisper がパソコン上で音声を文字起こしし、その文字起こしを翻訳します。
- **字幕ファイル。** SRT、VTT、プレーンテキストを、アラビア語のみまたは二言語でダウンロードできます。そのまま共有できる字幕付き MP4 も作れます。
- **プレイリストまるごと。** プレイリストやチャンネルのリンクを渡せば、含まれるすべての動画について字幕、字幕付き動画、吹き替え動画を作成します。
- **動画に質問する**（AI はオプション）。要約、要点、クリックできるチャプター、そして質問の内容が語られている場面へジャンプできる回答が得られます。Claude、または OpenAI 互換の任意のプロバイダー（Gemini、Groq、OpenRouter、Ollama）で動作します。
- **英語を学ぶ。** 単語をタップすると意味が表示され、その文ごと保存して後で復習し、Anki に書き出せます。文を繰り返したり、一行ごとに一時停止したり、字幕をぼかして自分を試したりもできます。
- **ブラウザ拡張機能。** 同じ字幕と吹き替えを、YouTube 上で直接、プレーヤーに字幕があるサイト（Coursera、Udemy など）で、あるいはタブの音声を聞き取ることでその他のどのサイトでも使えます。

他の言語にも対応しています。フランス語、スペイン語、ドイツ語、トルコ語、英語が翻訳先として組み込まれています。

## クイックスタート

**Python 3.11+** と **Node.js 20+** が必要です。

**Windows：** `start.cmd` をダブルクリックします。

**macOS / Linux：**

```sh
./start.sh
```

初回の実行ですべてがインストールされます。Python パッケージ、オフラインのアラビア語音声、そして Web アプリのビルドです。その後、アプリが `http://127.0.0.1:4318` で開きます。2 回目以降は数秒で起動します。スマートフォンから使うには、Wi-Fi 用に表示されるアドレスを開いてください。

<details>
<summary>手動セットアップ</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### コマンド

| コマンド | 内容 |
|---|---|
| `python -m tarjuman` | アプリを起動（`--port`、このパソコンからのみ使う場合は `--host 127.0.0.1`、`--no-open`） |
| `python -m tarjuman subs <link>` | 字幕ファイルを `data/output` に書き出す（`--lang`、`--format srt,vtt,txt`） |
| `python -m tarjuman setup` | すべてをインストールまたは修復 |
| `python -m tarjuman update` | ダウンロードや音声が動かなくなったときに yt-dlp と音声クライアントを更新 |
| `python -m tarjuman doctor` | すべてのコンポーネントをチェック |

## ブラウザ拡張機能

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Tarjuman 拡張機能のポップアップ" width="320">
</p>

1. 一度だけビルドします：`npm --prefix extension install && npm --prefix extension run build`。
2. `chrome://extensions`（または `edge://extensions`）を開き、**デベロッパー モード**をオンにして、**パッケージ化されていない拡張機能を読み込む**をクリックし、`extension/dist` を選びます。
3. アプリを起動したまま動画を開き、Tarjuman のアイコンをクリックするか、<kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd> を押します。

拡張機能はあなたのパソコン上のアプリとだけ通信します。Chrome Web Store 用のキット（掲載文、権限の説明、プライバシーポリシー、プロモーション画像）は [`extension/store`](../../extension/store) にあります。

## 吹き替えが同期を保つしくみ

字幕の行は完全な文にまとめられ、話し言葉のつなぎ言葉は取り除かれます。次に、約 12 秒の先読みウィンドウをもとに各文の速度を決めます。余裕のある文が詰まった文に時間を貸し、速度は急に跳ねずに少しずつ変わります。ブラウザが何かを再生する前に、サーバーがすべての文を合成して長さを測るので、計画は推測ではなく実際の長さに基づいています。それでも吹き替えが遅れた場合は、続く文を少し速く再生します。動画が一時停止するのは、ずれが約 2 秒を超えたときだけです。どこにシークしても、吹き替えはその位置から正確に再開します。

詳しい設計は [docs/implementation.md](../implementation.md) にあります。

## プライバシー

Tarjuman はローカルファーストです。動画、字幕、保存した単語、設定、API キーは、あなたのパソコンの `data/` フォルダに保存されます。アプリが接続するのは YouTube（字幕とダウンロード）、Google Translate と MyMemory（翻訳）、Microsoft の Edge 音声サービス（音声合成）、そして有効にした場合に限り、あなたが選んだ AI プロバイダーです。アカウント、アクセス解析、トラッキングは一切ありません。API は他の Web サイトからのリクエストを拒否し、AI の設定はアプリを実行しているパソコンからしか変更できません。

## 設定

| 環境変数 | 既定値 | 意味 |
|---|---|---|
| `TARJUMAN_HOME` | プロジェクトフォルダ | `data/` を置く場所 |
| `TARJUMAN_PORT` | `4318` | 最初に試すポート（使用中なら次の番号に進み、拡張機能もそれに追従） |
| `TARJUMAN_HOST` | `0.0.0.0` | `127.0.0.1` にすると Wi-Fi からアプリにアクセスできなくなります |
| `TARJUMAN_WHISPER_MODEL` | `base` | より正確な（ただし遅い）文字起こしには `small` または `medium` |
| `ANTHROPIC_API_KEY` | – | 設定にキーが保存されていないときに Claude で使用 |

## プロジェクト構成

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## 開発

```sh
# backend tests (offline)
cd backend && ../.venv/bin/python -m pytest      # Windows: ...venvScriptspython

# dub engine tests
npm test

# web app with hot reload (proxies the API to 127.0.0.1:4318)
npm --prefix frontend run dev

# extension: build, test, package a store zip
npm --prefix extension run build && npm --prefix extension test && npm --prefix extension run package
```

API のルートを変更する前に [docs/specs.md](../specs.md) を読んでください。Web アプリと拡張機能の両方がこれに依存しています。

## 使用技術

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[Ultimate Vocal Remover の MDX-Net モデル](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## ライセンス

[MIT](../../LICENSE)。動画や字幕のダウンロードは、各サイトの利用規約に従います。Tarjuman は、視聴と改変が許可されているコンテンツにのみ使用してください。
