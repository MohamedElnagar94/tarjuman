<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman-Symbol: der arabische Buchstabe Taa unter einem Wiedergabezeichen">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Jedes Video auf Arabisch ansehen.</strong><br>
  Synchrone Übersetzung, natürliche Live-Synchronisation, synchronisierte MP4s und eine Browser-Erweiterung. Alles läuft auf deinem eigenen Rechner.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="MIT-Lizenz" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1F2E8C">
  <img alt="Vue 3" src="https://img.shields.io/badge/vue-3-1F2E8C">
  <img alt="Chrome MV3" src="https://img.shields.io/badge/chrome-MV3-F0922B">
</p>

<p align="center">
  <a href="../../README.md">English</a> ·
  <a href="README.ar.md">العربية</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.es.md">Español</a> ·
  <b>Deutsch</b> ·
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
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="Tarjuman spielt ein YouTube-Video mit arabischen Untertiteln ab, das Synchronisationsfeld ist geöffnet" width="900">
</p>

## Was es kann

Füge einen YouTube-Link ein, lade ein Video von deinem Rechner hoch oder gib einen Link von fast jeder beliebigen Website an.

- **Synchrone Untertitel.** Arabische Untertitel erscheinen Zeile für Zeile im Video, auf Wunsch mit der Originalsprache darunter. Automatisch erzeugte Untertitel werden vor der Übersetzung zu ganzen Sätzen zusammengesetzt.
- **Live-Synchronisation, die menschlich klingt.** Eine neuronale arabische Stimme spricht jeden Satz im Takt des Sprechers, auf Ägyptisch, Saudi-Arabisch, Emiratisch, Syrisch, Jordanisch, Libanesisch, Marokkanisch oder Irakisch. Kein Satz wird abgeschnitten oder übersprungen, und das Video pausiert nur, wenn die Synchronisation deutlich zurückliegt.
- **Synchronisiertes MP4.** Exportiere das Video mit arabischem Voice-over. Dabei lässt sich die Stimme des ursprünglichen Sprechers entfernen, während Musik und Effekte erhalten bleiben; jeder Sprecher bekommt eine passende männliche oder weibliche Stimme, und Untertitel können eingebettet oder eingebrannt werden.
- **Keine Untertitel? Kein Problem.** Whisper transkribiert den Ton auf deinem Rechner, anschließend wird das Transkript übersetzt.
- **Untertiteldateien.** Lade SRT, VTT oder reinen Text herunter, auf Arabisch oder zweisprachig, oder ein untertiteltes MP4, das sich direkt teilen lässt.
- **Ganze Playlists.** Gib einen Playlist- oder Kanal-Link an, um für jedes enthaltene Video Untertitel, untertitelte oder synchronisierte Videos zu erstellen.
- **Frag das Video** (optionale KI). Erhalte eine Zusammenfassung, die wichtigsten Punkte, anklickbare Kapitel und Antworten, die direkt zu der Stelle springen, an der das Video deine Frage behandelt. Funktioniert mit Claude oder jedem OpenAI-kompatiblen Anbieter (Gemini, Groq, OpenRouter, Ollama).
- **Englisch lernen.** Tippe auf ein Wort, um seine Bedeutung zu sehen, speichere es mit seinem Satz, wiederhole es später und exportiere es nach Anki. Du kannst auch einen Satz wiederholen, nach jeder Zeile pausieren oder die Untertitel verwischen, um dich selbst zu testen.
- **Browser-Erweiterung.** Nutze dieselben Untertitel und dieselbe Synchronisation direkt auf YouTube, auf Websites, deren Player Untertitel hat (Coursera, Udemy und andere), oder auf jeder anderen Website, indem der Ton des Tabs mitgehört wird.

Auch andere Sprachen funktionieren: Französisch, Spanisch, Deutsch, Türkisch und Englisch sind als Zielsprachen integriert.

## Schnellstart

Du brauchst **Python 3.11+** und **Node.js 20+**.

**Windows:** Doppelklick auf `start.cmd`.

**macOS / Linux:**

```sh
./start.sh
```

Beim ersten Start wird alles installiert: die Python-Pakete, die arabische Offline-Stimme und ein Build der Web-App. Danach öffnet sich die App unter `http://127.0.0.1:4318`. Bei späteren Starts ist sie in wenigen Sekunden bereit. Um sie auf dem Handy zu nutzen, öffne die Adresse, die sie für dein WLAN ausgibt.

