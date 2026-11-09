<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman simgesi: oynatma işaretinin altında Arapça tâ harfi">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Her videoyu Arapça izleyin.</strong><br>
  Senkronize çeviri, doğal canlı seslendirme, seslendirilmiş MP4'ler ve bir tarayıcı eklentisi. Her şey kendi bilgisayarınızda çalışır.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="MIT lisansı" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <b>Türkçe</b> ·
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
  <img src="../screenshots/watch.png" alt="Tarjuman, Arapça altyazılarla bir YouTube videosu oynatıyor; seslendirme paneli açık" width="900">
</p>

## Ne yapar

Bir YouTube bağlantısı yapıştırın, bilgisayarınızdan bir video yükleyin ya da neredeyse herhangi bir siteden bağlantı verin.

- **Senkronize altyazılar.** Arapça altyazılar videonun üzerinde satır satır görünür; isterseniz altında orijinal dil de yer alır. Otomatik oluşturulan altyazılar çevrilmeden önce tam cümlelere dönüştürülür.
- **İnsan gibi konuşan canlı seslendirme.** Nöral bir Arapça ses, her cümleyi konuşmacıyla aynı zamanlamada; Mısır, Suudi, Emirlik, Suriye, Ürdün, Lübnan, Fas veya Irak Arapçasıyla okur. Hiçbir cümle kesilmez ya da atlanmaz; video yalnızca seslendirme epey geride kaldığında duraklar.
- **Seslendirilmiş MP4.** Videoyu Arapça seslendirmeyle dışa aktarın. Müzik ve efektleri korurken orijinal konuşmacının sesini kaldırabilir, her konuşmacıya uygun bir erkek ya da kadın sesi atayabilir, altyazıları gömebilir veya görüntüye yakabilir.
- **Altyazı yok mu? Sorun değil.** Whisper sesi bilgisayarınızda yazıya döker, ardından bu döküm çevrilir.
- **Altyazı dosyaları.** SRT, VTT veya düz metin olarak, Arapça ya da iki dilli indirin; dilerseniz paylaşmaya hazır altyazılı bir MP4 alın.
- **Oynatma listelerinin tamamı.** Bir oynatma listesi veya kanal bağlantısı verin; içindeki her video için altyazı, altyazılı video ya da seslendirilmiş video üretsin.
- **Videoya sorun** (isteğe bağlı yapay zekâ). Bir özet, ana noktalar, tıklanabilir bölümler ve sizi videonun sorunuzu ele aldığı ana götüren yanıtlar alın. Claude veya OpenAI uyumlu herhangi bir sağlayıcıyla (Gemini, Groq, OpenRouter, Ollama) çalışır.
- **İngilizce öğrenin.** Anlamını görmek için herhangi bir kelimeye dokunun, onu cümlesiyle birlikte kaydedin, daha sonra tekrar edin ve Anki'ye aktarın. Ayrıca bir cümleyi tekrarlayabilir, her satırdan sonra duraklatabilir ya da kendinizi sınamak için altyazıları bulanıklaştırabilirsiniz.
- **Tarayıcı eklentisi.** Aynı altyazıları ve seslendirmeyi doğrudan YouTube'da, oynatıcısında altyazı bulunan sitelerde (Coursera, Udemy ve diğerleri) ya da sekmenin sesini dinleyerek başka herhangi bir sitede kullanın.

Başka diller de çalışır: Fransızca, İspanyolca, Almanca, Türkçe ve İngilizce hedef dil olarak yerleşiktir.

## Hızlı başlangıç

**Python 3.11+** ve **Node.js 20+** gerekir.

**Windows:** `start.cmd` dosyasına çift tıklayın.

**macOS / Linux:**

```sh
./start.sh
```

İlk çalıştırma her şeyi kurar: Python paketlerini, çevrimdışı Arapça sesi ve web uygulamasının derlenmiş hâlini. Ardından uygulama `http://127.0.0.1:4318` adresinde açılır. Sonraki çalıştırmalarda birkaç saniyede başlar. Telefonunuzdan kullanmak için Wi-Fi ağınız için yazdırdığı adresi açın.

<details>
<summary>Elle kurulum</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Komutlar

