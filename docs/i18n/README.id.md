<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Ikon Tarjuman: huruf Arab ta di bawah tanda putar">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Tonton video apa pun dalam bahasa Arab.</strong><br>
  Terjemahan tersinkron, sulih suara langsung yang alami, MP4 bersulih suara, dan ekstensi browser. Semuanya berjalan di komputer Anda sendiri.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="Lisensi MIT" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <b>Bahasa Indonesia</b> ·
  <a href="README.zh.md">中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="Tarjuman memutar video YouTube dengan subtitle Arab dan panel sulih suara terbuka" width="900">
</p>

## Apa yang dilakukannya

Tempel tautan YouTube, unggah video dari komputer Anda, atau berikan tautan dari hampir situs mana pun.

- **Subtitle tersinkron.** Subtitle Arab muncul di video baris demi baris, dengan bahasa aslinya di bawah jika Anda mau. Teks otomatis disusun ulang menjadi kalimat utuh sebelum diterjemahkan.
- **Sulih suara langsung yang terdengar seperti manusia.** Suara Arab neural mengucapkan setiap kalimat seiring pembicara, dalam bahasa Arab Mesir, Saudi, Emirat, Suriah, Yordania, Lebanon, Maroko, atau Irak. Tidak ada kalimat yang terpotong atau terlewat, dan video hanya dijeda jika sulih suara tertinggal cukup jauh.
- **MP4 bersulih suara.** Ekspor video dengan sulih suara Arab. Tarjuman dapat menghapus suara pembicara asli sambil mempertahankan musik dan efek, memberi tiap pembicara suara pria atau wanita yang sesuai, serta menyematkan atau menempelkan subtitle secara permanen.
- **Tidak ada teks? Tidak masalah.** Whisper mentranskripsikan audio di komputer Anda, lalu transkripnya diterjemahkan.
- **Berkas subtitle.** Unduh SRT, VTT, atau teks biasa, dalam bahasa Arab atau dwibahasa, atau MP4 bersubtitle yang siap dibagikan.
- **Seluruh playlist.** Berikan tautan playlist atau kanal untuk membuat subtitle, video bersubtitle, atau video bersulih suara bagi setiap video di dalamnya.
- **Tanya videonya** (AI opsional). Dapatkan ringkasan, poin-poin penting, bab yang dapat diklik, dan jawaban yang langsung melompat ke momen saat video membahas pertanyaan Anda. Bekerja dengan Claude atau penyedia apa pun yang kompatibel dengan OpenAI (Gemini, Groq, OpenRouter, Ollama).
- **Belajar bahasa Inggris.** Ketuk kata apa pun untuk melihat artinya, simpan beserta kalimatnya, ulangi nanti, dan ekspor ke Anki. Anda juga bisa mengulang kalimat, berhenti setelah tiap baris, atau mengaburkan subtitle untuk menguji diri sendiri.
- **Ekstensi browser.** Gunakan subtitle dan sulih suara yang sama langsung di YouTube, di situs yang pemutarnya punya teks (Coursera, Udemy, dan lainnya), atau di situs lain mana pun dengan mendengarkan audio tab.

Bahasa lain juga bisa: Prancis, Spanyol, Jerman, Turki, dan Inggris sudah tersedia sebagai bahasa target.

## Mulai cepat

Anda memerlukan **Python 3.11+** dan **Node.js 20+**.

**Windows:** klik dua kali `start.cmd`.

**macOS / Linux:**

```sh
./start.sh
```

Proses pertama memasang semuanya: paket Python, suara Arab luring, dan build aplikasi web. Setelah itu aplikasi terbuka di `http://127.0.0.1:4318`. Pada proses berikutnya, aplikasi siap dalam beberapa detik. Untuk memakainya dari ponsel, buka alamat yang ditampilkannya untuk Wi-Fi Anda.

<details>
<summary>Penyiapan manual</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Perintah

