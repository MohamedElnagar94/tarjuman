<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Icona di Tarjuman: la lettera araba taa sotto un simbolo di riproduzione">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Guarda qualsiasi video in arabo.</strong><br>
  Traduzione sincronizzata, doppiaggio dal vivo naturale, MP4 doppiati e un'estensione per il browser. Tutto gira sul tuo computer.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="Licenza MIT" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <b>Italiano</b> ·
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
  <img src="../screenshots/watch.png" alt="Tarjuman che riproduce un video di YouTube con sottotitoli in arabo e il pannello del doppiaggio aperto" width="900">
</p>

## Cosa fa

Incolla un link di YouTube, carica un video dal tuo computer o dagli un link da quasi qualsiasi sito.

- **Sottotitoli sincronizzati.** I sottotitoli in arabo compaiono sul video riga per riga, con la lingua originale sotto, se vuoi. I sottotitoli generati automaticamente vengono ricomposti in frasi complete prima della traduzione.
- **Doppiaggio dal vivo che suona umano.** Una voce araba neurale pronuncia ogni frase a tempo con chi parla, in arabo egiziano, saudita, emiratino, siriano, giordano, libanese, marocchino o iracheno. Nessuna frase viene troncata o saltata, e il video si mette in pausa solo quando il doppiaggio resta parecchio indietro.
- **MP4 doppiato.** Esporta il video con la voce fuori campo in arabo. Può rimuovere la voce di chi parla nell'originale mantenendo musica ed effetti, assegnare a ogni persona una voce maschile o femminile adatta e incorporare o imprimere i sottotitoli.
- **Niente sottotitoli? Nessun problema.** Whisper trascrive l'audio sul tuo computer, poi la trascrizione viene tradotta.
- **File di sottotitoli.** Scarica SRT, VTT o testo semplice, in arabo o bilingue, oppure un MP4 sottotitolato pronto da condividere.
- **Playlist intere.** Dagli il link di una playlist o di un canale per creare sottotitoli, video sottotitolati o video doppiati per ogni video contenuto.
- **Chiedi al video** (IA facoltativa). Ottieni un riassunto, i punti chiave, capitoli cliccabili e risposte che saltano al momento in cui il video tratta la tua domanda. Funziona con Claude o con qualsiasi provider compatibile con OpenAI (Gemini, Groq, OpenRouter, Ollama).
- **Impara l'inglese.** Tocca una parola per vederne il significato, salvala con la sua frase, ripassala più tardi ed esportala in Anki. Puoi anche ripetere una frase, mettere in pausa dopo ogni riga o sfocare i sottotitoli per metterti alla prova.
- **Estensione per il browser.** Usa gli stessi sottotitoli e lo stesso doppiaggio direttamente su YouTube, sui siti il cui player ha i sottotitoli (Coursera, Udemy e altri) o su qualsiasi altro sito ascoltando l'audio della scheda.

Funzionano anche altre lingue: francese, spagnolo, tedesco, turco e inglese sono integrate come lingue di destinazione.

## Avvio rapido

Ti servono **Python 3.11+** e **Node.js 20+**.

**Windows:** fai doppio clic su `start.cmd`.

**macOS / Linux:**

```sh
./start.sh
```

Il primo avvio installa tutto: i pacchetti Python, la voce araba offline e una build dell'app web. Poi l'app si apre su `http://127.0.0.1:4318`. Agli avvii successivi parte in un paio di secondi. Per usarla dal telefono, apri l'indirizzo che mostra per la tua rete Wi-Fi.

<details>
<summary>Installazione manuale</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Comandi

| Comando | Cosa fa |
|---|---|
| `python -m tarjuman` | Avvia l'app (`--port`, `--host 127.0.0.1` solo per questo computer, `--no-open`) |
| `python -m tarjuman subs <link>` | Scrive i file di sottotitoli in `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Installa o ripara tutto |
| `python -m tarjuman update` | Aggiorna yt-dlp e il client delle voci, se i download o le voci smettono di funzionare |
| `python -m tarjuman doctor` | Controlla ogni componente |

## L'estensione per il browser

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Il popup dell'estensione Tarjuman" width="320">
</p>

1. Compilala una volta: `npm --prefix extension install && npm --prefix extension run build`.
2. Apri `chrome://extensions` (o `edge://extensions`), attiva la **Modalità sviluppatore**, fai clic su **Carica estensione non pacchettizzata** e scegli `extension/dist`.
3. Lascia l'app in esecuzione, apri un video e fai clic sull'icona di Tarjuman, oppure premi <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

L'estensione comunica solo con l'app sul tuo computer. Il suo kit per il Chrome Web Store (testo della scheda, motivazioni delle autorizzazioni, informativa sulla privacy, immagini promozionali) si trova in [`extension/store`](../../extension/store).

## Come il doppiaggio resta sincronizzato

Le righe dei sottotitoli vengono unite in frasi complete e gli intercalari vengono eliminati. La velocità di ogni frase viene poi scelta in base a una finestra di anticipo di circa 12 secondi, così una frase con margine presta tempo a una più fitta e la velocità cambia gradualmente invece di saltare. Prima che il browser riproduca qualcosa, il server sintetizza e misura ogni frase, quindi il piano si basa su durate reali e non su stime. Se il doppiaggio resta comunque indietro, le frasi successive vengono riprodotte un po' più velocemente; il video va in pausa solo quando il ritardo supera circa due secondi. Spostandoti in qualsiasi punto, il doppiaggio riprende esattamente da lì.

Il progetto completo è descritto in [docs/implementation.md](../implementation.md).

## Privacy

Tarjuman è pensato per funzionare in locale. I tuoi video, sottotitoli, parole salvate, impostazioni e chiave API restano nella cartella `data/` del tuo computer. L'app contatta YouTube (sottotitoli e download), Google Translate e MyMemory (traduzione), il servizio vocale Edge di Microsoft (sintesi vocale) e, solo se lo attivi, il provider di IA che scegli. Niente account, statistiche o tracciamento. L'API rifiuta le richieste provenienti da altri siti, e le impostazioni dell'IA si possono modificare solo dal computer su cui gira l'app.

## Configurazione

| Variabile d'ambiente | Predefinito | Significato |
|---|---|---|
| `TARJUMAN_HOME` | cartella del progetto | Dove viene tenuta `data/` |
| `TARJUMAN_PORT` | `4318` | Prima porta da provare (se è occupata passa alla successiva; l'estensione si adegua) |
| `TARJUMAN_HOST` | `0.0.0.0` | Usa `127.0.0.1` per non esporre l'app sulla tua rete Wi-Fi |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` o `medium` per una trascrizione più accurata (più lenta) |
| `ANTHROPIC_API_KEY` | – | Usata per Claude quando nelle impostazioni non è salvata alcuna chiave |

## Struttura del progetto

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Sviluppo

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

Leggi [docs/specs.md](../specs.md) prima di modificare una route dell'API: sia l'app web sia l'estensione ne dipendono.

## Realizzato con

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[i modelli MDX-Net di Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Licenza

[MIT](../../LICENSE). Il download di video e sottotitoli è soggetto ai termini di ciascun sito. Usa Tarjuman per contenuti che hai il diritto di guardare e adattare.
