<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Icono de Tarjuman: la letra árabe taa bajo un símbolo de reproducción">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Mira cualquier vídeo en árabe.</strong><br>
  Traducción sincronizada, doblaje en directo natural, MP4 doblados y una extensión de navegador. Todo se ejecuta en tu propio ordenador.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="Licencia MIT" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1F2E8C">
  <img alt="Vue 3" src="https://img.shields.io/badge/vue-3-1F2E8C">
  <img alt="Chrome MV3" src="https://img.shields.io/badge/chrome-MV3-F0922B">
</p>

<p align="center">
  <a href="../../README.md">English</a> ·
  <a href="README.ar.md">العربية</a> ·
  <a href="README.fr.md">Français</a> ·
  <b>Español</b> ·
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
  <a href="README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="../screenshots/watch.png" alt="Tarjuman reproduciendo un vídeo de YouTube con subtítulos en árabe y el panel de doblaje abierto" width="900">
</p>

## Qué hace

Pega un enlace de YouTube, sube un vídeo desde tu ordenador o dale un enlace de casi cualquier sitio.

- **Subtítulos sincronizados.** Los subtítulos en árabe aparecen sobre el vídeo línea a línea, con el idioma original debajo si lo quieres. Los subtítulos generados automáticamente se reconstruyen en frases completas antes de traducirse. Si no tienen ninguna puntuación, se cortan donde el orador hace pausas de verdad, usando los tiempos por palabra de YouTube.
- **Doblaje en directo que suena a persona.** Una voz árabe neuronal pronuncia cada frase al ritmo del orador, en árabe egipcio, saudí, emiratí, sirio, jordano, libanés, marroquí o iraquí. Ninguna frase se corta ni se salta. Con un orador rápido, el vídeo se ralentiza un poco mientras la voz lo alcanza, en lugar de que la voz se acelere; si ralentizas tú el vídeo, la voz aprovecha ese tiempo extra. Las palabras que se escriben igual pero se leen distinto se pronuncian según el sentido de la frase (الجُمَل «las frases», no الجَمَل «el camello»), a partir del original en inglés.
- **MP4 doblado.** Exporta el vídeo con la locución en árabe. Puede eliminar la voz del orador original conservando la música y los efectos, asignar a cada orador una voz masculina o femenina acorde, e incrustar o grabar los subtítulos en la imagen.
- **¿Sin subtítulos? No pasa nada.** Whisper transcribe el audio en tu ordenador y después se traduce la transcripción.
- **Archivos de subtítulos.** Descarga SRT, VTT o texto plano, en árabe o bilingüe, o un MP4 subtitulado listo para compartir.
- **Listas de reproducción completas.** Dale el enlace de una lista o de un canal para crear subtítulos, vídeos subtitulados o vídeos doblados de todos sus vídeos.
- **Pregúntale al vídeo** (IA opcional). Obtén un resumen, los puntos clave, capítulos en los que hacer clic y respuestas que saltan al momento en que el vídeo trata tu pregunta. Funciona con Claude o con cualquier proveedor compatible con OpenAI (Gemini, Groq, OpenRouter, Ollama).
- **Aprende inglés.** Toca cualquier palabra para ver su significado, guárdala con su frase, repásala más tarde y expórtala a Anki. También puedes repetir una frase, pausar tras cada línea o difuminar los subtítulos para ponerte a prueba.
- **Extensión de navegador.** Usa los mismos subtítulos y el mismo doblaje en el propio YouTube, en sitios cuyo reproductor tiene subtítulos (Coursera, Udemy y otros), en sitios de películas y anime que incrustan su reproductor desde otro sitio o en cualquier otro sitio escuchando el audio de la pestaña.
- **En tu móvil.** Abre la aplicación desde cualquier móvil conectado a la misma Wi-Fi.

También funcionan otros idiomas: francés, español, alemán, turco e inglés vienen integrados como idiomas de destino.

## Capturas de pantalla

