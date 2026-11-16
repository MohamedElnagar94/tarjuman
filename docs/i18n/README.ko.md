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

YouTube 링크를 붙여 넣거나, 컴퓨터에서 영상이나 오디오 파일을 업로드하거나, 직접 목소리를 녹음하거나, 거의 모든 사이트의 링크를 넣으세요.

- **동기화 자막.** 아랍어 자막이 영상 위에 한 줄씩 표시되며, 원하면 원래 언어를 그 아래에 함께 볼 수 있습니다. 자동 생성 자막은 번역 전에 완전한 문장으로 다시 묶입니다. 문장 부호가 전혀 없으면 YouTube의 단어별 타이밍을 이용해 화자가 실제로 쉬는 지점에서 나눕니다.
- **사람 목소리 같은 실시간 더빙.** 신경망 아랍어 음성이 화자의 타이밍에 맞춰 각 문장을 읽어 줍니다. 이집트, 사우디, 에미리트, 시리아, 요르단, 레바논, 모로코, 이라크 아랍어를 지원합니다. 문장이 잘리거나 건너뛰는 일은 없습니다. 화자가 빠르게 말하면 음성을 서두르게 하는 대신 음성이 따라잡을 때까지 영상이 살짝 느려지고, 직접 영상을 느리게 하면 그만큼의 시간이 음성에 주어집니다. 철자는 같지만 읽는 법이 다른 단어는 영어 원문을 근거로 문장의 뜻에 맞게 읽습니다(الجَمَل '낙타'가 아니라 الجُمَل '문장들').
- **더빙 MP4.** 아랍어 보이스오버를 입힌 영상을 내보냅니다. 음악과 효과음은 그대로 두고 원래 화자의 목소리만 제거할 수 있고, 화자마다 어울리는 남성 또는 여성 음성을 지정하며, 자막을 삽입하거나 영상에 입힐 수 있습니다.
- **자막이 없어도 괜찮습니다.** Whisper가 내 컴퓨터에서 오디오를 받아쓰고, 그 내용을 번역합니다. 설정 → 받아쓰기에서는 내 컴퓨터(메모리, 그래픽 카드, 프로세서)를 살펴보고 모델을 추천하며 그 이유도 알려 줍니다. 녹음, 영상, 실시간 듣기에 각각 다른 모델을 고를 수도 있습니다. 아랍어 음성에는 방언(이집트, 걸프, 레반트 등)으로 학습한 모델이 있는데, 이집트 방언 음성 메모로 진행한 테스트에서 표준 모델보다 틀린 단어가 훨씬 적었습니다. 정확히 받아써야 할 단어 목록(이름, 제품명, 아랍어 중에 말하는 영어 용어 등)을 각각 어떻게 표기할지와 함께 추가할 수 있고, 원하면 AI 제공자가 받아쓴 내용을 나중에 교정하게 할 수도 있습니다. CTranslate2 형식의 Whisper 모델이라면 Hugging Face나 내 컴퓨터의 폴더에서 추가할 수 있으며, 내려받은 모델은 삭제해 공간을 확보할 수 있습니다.
- **오디오 파일과 음성 메모.** MP3, M4A, WAV, OGG, Opus, FLAC 또는 WhatsApp 음성 메모를 업로드하거나 마이크로 바로 녹음하세요. 빈 화면의 영상 대신 움직이는 파형이 표시되고 받아쓴 내용도 동기화됩니다. 자막, 더빙된 M4A, 또는 파형과 입힌 자막이 들어간 공유용 영상으로 내보낼 수 있습니다.
- **자막 파일.** SRT, VTT 또는 일반 텍스트를 아랍어나 이중 언어로 내려받거나, 바로 공유할 수 있는 자막 입힌 MP4를 받으세요.
- **재생목록 전체.** 재생목록이나 채널 링크를 넣으면 그 안의 모든 영상에 대해 자막, 자막 영상 또는 더빙 영상을 만듭니다.
- **영상에게 묻기** (선택형 AI). 요약, 핵심 내용, 클릭할 수 있는 챕터, 그리고 질문과 관련된 장면으로 바로 이동하는 답변을 받아 보세요. Claude 또는 OpenAI 호환 제공자(Gemini, Groq, OpenRouter, Ollama)와 함께 작동합니다.
- **내 마음대로 조절하는 시청 페이지.** 영상 옆의 스크립트는 말하는 단어를 차례로 강조하고, 화자가 바뀌는 지점과 [music] 같은 소리를 표시하며, 검색도 할 수 있습니다. 아무 줄이나 클릭하면 그 지점으로 이동합니다. 영상 소유자가 만든 챕터(또는 AI 요약의 챕터)가 스크립트의 해당 부분 제목이 되고 타임라인에도 표시됩니다. 영상 아래 타임라인은 자막 줄이 있는 위치를 보여 주고, 플레이어 뒤로는 영상 자체의 색으로 은은한 빛이 번지며, 시네마 모드(<kbd>T</kbd>)는 나머지를 모두 어둡게 합니다. 이 기능들은 모두 설정 → 시청에서 끄거나 조절할 수 있습니다. 키보드: <kbd>→</kbd> 다음 줄, <kbd>←</kbd> 이전 줄, <kbd>R</kbd> 반복, <kbd>K</kbd> 재생 또는 일시 정지, <kbd>?</kbd> 전체 목록 보기(아랍어 키보드 배열에서도 작동합니다).
- **영어 공부.** 단어를 탭하면 뜻이 나오고, 문장과 함께 저장해 나중에 복습하며, Anki로 내보낼 수 있습니다. 문장을 반복하거나, 한 줄마다 멈추거나, 자막을 흐리게 해서 스스로 테스트할 수도 있습니다.
- **브라우저 확장 프로그램.** 같은 자막과 더빙을 YouTube에서 바로, 다른 사이트에 삽입된 YouTube 영상에서, 플레이어에 자막이 있는 사이트(Coursera, Udemy 등)에서, 다른 사이트의 플레이어를 삽입한 영화·애니메이션 사이트에서, 또는 탭의 오디오를 듣는 방식으로 다른 어떤 사이트에서든 사용하세요. YouTube에서는 영상 옆 스크립트, 클릭한 단어의 뜻, 한 줄씩 이동하는 단축키, 그리고 앱에서 이어 보기 버튼이 추가됩니다.
- **휴대폰에서.** 같은 Wi-Fi에 연결된 휴대폰이라면 어떤 기기에서든 앱을 열 수 있습니다.