| Komut | Ne yapar |
|---|---|
| `python -m tarjuman` | Uygulamayı başlatır (`--port`, yalnızca bu bilgisayar için `--host 127.0.0.1`, `--no-open`) |
| `python -m tarjuman subs <link>` | Altyazı dosyalarını `data/output` klasörüne yazar (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Her şeyi kurar veya onarır |
| `python -m tarjuman update` | İndirmeler ya da sesler çalışmaz olursa yt-dlp'yi ve ses istemcisini günceller |
| `python -m tarjuman doctor` | Her bileşeni denetler |

## Tarayıcı eklentisi

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="Tarjuman eklentisinin açılır penceresi" width="320">
</p>

1. Bir kez derleyin: `npm --prefix extension install && npm --prefix extension run build`.
2. `chrome://extensions` (veya `edge://extensions`) sayfasını açın, **Geliştirici modu**'nu etkinleştirin, **Paketlenmemiş öğe yükle**'ye tıklayın ve `extension/dist` klasörünü seçin.
3. Uygulamayı açık tutun, bir video açın ve Tarjuman simgesine tıklayın ya da <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd> tuşlarına basın.

Eklenti yalnızca bilgisayarınızdaki uygulamayla iletişim kurar. Chrome Web Store kiti (mağaza metni, izin gerekçeleri, gizlilik politikası, tanıtım görselleri) [`extension/store`](../../extension/store) klasöründedir.

## Seslendirme nasıl senkron kalır

Altyazı satırları tam cümlelerde birleştirilir ve dolgu sözcükleri çıkarılır. Ardından her cümlenin hızı yaklaşık 12 saniyelik bir ileriye bakış penceresine göre seçilir; böylece rahat bir cümle sıkışık bir cümleye zaman ödünç verir ve hız sıçramak yerine kademeli olarak değişir. Tarayıcı herhangi bir şey çalmadan önce sunucu her cümleyi sentezler ve süresini ölçer; yani plan tahminlere değil gerçek sürelere dayanır. Seslendirme yine de geride kalırsa sonraki cümleler biraz daha hızlı çalınır; video yalnızca fark yaklaşık iki saniyeyi aştığında duraklar. Herhangi bir noktaya atladığınızda seslendirme tam o yerden devam eder.

Tasarımın tamamı [docs/implementation.md](../implementation.md) dosyasındadır.

## Gizlilik

Tarjuman önce yerel çalışacak şekilde tasarlanmıştır. Videolarınız, altyazılarınız, kaydettiğiniz kelimeler, ayarlarınız ve API anahtarınız bilgisayarınızdaki `data/` klasöründe kalır. Uygulama YouTube (altyazılar ve indirmeler), Google Translate ve MyMemory (çeviri), Microsoft'un Edge ses hizmeti (konuşma) ve yalnızca siz açarsanız seçtiğiniz yapay zekâ sağlayıcısıyla iletişim kurar. Hesap, analiz veya izleme yoktur. API diğer web sitelerinden gelen istekleri reddeder ve yapay zekâ ayarları yalnızca uygulamayı çalıştıran bilgisayardan değiştirilebilir.

## Yapılandırma

| Ortam değişkeni | Varsayılan | Anlamı |
|---|---|---|
| `TARJUMAN_HOME` | proje klasörü | `data/` klasörünün tutulduğu yer |
| `TARJUMAN_PORT` | `4318` | Denenecek ilk port (doluysa bir üstüne geçer; eklenti de onu izler) |
| `TARJUMAN_HOST` | `0.0.0.0` | Uygulamayı Wi-Fi ağınıza kapatmak için `127.0.0.1` kullanın |
| `TARJUMAN_WHISPER_MODEL` | `base` | Daha doğru (ama daha yavaş) yazıya dökme için `small` veya `medium` |
| `ANTHROPIC_API_KEY` | – | Ayarlarda kayıtlı anahtar yoksa Claude için kullanılır |

## Proje yapısı

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Geliştirme

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

Bir API rotasını değiştirmeden önce [docs/specs.md](../specs.md) dosyasını okuyun: hem web uygulaması hem de eklenti ona bağlıdır.

## Kullanılan teknolojiler

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[Ultimate Vocal Remover'ın MDX-Net modelleri](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Lisans

[MIT](../../LICENSE). Video ve altyazı indirmek her sitenin kendi koşullarına tabidir. Tarjuman'ı izlemenize ve uyarlamanıza izin verilen içerikler için kullanın.