<table>
  <tr>
    <td width="50%"><img src="../screenshots/home.png" alt="Inicio: pegar un enlace, subir un vídeo, vídeos recientes y el estado del ordenador"></td>
    <td width="50%"><img src="../screenshots/watch-en.png" alt="Viendo un vídeo con subtítulos sincronizados y la transcripción, en inglés y con el tema claro"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/library.png" alt="Mis archivos: tareas, un lote de una lista de reproducción, vídeos subidos y archivos terminados"></td>
    <td><img src="../screenshots/settings.png" alt="Ajustes: proveedor de IA, diccionario de pronunciación, valores predeterminados y apariencia"></td>
  </tr>
  <tr>
    <td><img src="../screenshots/extension-overlay.png" alt="La extensión mostrando subtítulos en árabe en YouTube"></td>
    <td><img src="../screenshots/extension-welcome.png" alt="La página de bienvenida de la extensión, conectada a la aplicación"></td>
  </tr>
</table>

<p align="center">
  <img src="../screenshots/phone-home.png" alt="Inicio en un móvil" width="260">
  <img src="../screenshots/phone-watch.png" alt="Viendo un vídeo en un móvil" width="260">
</p>

## Inicio rápido

### Instalador de Windows

Descarga `Tarjuman-Setup-<version>.exe` desde la página de [Releases](https://github.com/MohamedElnagar94/tarjuman/releases) y ejecútalo. Trae su propio Python, todos los paquetes, la aplicación web y la extensión de navegador, así que no necesitas ni Python ni Node.js. Pide permisos de administrador una sola vez, se instala en Program Files y no toca el cortafuegos. Después, Tarjuman se abre en una ventana propia, como cualquier aplicación de escritorio, sin ventana de consola ni pestaña del navegador; al cerrar la ventana, se detiene. (La ventana es Microsoft Edge en modo aplicación, que viene con todo Windows 10 y 11; no se instala nada más.)

- Si el instalador se detiene enseguida con «unable to create the directory ...\Temp\is-*.tmp, access is denied», el archivo del instalador está en una carpeta marcada con nivel de integridad bajo (algunas herramientas de aislamiento marcan así sus carpetas de trabajo; `icacls <file>` muestra entonces `Low Mandatory Level`). Windows ejecuta un archivo así con menos permisos. Cópialo a otra carpeta, como Descargas, y ejecuta la copia.
- El instalador aún no está firmado digitalmente, así que Windows SmartScreen puede decir «editor desconocido»: elige *Más información → Ejecutar de todas formas*.
- El primer inicio descarga en segundo plano la voz árabe sin conexión (unos 60 MB). El modelo de Whisper se descarga solo la primera vez que un vídeo lo necesita.
- Tus vídeos, subtítulos, ajustes y el `.env` se guardan en `%LOCALAPPDATA%\Tarjuman`, aparte del programa. Una actualización los conserva; al desinstalar se te pregunta si quieres borrarlos.
- El menú Inicio tiene un acceso directo a la carpeta de la extensión, para *Cargar descomprimida* en `chrome://extensions`.

¿Algo no funciona? Consulta [Solución de problemas](../troubleshooting.md). Los cambios de cada versión están en el [registro de cambios](../../CHANGELOG.md).

### Desde el código fuente

Necesitas **Python 3.11+** y **Node.js 20+**.

**Windows:** haz doble clic en `start.cmd`. Si Windows pregunta si quieres ejecutar un script de un editor desconocido, crea una sola vez un acceso directo en el escritorio con `powershell -ExecutionPolicy Bypass -File scripts/create-shortcut.ps1` e inicia Tarjuman desde él; ejecuta el mismo script a través del propio `cmd.exe` de Windows, así que el aviso no aparece.

**macOS / Linux:**

```sh
./start.sh
```

En Debian, Ubuntu y Kali, instala primero `python3-venv` si falta (`sudo apt install python3-venv`).

La primera ejecución lo instala todo: los paquetes de Python, la voz árabe sin conexión y una compilación de la aplicación web. Después, la aplicación se abre en `http://127.0.0.1:4318`. En las siguientes ejecuciones arranca en un par de segundos. Para usarla desde el móvil, abre la dirección que muestra para tu Wi-Fi. En Windows, si el móvil no consigue conectarse, ejecuta `scripts/allow-phone.ps1` una vez como administrador: marca tu Wi-Fi de casa como privada y abre los puertos de Tarjuman solo en redes privadas.

<details>
<summary>Instalación manual</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Comandos

| Comando | Qué hace |
|---|---|
| `python -m tarjuman` | Inicia la aplicación (`--port`, `--host 127.0.0.1` solo para este ordenador, `--no-open`) |
| `python -m tarjuman app` | Inicia la aplicación en una ventana propia (Edge o Chrome en modo aplicación) en lugar de una pestaña del navegador; al cerrar la ventana, se detiene |
| `python -m tarjuman subs <link>` | Escribe archivos de subtítulos en `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Instala o repara todo |
| `python -m tarjuman update` | Actualiza yt-dlp y el cliente de voz, si las descargas o las voces dejan de funcionar |
| `python -m tarjuman doctor` | Comprueba cada componente |

## La extensión de navegador

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="La ventana emergente de la extensión Tarjuman" width="320">
</p>

Instálala directamente desde la [Chrome Web Store](https://chromewebstore.google.com/detail/gcfnomfbpenbhdebopmpdfamlaiodflp), o compílala desde el código fuente con estos pasos:

1. Compílala una vez: `npm --prefix extension install && npm --prefix extension run build`.
2. Abre `chrome://extensions` (o `edge://extensions`), activa el **Modo de desarrollador**, haz clic en **Cargar descomprimida** y elige `extension/dist`.
3. Deja la aplicación en marcha, abre un vídeo y haz clic en el icono de Tarjuman, o pulsa <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

Si Chrome muestra *Proceed with caution: this extension is not trusted by Enhanced Safe Browsing*, es porque el editor es nuevo en la Chrome Web Store: Chrome lo muestra para todo editor nuevo hasta que cumple las políticas de la tienda durante unos meses, y solo a quien activó la protección mejorada. La extensión superó la revisión de la tienda y su [código fuente](https://github.com/MohamedElnagar94/tarjuman/tree/main/extension) es abierto. Elige *Continue to install*.

La extensión solo se comunica con la aplicación de tu ordenador. Su kit para Chrome Web Store (texto de la ficha, justificación de permisos, política de privacidad, imágenes promocionales) está en [`extension/store`](../../extension/store).

## Cómo se mantiene sincronizado el doblaje

Las líneas de subtítulos se unen en frases completas y se eliminan las muletillas. Después, la velocidad de cada frase se elige a partir de una ventana de anticipación de unos 12 segundos, de modo que una frase holgada le presta tiempo a una apretada y la velocidad cambia de forma gradual en lugar de dar saltos. Antes de que el navegador reproduzca las primeras frases de cada tramo, el servidor las sintetiza y las mide, así que el plan se basa en duraciones reales y no en estimaciones, y prepara el tramo siguiente en segundo plano. Si aun así el doblaje se retrasa, el vídeo baja al 85 % de tu velocidad hasta que la voz lo alcanza, y solo se pausa cuando el desfase supera unos dos segundos. El ritmo sigue tu velocidad de reproducción. Si saltas a cualquier punto, el doblaje se reanuda exactamente ahí. Cuando los traductores gratuitos limitan las peticiones, un segundo endpoint de Google y, después, la propia traducción de YouTube mantienen el doblaje en marcha.

El diseño completo está en [docs/implementation.md](../implementation.md).

## Privacidad

Tarjuman funciona en local primero. Tus vídeos, subtítulos, palabras guardadas, ajustes y clave de API se quedan en la carpeta `data/` de tu ordenador. La aplicación contacta con YouTube (subtítulos y descargas), Google Translate y MyMemory (traducción), el servicio de voz de Edge de Microsoft (voz) y, solo si lo activas, el proveedor de IA que elijas. No hay cuentas, analíticas ni rastreo. El vídeo y el audio nunca se suben a ningún sitio.

| Función | Qué sale de tu ordenador | Se envía a | Sin enviar nada |
|---|---|---|---|
| Subtítulos de YouTube | El enlace del vídeo | YouTube | Sube un archivo; se transcribe en local |
| Traducción | Las frases del vídeo, como texto | Google Translate y, después, MyMemory | Nada por ahora; las frases guardadas siguen funcionando sin conexión |
| Voz del doblaje | Cada frase traducida y el nombre de la voz | Voces de Microsoft Edge y, después, Google | Piper, la voz árabe local |
| Descarga de vídeo | Una petición del vídeo | El sitio que lo aloja | Un archivo que ya está en tu ordenador |
| IA (opcional, desactivada por defecto) | El texto del vídeo y tu pregunta | El proveedor que hayas elegido | Déjala desactivada o usa un servidor local como Ollama |
| Descargas de modelos | Una petición de descarga, una sola vez | Hugging Face, GitHub | Nada después de la primera descarga |
| Reconocimiento de voz, separación de música, tus archivos | Nada | – | Siempre en local |

La misma tabla está en la aplicación, en Ajustes → Privacidad. La API rechaza las peticiones de otros sitios web, y los ajustes de IA solo se pueden cambiar desde el ordenador que ejecuta la aplicación.

## Configuración

Copia `.env.example` como `.env` en la carpeta del proyecto y edítalo; cada ajuste está explicado ahí, en árabe y en inglés. El archivo se lee al arrancar, así que reinicia Tarjuman después de un cambio. Una variable definida en el entorno real tiene prioridad sobre el archivo.

| Variable de entorno | Valor predeterminado | Significado |
|---|---|---|
| `TARJUMAN_HOME` | carpeta del proyecto | Dónde se guarda `data/` |
| `TARJUMAN_PORT` | `4318` | Primer puerto que se prueba (sube al siguiente si está ocupado; la extensión lo sigue) |
| `TARJUMAN_HOST` | `0.0.0.0` | Usa `127.0.0.1` para que la aplicación no sea accesible desde tu Wi-Fi |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` o `medium` para una transcripción más precisa (más lenta) |
| `TARJUMAN_VOICE_CACHE_GB` | `2` | Límite de tamaño de las voces de doblaje guardadas; se eliminan primero las usadas hace más tiempo |
| `TARJUMAN_MAX_UPLOAD_GB` | `8` | Tamaño máximo del vídeo que puedes subir |
| `TARJUMAN_PAIR_MINUTES` | `15` | Cuánto tiempo sirve un código de emparejamiento del móvil (el QR); `0` = hasta que generes uno nuevo |
| `TARJUMAN_FETCH_PRIVATE` | desactivado | Ponlo en `1` para permitir descargas desde direcciones de tu propia red |
| `TARJUMAN_HEAVY_JOBS` | `2` | Cuántas tareas pesadas (Whisper, doblaje, grabar subtítulos en la imagen) se ejecutan a la vez; usa `1` en un ordenador con poca memoria |
| `TARJUMAN_MAX_QUEUE` | `20` | Número máximo de tareas que pueden esperar su turno |
| `TARJUMAN_FORCE_ASR` | desactivado | Ponlo en `1` para transcribir siempre con Whisper, sin tener en cuenta los subtítulos de YouTube |
| `ANTHROPIC_API_KEY` | – | Se usa para Claude cuando no hay ninguna clave guardada en los ajustes |

## Estructura del proyecto

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Desarrollo

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

Lee [docs/specs.md](../specs.md) antes de cambiar una ruta de la API: tanto la aplicación web como la extensión dependen de ella.

### Compilar el instalador de Windows

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1   # build\windows\app: Python, packages, web app, extension
iscc /DAppVersion=3.0.0 installer\tarjuman.iss                # build\windows\Tarjuman-Setup-3.0.0.exe (Inno Setup 6)
```

El flujo de trabajo *Windows installer* hace lo mismo en GitHub: ejecútalo desde la pestaña Actions, o sube una etiqueta como `v3.0.0` para adjuntar el instalador a una versión publicada. Antes de compilar, inicia la aplicación empaquetada y comprueba que responde.

## Hecho con

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[los modelos MDX-Net de Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Licencia

[MIT](../../LICENSE). La descarga de vídeos y subtítulos está sujeta a las condiciones de cada sitio. Usa Tarjuman con contenido que tengas permiso para ver y adaptar.
