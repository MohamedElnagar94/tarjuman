<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman 아이콘: 재생 기호 아래의 아랍 문자 타">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>어떤 영상이든 아랍어로 보세요.</strong><br>
  동기화된 번역, 자연스러운 실시간 더빙, 더빙된 MP4, 그리고 브라우저 확장 프로그램. 모든 것이 내 컴퓨터에서 실행됩니다.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="MIT 라이선스" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <a href="README.ja.md">日本語</a> ·
  <b>한국어</b>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="아랍어 자막과 함께 YouTube 영상을 재생하고 더빙 패널을 연 Tarjuman" width="900">
</p>

## 주요 기능

YouTube 링크를 붙여 넣거나, 컴퓨터에서 영상을 업로드하거나, 거의 모든 사이트의 링크를 넣으세요.

- **동기화 자막.** 아랍어 자막이 영상 위에 한 줄씩 표시되며, 원하면 원래 언어를 그 아래에 함께 볼 수 있습니다. 자동 생성 자막은 번역 전에 완전한 문장으로 다시 묶입니다.
- **사람 목소리 같은 실시간 더빙.** 신경망 아랍어 음성이 화자의 타이밍에 맞춰 각 문장을 읽어 줍니다. 이집트, 사우디, 에미리트, 시리아, 요르단, 레바논, 모로코, 이라크 아랍어를 지원합니다. 문장이 잘리거나 건너뛰는 일은 없으며, 더빙이 크게 뒤처질 때만 영상이 일시 정지됩니다.
- **더빙 MP4.** 아랍어 보이스오버를 입힌 영상을 내보냅니다. 음악과 효과음은 그대로 두고 원래 화자의 목소리만 제거할 수 있고, 화자마다 어울리는 남성 또는 여성 음성을 지정하며, 자막을 삽입하거나 영상에 입힐 수 있습니다.
- **자막이 없어도 괜찮습니다.** Whisper가 내 컴퓨터에서 오디오를 받아쓰고, 그 내용을 번역합니다.
- **자막 파일.** SRT, VTT 또는 일반 텍스트를 아랍어나 이중 언어로 내려받거나, 바로 공유할 수 있는 자막 입힌 MP4를 받으세요.
- **재생목록 전체.** 재생목록이나 채널 링크를 넣으면 그 안의 모든 영상에 대해 자막, 자막 영상 또는 더빙 영상을 만듭니다.
- **영상에게 묻기** (선택형 AI). 요약, 핵심 내용, 클릭할 수 있는 챕터, 그리고 질문과 관련된 장면으로 바로 이동하는 답변을 받아 보세요. Claude 또는 OpenAI 호환 제공자(Gemini, Groq, OpenRouter, Ollama)와 함께 작동합니다.
- **영어 공부.** 단어를 탭하면 뜻이 나오고, 문장과 함께 저장해 나중에 복습하며, Anki로 내보낼 수 있습니다. 문장을 반복하거나, 한 줄마다 멈추거나, 자막을 흐리게 해서 스스로 테스트할 수도 있습니다.
- **브라우저 확장 프로그램.** 같은 자막과 더빙을 YouTube에서 바로, 플레이어에 자막이 있는 사이트(Coursera, Udemy 등)에서, 또는 탭의 오디오를 듣는 방식으로 다른 어떤 사이트에서든 사용하세요.

다른 언어도 됩니다. 프랑스어, 스페인어, 독일어, 터키어, 영어가 대상 언어로 내장되어 있습니다.

## 빠른 시작

**Python 3.11+**와 **Node.js 20+**가 필요합니다.

**Windows:** `start.cmd`를 더블클릭하세요.

**macOS / Linux:**

```sh
./start.sh
```

처음 실행하면 Python 패키지, 오프라인 아랍어 음성, 웹 앱 빌드까지 모든 것이 설치됩니다. 그런 다음 앱이 `http://127.0.0.1:4318`에서 열립니다. 이후에는 몇 초 만에 시작됩니다. 휴대폰에서 사용하려면 Wi-Fi용으로 출력되는 주소를 여세요.

<details>
<summary>수동 설치</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### 명령어

