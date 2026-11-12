<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman 图标：播放符号下方的阿拉伯字母 taa">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>用阿拉伯语观看任何视频。</strong><br>
  同步翻译、自然的实时配音、配音版 MP4，以及浏览器扩展。一切都在你自己的电脑上运行。
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="MIT 许可证" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <b>中文</b> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="Tarjuman 正在播放带阿拉伯语字幕的 YouTube 视频，配音面板已打开" width="900">
</p>

## 功能

粘贴一个 YouTube 链接、从电脑上传视频，或者提供几乎任何网站的链接。

- **同步字幕。** 阿拉伯语字幕逐行显示在视频上，如有需要，原语言可显示在下方。自动生成的字幕会先重组为完整的句子，再进行翻译。如果完全没有标点，就利用 YouTube 的逐词时间信息，在讲话者真正停顿的地方断句。
- **听起来像真人的实时配音。** 神经网络阿拉伯语语音与讲话者同步朗读每一句，支持埃及、沙特、阿联酋、叙利亚、约旦、黎巴嫩、摩洛哥和伊拉克阿拉伯语。句子不会被截断或跳过。遇到语速快的讲话者，视频会稍稍放慢，等语音跟上，而不是让语音抢着念；如果你自己放慢视频，语音也会得到这段额外的时间。拼写相同但读音不同的词，会依据英文原文按句意来读（读作 الجُمَل“句子”，而不是 الجَمَل“骆驼”）。
- **配音版 MP4。** 导出带阿拉伯语配音的视频。可以去除原讲话者的人声并保留音乐和音效，为每位讲话者匹配合适的男声或女声，并嵌入字幕或将字幕烧录进画面。
- **没有字幕？没关系。** Whisper 会在你的电脑上转写音频，然后翻译转写文本。
- **字幕文件。** 下载 SRT、VTT 或纯文本，可选阿拉伯语或双语，也可以下载可直接分享的带字幕 MP4。
- **整个播放列表。** 提供播放列表或频道链接，即可为其中每个视频生成字幕、带字幕的视频或配音视频。
- **向视频提问**（可选 AI）。获取摘要、要点、可点击的章节，以及能直接跳转到视频中讨论你问题的那一刻的回答。支持 Claude 或任何兼容 OpenAI 的服务商（Gemini、Groq、OpenRouter、Ollama）。
- **学英语。** 点按任意单词查看释义，连同所在句子一起保存，稍后复习，并导出到 Anki。你还可以重复某一句、每行结束后暂停，或模糊字幕来自我检测。
- **浏览器扩展。** 在 YouTube 本站、播放器自带字幕的网站（Coursera、Udemy 等）、从其他网站嵌入播放器的影视和动漫网站，或者通过收听标签页音频在任何其他网站上，使用同样的字幕和配音。
- **在手机上使用。** 用连接同一 Wi-Fi 的任何手机都能打开应用。

其他语言同样可用：法语、西班牙语、德语、土耳其语和英语已内置为目标语言。

## 截图

<table>
  <tr>
    <td width="50%"><img src="../screenshots/home.png" alt="首页：粘贴链接、上传视频、最近的视频和电脑状态"></td>
    <td width="50%"><img src="../screenshots/watch-en.png" alt="观看带同步字幕和文字稿的视频，英文界面、浅色主题"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/library.png" alt="我的文件：任务、播放列表批处理、已上传的视频和已完成的文件"></td>
    <td><img src="../screenshots/settings.png" alt="设置：AI 服务商、发音词典、默认选项和外观"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/extension-overlay.png" alt="扩展在 YouTube 上显示阿拉伯语字幕"></td>
    <td><img src="../screenshots/extension-welcome.png" alt="扩展的欢迎页，已连接到应用"></td>
  </tr>
</table>

<p align="center">
  <img src="../screenshots/phone-home.png" alt="手机上的首页" width="260">
  <img src="../screenshots/phone-watch.png" alt="在手机上观看" width="260">
</p>

## 快速开始

### Windows 安装程序