**74개 언어**로 번역하고 더빙할 수 있으며, 언어마다 원어민 음성이 있습니다(일본어는 일본어답게, 힌디어는 힌디어답게 들립니다). 그리고 이 모든 것이 인터넷 없이도 작동할 수 있습니다.

- **오프라인 번역:** 언어 모델을 한 번 내려받으면(설정 → 오프라인 번역) Google을 쓸 수 없을 때 또는 항상 내 컴퓨터에서 번역합니다.
- **오프라인 음성**은 31개 언어를 지원하며 일반 노트북에서도 실시간으로 더빙합니다.
- **음성 팩**은 원할 때만 설치합니다. MP4를 **원래 화자 본인의 목소리**로 더빙하거나(실험적 기능), 성능 좋은 그래픽 카드가 있는 컴퓨터에서 **아랍어 방언 음성**(이집트, 이라크, 모로코…)으로 더빙할 수 있습니다.

## 스크린샷

<table>
  <tr>
    <td width="50%"><img src="../screenshots/home.png" alt="홈: 링크 붙여넣기, 영상 업로드, 최근 영상과 컴퓨터 상태"></td>
    <td width="50%"><img src="../screenshots/watch-en.png" alt="동기화된 자막과 스크립트를 띄워 놓고 영상 시청, 영어 화면과 라이트 테마"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/library.png" alt="내 파일: 작업, 재생목록 일괄 작업, 업로드한 영상과 완성된 파일"></td>
    <td><img src="../screenshots/settings.png" alt="설정: AI 제공업체, 발음 사전, 기본값과 화면 모양"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/extension-overlay.png" alt="YouTube에서 아랍어 자막을 보여 주는 확장 프로그램"></td>
    <td><img src="../screenshots/extension-welcome.png" alt="앱에 연결된 확장 프로그램의 환영 페이지"></td>
  </tr>
</table>

<p align="center">
  <img src="../screenshots/phone-home.png" alt="휴대폰의 홈 화면" width="260">
  <img src="../screenshots/phone-watch.png" alt="휴대폰에서 시청" width="260">
</p>

## 빠른 시작

### Windows 설치 프로그램