| 명령어 | 하는 일 |
|---|---|
| `python -m tarjuman` | 앱 시작 (`--port`, 이 컴퓨터에서만 쓰려면 `--host 127.0.0.1`, `--no-open`) |
| `python -m tarjuman subs <link>` | 자막 파일을 `data/output`에 저장 (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | 모든 것을 설치하거나 복구 |
| `python -m tarjuman update` | 다운로드나 음성이 작동하지 않을 때 yt-dlp와 음성 클라이언트를 업데이트 |
| `python -m tarjuman doctor` | 모든 구성 요소 점검 |

## 브라우저 확장 프로그램

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Tarjuman 확장 프로그램 팝업" width="320">
</p>

1. 한 번 빌드합니다: `npm --prefix extension install && npm --prefix extension run build`.
2. `chrome://extensions`(또는 `edge://extensions`)를 열고, **개발자 모드**를 켠 뒤, **압축해제된 확장 프로그램을 로드합니다**를 클릭하고 `extension/dist`를 선택합니다.
3. 앱을 실행한 채로 영상을 열고 Tarjuman 아이콘을 클릭하거나 <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>를 누릅니다.

확장 프로그램은 내 컴퓨터의 앱과만 통신합니다. Chrome Web Store 등록 키트(등록 문구, 권한 사유, 개인정보처리방침, 홍보 이미지)는 [`extension/store`](../../extension/store)에 있습니다.

## 더빙이 동기화를 유지하는 방법

자막 줄은 완전한 문장으로 합쳐지고, 말버릇 같은 군말은 제거됩니다. 그런 다음 약 12초 길이의 선행 창을 보고 각 문장의 속도를 정합니다. 여유 있는 문장이 빠듯한 문장에 시간을 빌려주고, 속도는 갑자기 튀지 않고 점진적으로 바뀝니다. 브라우저가 무언가를 재생하기 전에 서버가 모든 문장을 합성해 길이를 재므로, 계획은 추측이 아니라 실제 길이에 기반합니다. 그래도 더빙이 뒤처지면 다음 문장들을 조금 빠르게 재생하며, 차이가 약 2초를 넘을 때만 영상이 일시 정지됩니다. 어디로 이동하든 더빙은 정확히 그 지점에서 다시 시작됩니다.

전체 설계는 [docs/implementation.md](../implementation.md)에 있습니다.

## 개인정보 보호

Tarjuman은 로컬 우선입니다. 영상, 자막, 저장한 단어, 설정, API 키는 내 컴퓨터의 `data/` 폴더에 남습니다. 앱은 YouTube(자막과 다운로드), Google Translate와 MyMemory(번역), Microsoft의 Edge 음성 서비스(음성), 그리고 직접 켠 경우에만 선택한 AI 제공자에 연결합니다. 계정, 분석, 추적은 없습니다. API는 다른 웹사이트에서 온 요청을 거부하며, AI 설정은 앱을 실행 중인 컴퓨터에서만 변경할 수 있습니다.

## 설정

| 환경 변수 | 기본값 | 의미 |
|---|---|---|
| `TARJUMAN_HOME` | 프로젝트 폴더 | `data/`를 두는 위치 |
| `TARJUMAN_PORT` | `4318` | 처음 시도할 포트 (사용 중이면 다음 번호로 넘어가며, 확장 프로그램도 따라갑니다) |
| `TARJUMAN_HOST` | `0.0.0.0` | Wi-Fi에서 앱에 접근하지 못하게 하려면 `127.0.0.1` 사용 |
| `TARJUMAN_WHISPER_MODEL` | `base` | 더 정확한(대신 느린) 받아쓰기를 원하면 `small` 또는 `medium` |
| `ANTHROPIC_API_KEY` | – | 설정에 저장된 키가 없을 때 Claude에 사용 |

## 프로젝트 구조

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## 개발

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

API 경로를 바꾸기 전에 [docs/specs.md](../specs.md)를 읽어 주세요. 웹 앱과 확장 프로그램 모두 이 문서에 의존합니다.

## 사용 기술

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[Ultimate Vocal Remover의 MDX-Net 모델](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## 라이선스

[MIT](../../LICENSE). 영상과 자막 다운로드는 각 사이트의 약관을 따릅니다. Tarjuman은 시청하고 각색할 수 있도록 허락된 콘텐츠에만 사용하세요.