| Perintah | Fungsinya |
|---|---|
| `python -m tarjuman` | Menjalankan aplikasi (`--port`, `--host 127.0.0.1` khusus komputer ini, `--no-open`) |
| `python -m tarjuman subs <link>` | Menulis berkas subtitle ke `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Memasang atau memperbaiki semuanya |
| `python -m tarjuman update` | Memperbarui yt-dlp dan klien suara, jika unduhan atau suara berhenti berfungsi |
| `python -m tarjuman doctor` | Memeriksa setiap komponen |

## Ekstensi browser

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Popup ekstensi Tarjuman" width="320">
</p>

1. Build sekali: `npm --prefix extension install && npm --prefix extension run build`.
2. Buka `chrome://extensions` (atau `edge://extensions`), aktifkan **Mode developer**, klik **Muat yang belum dibuka**, lalu pilih `extension/dist`.
3. Biarkan aplikasi tetap berjalan, buka video, lalu klik ikon Tarjuman atau tekan <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

Ekstensi hanya berkomunikasi dengan aplikasi di komputer Anda. Kit Chrome Web Store-nya (teks listing, alasan izin, kebijakan privasi, gambar promosi) ada di [`extension/store`](../../extension/store).

## Cara sulih suara tetap sinkron

Baris teks digabung menjadi kalimat utuh dan kata pengisi dihapus. Kemudian kecepatan setiap kalimat dipilih berdasarkan jendela antisipasi sekitar 12 detik, sehingga kalimat yang longgar meminjamkan waktu kepada kalimat yang padat dan kecepatan berubah bertahap alih-alih melompat. Sebelum browser memutar apa pun, server menyintesis dan mengukur setiap kalimat, jadi rencananya didasarkan pada durasi nyata, bukan tebakan. Jika sulih suara tetap tertinggal, kalimat berikutnya diputar sedikit lebih cepat; video hanya dijeda bila selisihnya melewati sekitar dua detik. Melompat ke titik mana pun akan melanjutkan sulih suara tepat di posisi itu.

Desain lengkapnya ada di [docs/implementation.md](../implementation.md).

## Privasi

Tarjuman mengutamakan pemrosesan lokal. Video, subtitle, kata tersimpan, pengaturan, dan kunci API Anda tetap berada di folder `data/` di komputer Anda. Aplikasi menghubungi YouTube (teks dan unduhan), Google Translate dan MyMemory (terjemahan), layanan suara Edge milik Microsoft (ucapan), dan, hanya jika Anda mengaktifkannya, penyedia AI pilihan Anda. Tidak ada akun, analitik, atau pelacakan. API menolak permintaan dari situs web lain, dan pengaturan AI hanya dapat diubah dari komputer yang menjalankan aplikasi.

## Konfigurasi

| Variabel lingkungan | Bawaan | Arti |
|---|---|---|
| `TARJUMAN_HOME` | folder proyek | Lokasi penyimpanan `data/` |
| `TARJUMAN_PORT` | `4318` | Port pertama yang dicoba (naik ke port berikutnya jika sibuk; ekstensi mengikutinya) |
| `TARJUMAN_HOST` | `0.0.0.0` | Gunakan `127.0.0.1` agar aplikasi tidak bisa diakses dari Wi-Fi Anda |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` atau `medium` untuk transkripsi yang lebih akurat (lebih lambat) |
| `ANTHROPIC_API_KEY` | – | Dipakai untuk Claude jika tidak ada kunci yang tersimpan di pengaturan |

## Struktur proyek

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Pengembangan

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

Baca [docs/specs.md](../specs.md) sebelum mengubah rute API: aplikasi web dan ekstensi sama-sama bergantung padanya.

## Dibangun dengan

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[model MDX-Net dari Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Lisensi

[MIT](../../LICENSE). Mengunduh video dan teks tunduk pada ketentuan masing-masing situs. Gunakan Tarjuman untuk konten yang boleh Anda tonton dan adaptasi.