从 [Releases](https://github.com/MohamedElnagar94/tarjuman/releases) 页面下载 `Tarjuman-Setup-<version>.exe` 并运行。它自带 Python、所有软件包、Web 应用和浏览器扩展，因此你既不需要 Python，也不需要 Node.js。它只会请求一次管理员权限，安装到 Program Files，并且不会改动防火墙。之后 Tarjuman 会像普通桌面应用一样在自己的窗口中打开，没有控制台窗口，也没有浏览器标签页；关闭窗口即停止运行。（这个窗口是应用模式下的 Microsoft Edge，每台 Windows 10 和 11 都自带，不会额外安装任何东西。）

- 如果 Setup 一启动就停止并提示 "unable to create the directory ...\Temp\is-*.tmp, access is denied"，说明安装程序文件位于被标记为低完整性的文件夹中（有些沙盒工具会这样标记自己的工作文件夹；此时 `icacls <file>` 会显示 `Low Mandatory Level`）。Windows 会以较低的权限运行这样的文件。请把它复制到其他文件夹（例如 Downloads），然后运行副本。
- 安装程序尚未进行代码签名，因此 Windows SmartScreen 可能会提示“未知发布者”：请选择*更多信息 → 仍要运行*。
- 首次启动时会在后台下载离线阿拉伯语语音（约 60 MB）。Whisper 模型会在第一次有视频需要它时自动下载。
- 你的视频、字幕、设置和 `.env` 保存在 `%LOCALAPPDATA%\Tarjuman` 中，与程序分开存放。更新时会保留它们；卸载时会询问是否删除。
- 开始菜单中有一个指向扩展文件夹的快捷方式，用于在 `chrome://extensions` 中*加载已解压的扩展程序*。

遇到问题？请参阅[故障排除](../troubleshooting.md)。每个版本的变更见[更新日志](../../CHANGELOG.md)。

### 从源码运行

你需要 **Python 3.11+** 和 **Node.js 20+**。

**Windows：** 双击 `start.cmd`。如果 Windows 询问是否运行来自未知发布者的脚本，请用 `powershell -ExecutionPolicy Bypass -File scripts/create-shortcut.ps1` 创建一次桌面快捷方式，之后从它启动 Tarjuman；它通过 Windows 自带的 `cmd.exe` 运行同一个脚本，因此不会出现这个提示。

**macOS / Linux：**

```sh
./start.sh
```

在 Debian、Ubuntu 和 Kali 上，如果缺少 `python3-venv`，请先安装（`sudo apt install python3-venv`）。

首次运行会安装所有内容：Python 包、离线阿拉伯语语音，以及构建好的 Web 应用。随后应用会在 `http://127.0.0.1:4318` 打开。之后再启动只需几秒。要在手机上使用，请打开它为你的 Wi-Fi 打印出的地址。在 Windows 上，如果手机无法访问，请以管理员身份运行一次 `scripts/allow-phone.ps1`：它会把你家里的 Wi-Fi 标记为专用网络，并且只在专用网络上开放 Tarjuman 的端口。

<details>
<summary>手动安装</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### 命令

| 命令 | 作用 |
|---|---|
| `python -m tarjuman` | 启动应用（`--port`、`--host 127.0.0.1` 仅限本机访问、`--no-open`） |
| `python -m tarjuman app` | 在独立窗口中启动应用（应用模式下的 Edge 或 Chrome），而不是浏览器标签页；关闭窗口即停止运行 |
| `python -m tarjuman subs <link>` | 将字幕文件写入 `data/output`（`--lang`、`--format srt,vtt,txt`） |
| `python -m tarjuman setup` | 安装或修复所有组件 |
| `python -m tarjuman update` | 当下载或语音失效时，更新 yt-dlp 和语音客户端 |
| `python -m tarjuman doctor` | 检查每个组件 |

## 浏览器扩展

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Tarjuman 扩展的弹出窗口" width="320">
</p>

可直接从 [Chrome 应用商店](https://chromewebstore.google.com/detail/gcfnomfbpenbhdebopmpdfamlaiodflp) 安装，或按以下步骤从源码构建：

1. 构建一次：`npm --prefix extension install && npm --prefix extension run build`。
2. 打开 `chrome://extensions`（或 `edge://extensions`），开启**开发者模式**，点击**加载已解压的扩展程序**，然后选择 `extension/dist`。
3. 保持应用运行，打开一个视频，点击 Tarjuman 图标，或按 <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>。

扩展只与你电脑上的应用通信。它的 Chrome Web Store 上架材料（商品描述、权限说明、隐私政策、宣传图片）位于 [`extension/store`](../../extension/store)。

## 配音如何保持同步

字幕行会被合并成完整的句子，口语中的填充词会被删除。然后根据约 12 秒的前瞻窗口为每个句子选择语速，这样宽松的句子可以把时间“借”给紧凑的句子，语速也会平缓变化而不是突然跳变。在浏览器播放每一段的前几句之前，服务器会先合成并测量这些句子，因此计划依据的是真实时长而不是估计；同时它会在后台准备下一段。如果配音仍然落后，视频会放慢到你当前速度的 85%，直到语音跟上；只有当差距超过约两秒时视频才会暂停。节奏会跟随你的播放速度。无论跳转到哪里，配音都会从准确的位置继续。当免费翻译服务限流时，第二个 Google 端点以及随后 YouTube 自带的翻译会让配音继续下去。

完整设计见 [docs/implementation.md](../implementation.md)。

## 隐私

Tarjuman 以本地为先。你的视频、字幕、保存的单词、设置和 API 密钥都保存在你电脑上的 `data/` 文件夹中。应用会连接 YouTube（字幕和下载）、Google Translate 和 MyMemory（翻译）、微软的 Edge 语音服务（语音合成），以及仅在你开启时连接你选择的 AI 服务商。没有账户、没有统计分析、没有追踪。视频和音频绝不会被上传。

| 功能 | 离开你电脑的内容 | 发送到 | 不发送任何内容的做法 |
|---|---|---|---|
| YouTube 字幕 | 视频链接 | YouTube | 上传文件；它会在本地转写 |
| 翻译 | 视频中的句子（文本形式） | Google Translate，其次是 MyMemory | 暂无；已保存的句子仍可离线使用 |
| 配音语音 | 每个译好的句子和语音名称 | Microsoft Edge 语音，其次是 Google | Piper，本地阿拉伯语语音 |
| 视频下载 | 对该视频的请求 | 托管该视频的网站 | 使用电脑上已有的文件 |
| AI（可选，默认关闭） | 视频的文本和你的问题 | 你选择的服务商 | 保持关闭，或使用 Ollama 等本地服务器 |
| 模型下载 | 一次下载请求，仅一次 | Hugging Face、GitHub | 首次下载之后不再发送任何内容 |
| 语音识别、音乐分离、你的文件 | 无 | – | 始终在本地 |

应用内的“设置 → 隐私”中也有同一张表。API 会拒绝来自其他网站的请求，AI 设置也只能在运行应用的那台电脑上修改。

## 配置

在项目文件夹中把 `.env.example` 复制为 `.env` 并进行编辑；每项设置都在其中用阿拉伯语和英语作了说明。该文件在启动时读取，因此修改后请重启 Tarjuman。在真实环境中设置的变量优先于该文件。

| 环境变量 | 默认值 | 含义 |
|---|---|---|
| `TARJUMAN_HOME` | 项目文件夹 | `data/` 的存放位置 |
| `TARJUMAN_PORT` | `4318` | 首先尝试的端口（若被占用则依次递增；扩展会自动跟随） |
| `TARJUMAN_HOST` | `0.0.0.0` | 设为 `127.0.0.1` 可让应用不对 Wi-Fi 开放 |
| `TARJUMAN_WHISPER_MODEL` | `base` | 使用 `small` 或 `medium` 可获得更准确（但更慢）的转写 |
| `TARJUMAN_VOICE_CACHE_GB` | `2` | 已保存配音语音的大小上限；最久未使用的先删除 |
| `TARJUMAN_MAX_UPLOAD_GB` | `8` | 可上传视频的最大大小 |
| `TARJUMAN_PAIR_MINUTES` | `15` | 手机配对码（二维码）的有效时长（分钟）；`0` = 一直有效，直到你生成新的 |
| `TARJUMAN_FETCH_PRIVATE` | 关闭 | 设为 `1` 可允许从你自己网络内的地址下载 |
| `TARJUMAN_HEAVY_JOBS` | `2` | 同时运行的重型任务（Whisper、配音、烧录字幕）数量；内存较小的电脑请设为 `1` |
| `TARJUMAN_MAX_QUEUE` | `20` | 最多可排队等待的任务数 |
| `TARJUMAN_FORCE_ASR` | 关闭 | 设为 `1` 可始终使用 Whisper 转写，忽略 YouTube 的字幕 |
| `ANTHROPIC_API_KEY` | – | 设置中未保存密钥时，用于 Claude |

## 项目结构

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## 开发

```sh
# backend tests (offline)
cd backend && ../.venv/bin/python -m pytest      # Windows: ..\.venv\Scripts\python

# dub engine tests
npm test

# web app with hot reload (proxies the API to 127.0.0.1:4318)
npm --prefix frontend run dev

# extension: build, test, package a store zip
npm --prefix extension run build && npm --prefix extension test && npm --prefix extension run package
```

修改 API 路由前请先阅读 [docs/specs.md](../specs.md)：Web 应用和扩展都依赖它。

### 构建 Windows 安装程序

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1   # build\windows\app: Python, packages, web app, extension
iscc /DAppVersion=3.0.0 installer\tarjuman.iss                # build\windows\Tarjuman-Setup-3.0.0.exe (Inno Setup 6)
```

*Windows installer* 工作流会在 GitHub 上完成同样的事情：从 Actions 标签页运行它，或者推送形如 `v3.0.0` 的标签，把安装程序附加到发布版本中。编译之前，它会启动打包好的应用并检查其是否有响应。

## 使用的技术

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[Ultimate Vocal Remover 的 MDX-Net 模型](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## 许可证

[MIT](../../LICENSE)。下载视频和字幕须遵守各网站的条款。请仅将 Tarjuman 用于你有权观看和改编的内容。