<details>
<summary>Manuelle Einrichtung</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Befehle

| Befehl | Funktion |
|---|---|
| `python -m tarjuman` | Startet die App (`--port`, `--host 127.0.0.1` nur für diesen Rechner, `--no-open`) |
| `python -m tarjuman subs <link>` | Schreibt Untertiteldateien nach `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Installiert oder repariert alles |
| `python -m tarjuman update` | Aktualisiert yt-dlp und den Sprach-Client, falls Downloads oder Stimmen nicht mehr funktionieren |
| `python -m tarjuman doctor` | Prüft jede Komponente |

## Die Browser-Erweiterung

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Das Popup der Tarjuman-Erweiterung" width="320">
</p>

1. Einmal bauen: `npm --prefix extension install && npm --prefix extension run build`.
2. Öffne `chrome://extensions` (oder `edge://extensions`), aktiviere den **Entwicklermodus**, klicke auf **Entpackte Erweiterung laden** und wähle `extension/dist`.
3. Lass die App laufen, öffne ein Video und klicke auf das Tarjuman-Symbol oder drücke <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

Die Erweiterung kommuniziert ausschließlich mit der App auf deinem Rechner. Ihr Kit für den Chrome Web Store (Eintragstext, Begründungen der Berechtigungen, Datenschutzerklärung, Werbebilder) liegt in [`extension/store`](../../extension/store).

## Wie die Synchronisation im Takt bleibt

Untertitelzeilen werden zu ganzen Sätzen zusammengeführt, und Füllwörter werden entfernt. Anschließend wird die Geschwindigkeit jedes Satzes anhand eines Vorausschaufensters von etwa 12 Sekunden gewählt: Ein Satz mit viel Luft leiht einem gedrängten Satz Zeit, und die Geschwindigkeit ändert sich allmählich statt sprunghaft. Bevor der Browser irgendetwas abspielt, synthetisiert und misst der Server jeden Satz, sodass der Plan auf echten Dauern statt auf Schätzungen beruht. Fällt die Synchronisation trotzdem zurück, werden die nächsten Sätze etwas schneller abgespielt; das Video pausiert erst, wenn der Abstand etwa zwei Sekunden überschreitet. Springst du an eine beliebige Stelle, setzt die Synchronisation genau dort wieder ein.

Das vollständige Design steht in [docs/implementation.md](../implementation.md).

## Datenschutz

Tarjuman arbeitet lokal. Deine Videos, Untertitel, gespeicherten Wörter, Einstellungen und dein API-Schlüssel bleiben im Ordner `data/` auf deinem Rechner. Die App kontaktiert YouTube (Untertitel und Downloads), Google Translate und MyMemory (Übersetzung), den Edge-Sprachdienst von Microsoft (Sprachausgabe) und, nur wenn du es aktivierst, den KI-Anbieter deiner Wahl. Es gibt keine Konten, keine Analysen und kein Tracking. Die API lehnt Anfragen von anderen Websites ab, und die KI-Einstellungen lassen sich nur an dem Rechner ändern, auf dem die App läuft.

## Konfiguration

| Umgebungsvariable | Standard | Bedeutung |
|---|---|---|
| `TARJUMAN_HOME` | Projektordner | Wo `data/` liegt |
| `TARJUMAN_PORT` | `4318` | Erster Port, der versucht wird (ist er belegt, wird der nächste genommen; die Erweiterung zieht mit) |
| `TARJUMAN_HOST` | `0.0.0.0` | Mit `127.0.0.1` ist die App aus dem WLAN nicht erreichbar |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` oder `medium` für genauere Transkription (langsamer) |
| `ANTHROPIC_API_KEY` | – | Wird für Claude verwendet, wenn in den Einstellungen kein Schlüssel gespeichert ist |

## Projektstruktur

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Entwicklung

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

Lies [docs/specs.md](../specs.md), bevor du eine API-Route änderst: Sowohl die Web-App als auch die Erweiterung hängen davon ab.

## Erstellt mit

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[MDX-Net-Modellen von Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Lizenz

[MIT](../../LICENSE). Das Herunterladen von Videos und Untertiteln unterliegt den Bedingungen der jeweiligen Website. Nutze Tarjuman für Inhalte, die du ansehen und bearbeiten darfst.