[Releases](https://github.com/MohamedElnagar94/tarjuman/releases) 페이지에서 `Tarjuman-Setup-<version>.exe`를 내려받아 실행하세요. 자체 Python, 모든 패키지, 웹 앱, 브라우저 확장 프로그램이 함께 들어 있어 Python도 Node.js도 필요 없습니다. 관리자 권한을 한 번 요청하고, Program Files에 설치되며, 방화벽은 건드리지 않습니다. 그런 다음 Tarjuman은 여느 데스크톱 앱처럼 자체 창에서 열리며, 콘솔 창도 브라우저 탭도 없습니다. 기본적으로 창을 닫으면 앱이 종료되지만, 설정 → 데스크톱에서 대신 알림 영역에 남겨 두거나, 브라우저 확장 프로그램을 위해 엔진을 계속 실행하거나, Windows와 함께 시작하도록 할 수 있습니다. (이 창은 앱 모드로 실행되는 Microsoft Edge이며, 모든 Windows 10과 11에 들어 있습니다. 추가로 설치되는 것은 없습니다.)

- 설치 프로그램이 "unable to create the directory ...\Temp\is-*.tmp, access is denied"라는 메시지와 함께 바로 멈춘다면, 설치 파일이 낮은 무결성으로 표시된 폴더에 있는 것입니다(일부 샌드박스 도구는 작업 폴더를 이렇게 표시하며, 이때 `icacls <file>`에 `Low Mandatory Level`이 나옵니다). Windows는 이런 파일을 더 적은 권한으로 실행합니다. 다운로드 폴더 같은 다른 폴더로 복사한 뒤 복사본을 실행하세요.
- 설치 프로그램은 아직 코드 서명이 되어 있지 않아 Windows SmartScreen이 "알 수 없는 게시자"라고 표시할 수 있습니다. *추가 정보 → 실행*을 선택하세요.
- 처음 시작할 때 오프라인 아랍어 음성(약 60 MB)을 백그라운드에서 내려받습니다. Whisper 모델은 영상에 처음 필요해질 때 자동으로 내려받습니다.
- 업데이트: 설정 → 업데이트에서 새 버전에 추가되고 수정된 내용을 보여 주며, 클릭 한 번으로 설치합니다(켜 두면 자동으로 설치됩니다).
- 영상, 자막, 설정, `.env`는 프로그램과 분리된 `%LOCALAPPDATA%\Tarjuman`에 보관됩니다. 업데이트해도 그대로 유지되며, 제거할 때는 삭제할지 묻습니다.
- 시작 메뉴에 확장 프로그램 폴더 바로 가기가 있어, `chrome://extensions`의 *압축해제된 확장 프로그램을 로드합니다*에 사용할 수 있습니다.

문제가 있나요? [문제 해결](../troubleshooting.md)을 참고하세요. 버전별 변경 사항은 [Changelog](../../CHANGELOG.md)에 있습니다.

### Linux (AppImage)

[Releases](https://github.com/MohamedElnagar94/tarjuman/releases) 페이지에서 `Tarjuman-<version>-x86_64.AppImage`를 내려받아 실행 권한을 주고 실행하세요. Windows 설치 프로그램처럼 자체 Python, 모든 패키지, 웹 앱, 확장 프로그램이 함께 들어 있습니다.

```sh
chmod +x Tarjuman-*-x86_64.AppImage
./Tarjuman-*-x86_64.AppImage
```

- Chrome, Chromium 또는 Edge가 설치되어 있으면 자체 창에서 열리고, 그렇지 않으면 기본 브라우저에서 열립니다(이 경우 로그아웃하거나 `pkill -f "tarjuman app"`을 실행할 때까지 계속 실행됩니다).
- 데이터는 `~/.local/share/Tarjuman`에 보관됩니다. 설정 → 업데이트는 새 AppImage를 검증한 뒤 기존 파일과 교체합니다. 새 버전을 사용하려면 Tarjuman을 다시 시작하세요.
- FUSE가 없다는 메시지가 나오면(일부 배포판과 WSL) `--appimage-extract-and-run`을 붙여 실행하거나 `libfuse2`를 설치하세요.
- 알림 영역 아이콘과 데스크톱 설정은 아직 Windows 전용입니다.

### 소스에서 실행

**Python 3.11+**와 **Node.js 20+**가 필요합니다.

**Windows:** `start.cmd`를 더블클릭하세요. Windows가 알 수 없는 게시자의 스크립트를 실행할지 묻는다면 `powershell -ExecutionPolicy Bypass -File scripts/create-shortcut.ps1`로 바탕 화면 바로 가기를 한 번 만들고 거기서 Tarjuman을 실행하세요. 같은 스크립트를 Windows 자체의 `cmd.exe`로 실행하므로 확인 창이 나타나지 않습니다.

**macOS / Linux:**

```sh
./start.sh
```

Debian, Ubuntu, Kali에서는 `python3-venv`가 없으면 먼저 설치하세요(`sudo apt install python3-venv`).

처음 실행하면 Python 패키지, 오프라인 아랍어 음성, 웹 앱 빌드까지 모든 것이 설치됩니다. 그런 다음 앱이 `http://127.0.0.1:4318`에서 열립니다. 이후에는 몇 초 만에 시작됩니다. 휴대폰에서 사용하려면 Wi-Fi용으로 출력되는 주소를 여세요. Windows에서 휴대폰이 접속하지 못하면 `scripts/allow-phone.ps1`을 관리자 권한으로 한 번 실행하세요. 집 Wi-Fi를 개인 네트워크로 지정하고, Tarjuman의 포트를 개인 네트워크에서만 엽니다.

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
| `python -m tarjuman app` | 브라우저 탭 대신 자체 창(앱 모드의 Edge 또는 Chrome)에서 앱 시작. Windows에서는 알림 영역 아이콘도 표시(`--background`를 붙이면 창 없이 알림 영역에서 시작) |
| `python -m tarjuman subs <link>` | 자막 파일을 `data/output`에 저장 (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | 모든 것을 설치하거나 복구 |
| `python -m tarjuman update` | 다운로드나 음성이 작동하지 않을 때 yt-dlp와 음성 클라이언트를 업데이트 |
| `python -m tarjuman doctor` | 모든 구성 요소 점검 |

## 브라우저 확장 프로그램

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Tarjuman 확장 프로그램 팝업" width="320">
</p>

[Chrome 웹 스토어](https://chromewebstore.google.com/detail/gcfnomfbpenbhdebopmpdfamlaiodflp)에서 바로 설치하거나, 아래 단계에 따라 소스에서 빌드하세요.

1. 한 번 빌드합니다: `npm --prefix extension install && npm --prefix extension run build`.
2. `chrome://extensions`(또는 `edge://extensions`)를 열고, **개발자 모드**를 켠 뒤, **압축해제된 확장 프로그램을 로드합니다**를 클릭하고 `extension/dist`를 선택합니다.
3. 앱을 실행한 채로 영상을 열고 Tarjuman 아이콘을 클릭하거나 <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>를 누릅니다.
4. 옵션 페이지에서 자막 글꼴, 확장 프로그램 언어(브라우저 언어, 아랍어 또는 영어), 단축키, 그리고 YouTube에서 자동으로 시작할지 여부(안 함, 항상, 또는 선택한 채널에서만)를 설정합니다.

Chrome에 *Proceed with caution: this extension is not trusted by Enhanced Safe Browsing*가 표시되면, 게시자가 Chrome 웹 스토어에 새로 등록되었기 때문입니다. Chrome은 새 게시자가 몇 달 동안 스토어 정책을 지킬 때까지 이 경고를 표시하며, 향상된 보호를 켠 사용자에게만 보입니다. 확장 프로그램은 스토어 검토를 통과했고 [소스 코드](https://github.com/MohamedElnagar94/tarjuman/tree/main/extension)는 공개되어 있습니다. *Continue to install*을 선택하세요.

번역하는 동안:

- YouTube에서 **영상 옆 스크립트**: 모든 줄이 표시되고 현재 줄이 강조됩니다. 줄을 클릭해 그 지점으로 이동하거나 검색하세요.
- 원문 줄에서 **단어를 클릭**하면 뜻이 나오고, 문장과 함께 앱의 *내 단어*에 저장할 수 있습니다.
- **단축키:** <kbd>Alt</kbd>+<kbd>→</kbd> 다음 줄, <kbd>Alt</kbd>+<kbd>←</kbd> 이전 줄, <kbd>Alt</kbd>+<kbd>↓</kbd> 반복, <kbd>Alt</kbd>+<kbd>S</kbd> 자막, <kbd>Alt</kbd>+<kbd>V</kbd> 더빙, <kbd>Alt</kbd>+<kbd>T</kbd> 스크립트.
- **타이밍:** 자막 줄이 말보다 먼저 또는 늦게 나오면 <kbd>Alt</kbd>+<kbd>[</kbd>와 <kbd>Alt</kbd>+<kbd>]</kbd>로 옮기세요(더빙도 함께 움직입니다).
- 같은 지점에서 **앱으로 열기**: 내보내기와 전체 시청 페이지를 쓸 수 있습니다.
- YouTube 미니 플레이어에서도 계속 작동하고, 강의 사이트에서는 다음 강의로 따라가며, 사이트가 영상만 전체 화면으로 띄워도 자막 줄을 계속 보여 줍니다.

확장 프로그램은 내 컴퓨터의 앱과만 통신합니다. Chrome Web Store 등록 키트(등록 문구, 권한 사유, 개인정보처리방침, 홍보 이미지)는 [`extension/store`](../../extension/store)에 있습니다.

## 더빙이 동기화를 유지하는 방법

자막 줄은 완전한 문장으로 합쳐지고, 말버릇 같은 군말은 제거됩니다. 그런 다음 약 12초 길이의 선행 창을 보고 각 문장의 속도를 정합니다. 여유 있는 문장이 빠듯한 문장에 시간을 빌려주고, 속도는 갑자기 튀지 않고 점진적으로 바뀝니다. 브라우저가 각 구간의 첫 문장들을 재생하기 전에 서버가 이를 합성해 길이를 재므로 계획은 추측이 아니라 실제 길이에 기반하며, 다음 구간은 백그라운드에서 미리 준비합니다. 그래도 더빙이 뒤처지면 음성이 따라잡을 때까지 영상이 사용자 속도의 85%로 느려지고, 차이가 약 2초를 넘을 때만 일시 정지됩니다. 속도 조절은 재생 속도를 따릅니다. 어디로 이동하든 더빙은 정확히 그 지점에서 다시 시작됩니다. 무료 번역기가 요청 수를 제한하면 두 번째 Google 엔드포인트, 그다음에는 YouTube 자체 번역이 더빙을 계속 이어 갑니다.

전체 설계는 [docs/implementation.md](../implementation.md)에 있습니다.

## 개인정보 보호

Tarjuman은 로컬 우선입니다. 영상, 자막, 저장한 단어, 설정, API 키는 내 컴퓨터의 `data/` 폴더에 남습니다. 앱은 YouTube(자막과 다운로드), Google Translate와 MyMemory(번역), Microsoft의 Edge 음성 서비스(음성), 그리고 직접 켠 경우에만 선택한 AI 제공자에 연결합니다. 계정, 분석, 추적은 없습니다. 영상과 오디오는 절대 업로드되지 않습니다.

| 기능 | 내 컴퓨터 밖으로 나가는 것 | 보내는 곳 | 아무것도 보내지 않으려면 |
|---|---|---|---|
| YouTube 자막 | 영상 링크 | YouTube | 파일을 업로드하세요. 로컬에서 받아씁니다 |
| 번역 | 영상의 문장(텍스트) | Google Translate, 그다음 MyMemory | 오프라인 번역 모델(설정 → 오프라인 번역) |
| 더빙 음성 | 번역된 각 문장과 음성 이름 | Microsoft Edge 음성, 그다음 Google | 오프라인 음성(Supertonic, 31개 언어. 아랍어는 Piper)과 음성 팩 |
| 영상 다운로드 | 영상 요청 | 영상을 호스팅하는 사이트 | 이미 내 컴퓨터에 있는 파일 |
| AI (선택 사항, 기본적으로 꺼짐) | 영상의 텍스트와 내 질문 | 선택한 제공자 | 꺼 두거나 Ollama 같은 로컬 서버 사용 |
| 모델 다운로드 | 다운로드 요청, 한 번만 | Hugging Face, GitHub, 헬싱키 대학교(번역 모델), PyTorch와 PyPI(음성 팩) | 첫 다운로드 이후에는 없음 |
| 업데이트 확인 | 새 버전 목록 요청, 몇 시간마다 | GitHub | 설정 → 업데이트에서 "자동으로 업데이트 확인" 끄기 |
| 받아쓰기 교정 (선택 사항, 기본적으로 꺼짐) | 받아쓴 텍스트 | 선택한 AI 제공자 | 꺼 두기. 단어 목록은 이 기능 없이도 작동합니다 |
| 음성 인식, 음악 분리, 내 파일과 녹음 | 없음 | – | 항상 로컬 |

같은 표가 앱의 설정 → 개인정보 보호에도 있습니다. API는 다른 웹사이트에서 온 요청을 거부하며, AI 설정은 앱을 실행 중인 컴퓨터에서만 변경할 수 있습니다.

## 설정

프로젝트 폴더에서 `.env.example`을 `.env`로 복사한 뒤 수정하세요. 모든 설정이 그 파일에 아랍어와 영어로 설명되어 있습니다. 이 파일은 시작할 때 읽히므로 변경한 뒤에는 Tarjuman을 다시 시작하세요. 실제 환경에 설정된 변수가 파일보다 우선합니다.

| 환경 변수 | 기본값 | 의미 |
|---|---|---|
| `TARJUMAN_HOME` | 프로젝트 폴더 | `data/`를 두는 위치 |
| `TARJUMAN_PORT` | `4318` | 처음 시도할 포트 (사용 중이면 다음 번호로 넘어가며, 확장 프로그램도 따라갑니다) |
| `TARJUMAN_HOST` | `0.0.0.0` | Wi-Fi에서 앱에 접근하지 못하게 하려면 `127.0.0.1` 사용 |
| `TARJUMAN_WHISPER_MODEL` | (비어 있음) | 설정 → 받아쓰기에서 고르며, 그곳에서 내 컴퓨터에 맞는 모델을 추천합니다. 그 설정이 자동일 때는 여기 지정한 값이 사용됩니다 |
| `TARJUMAN_VOICE_CACHE_GB` | `2` | 저장된 더빙 음성의 용량 한도. 가장 오래 사용하지 않은 것부터 삭제됩니다 |
| `TARJUMAN_MAX_UPLOAD_GB` | `8` | 업로드할 수 있는 최대 영상 크기 |
| `TARJUMAN_PAIR_MINUTES` | `15` | 휴대폰 페어링 코드(QR)의 유효 시간. `0` = 새 코드를 만들 때까지 |
| `TARJUMAN_FETCH_PRIVATE` | 꺼짐 | 내 네트워크 내부 주소에서 다운로드를 허용하려면 `1`로 설정 |
| `TARJUMAN_HEAVY_JOBS` | `2` | 동시에 실행되는 무거운 작업(Whisper, 더빙, 자막 입히기)의 수. 메모리가 적은 컴퓨터에서는 `1` 사용 |
| `TARJUMAN_MAX_QUEUE` | `20` | 차례를 기다릴 수 있는 최대 작업 수 |
| `TARJUMAN_FORCE_ASR` | 꺼짐 | YouTube 자막을 무시하고 항상 Whisper로 받아쓰려면 `1`로 설정 |
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
cd backend && ../.venv/bin/python -m pytest      # Windows: ..\.venv\Scripts\python

# dub engine tests
npm test

# web app with hot reload (proxies the API to 127.0.0.1:4318)
npm --prefix frontend run dev

# extension: build, test, package a store zip
npm --prefix extension run build && npm --prefix extension test && npm --prefix extension run package
```

API 경로를 바꾸기 전에 [docs/specs.md](../specs.md)를 읽어 주세요. 웹 앱과 확장 프로그램 모두 이 문서에 의존합니다.

### Windows 설치 프로그램 빌드

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1   # build\windows\app: Python, packages, web app, extension
iscc /DAppVersion=3.0.0 installer\tarjuman.iss                # build\windows\Tarjuman-Setup-3.0.0.exe (Inno Setup 6)
```

*Windows installer* 워크플로가 GitHub에서 같은 작업을 합니다. Actions 탭에서 실행하거나, `v3.0.0` 같은 태그를 푸시해 설치 프로그램을 릴리스에 첨부하세요. 컴파일하기 전에 번들된 앱을 시작해 응답하는지 확인합니다.

### Linux AppImage 빌드

```sh
installer/linux/build.sh   # build/linux/Tarjuman-<version>-x86_64.AppImage (needs curl, python3, Node.js 20+)
```

python-build-standalone의 재배치 가능한 Python을 번들합니다. 같은 워크플로가 Windows 설치 프로그램과 함께 이것을 빌드하고, `v*` 태그가 붙으면 둘 다 게시합니다.

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
