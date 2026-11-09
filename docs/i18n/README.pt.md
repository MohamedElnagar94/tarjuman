<p align="center">
  <img src="../../assets/brand/icon-256.png" width="128" height="128" alt="Ícone do Tarjuman: a letra árabe taa sob um símbolo de reprodução">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Assista a qualquer vídeo em árabe.</strong><br>
  Tradução sincronizada, dublagem ao vivo natural, MP4 dublados e uma extensão de navegador. Tudo roda no seu próprio computador.
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="Licença MIT" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
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
  <b>Português</b> ·
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
  <img src="../screenshots/watch.png" alt="Tarjuman reproduzindo um vídeo do YouTube com legendas em árabe e o painel de dublagem aberto" width="900">
</p>

## O que ele faz

Cole um link do YouTube, envie um vídeo do seu computador ou passe um link de praticamente qualquer site.

- **Legendas sincronizadas.** As legendas em árabe aparecem sobre o vídeo linha por linha, com o idioma original embaixo, se você quiser. Legendas geradas automaticamente são reconstruídas em frases completas antes de serem traduzidas.
- **Dublagem ao vivo que soa como uma pessoa.** Uma voz árabe neural fala cada frase no ritmo de quem está falando, em árabe egípcio, saudita, emiradense, sírio, jordaniano, libanês, marroquino ou iraquiano. Nenhuma frase é cortada ou pulada, e o vídeo só pausa quando a dublagem fica bem atrasada.
- **MP4 dublado.** Exporte o vídeo com a narração em árabe. É possível remover a voz do locutor original mantendo a música e os efeitos, dar a cada pessoa uma voz masculina ou feminina correspondente e embutir ou gravar as legendas na imagem.
- **Sem legendas? Sem problema.** O Whisper transcreve o áudio no seu computador e, em seguida, a transcrição é traduzida.
- **Arquivos de legenda.** Baixe SRT, VTT ou texto simples, em árabe ou bilíngue, ou um MP4 legendado pronto para compartilhar.
- **Playlists inteiras.** Passe o link de uma playlist ou de um canal para gerar legendas, vídeos legendados ou vídeos dublados de todos os vídeos dela.
- **Pergunte ao vídeo** (IA opcional). Obtenha um resumo, os pontos principais, capítulos clicáveis e respostas que levam ao momento em que o vídeo trata da sua pergunta. Funciona com Claude ou qualquer provedor compatível com OpenAI (Gemini, Groq, OpenRouter, Ollama).
- **Aprenda inglês.** Toque em qualquer palavra para ver o significado, salve-a com a frase, revise depois e exporte para o Anki. Você também pode repetir uma frase, pausar após cada linha ou desfocar as legendas para se testar.
- **Extensão de navegador.** Use as mesmas legendas e a mesma dublagem no próprio YouTube, em sites cujo player tem legendas (Coursera, Udemy e outros) ou em qualquer outro site, ouvindo o áudio da aba.

Outros idiomas também funcionam: francês, espanhol, alemão, turco e inglês já vêm como idiomas de destino.

## Início rápido

Você precisa de **Python 3.11+** e **Node.js 20+**.

**Windows:** clique duas vezes em `start.cmd`.

**macOS / Linux:**

```sh
./start.sh
```

A primeira execução instala tudo: os pacotes Python, a voz árabe offline e um build do aplicativo web. Depois, o aplicativo abre em `http://127.0.0.1:4318`. Nas execuções seguintes, ele inicia em poucos segundos. Para usá-lo pelo celular, abra o endereço que ele mostra para o seu Wi-Fi.

<details>
<summary>Instalação manual</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Comandos

| Comando | O que faz |
|---|---|
| `python -m tarjuman` | Inicia o aplicativo (`--port`, `--host 127.0.0.1` apenas para este computador, `--no-open`) |
| `python -m tarjuman subs <link>` | Grava arquivos de legenda em `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Instala ou repara tudo |
| `python -m tarjuman update` | Atualiza o yt-dlp e o cliente de voz, se os downloads ou as vozes pararem de funcionar |
| `python -m tarjuman doctor` | Verifica cada componente |

## A extensão de navegador

<p align="center">
  <img src="../screenshots/extension-popup.png" alt="O popup da extensão Tarjuman" width="320">
</p>

1. Compile uma vez: `npm --prefix extension install && npm --prefix extension run build`.
2. Abra `chrome://extensions` (ou `edge://extensions`), ative o **Modo do desenvolvedor**, clique em **Carregar sem compactação** e escolha `extension/dist`.
3. Mantenha o aplicativo rodando, abra um vídeo e clique no ícone do Tarjuman, ou pressione <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

A extensão se comunica apenas com o aplicativo no seu computador. O kit para a Chrome Web Store (texto da página, justificativas das permissões, política de privacidade, imagens promocionais) está em [`extension/store`](../../extension/store).

## Como a dublagem fica sincronizada

As linhas de legenda são unidas em frases completas e as palavras de preenchimento são removidas. Em seguida, a velocidade de cada frase é escolhida com base numa janela de antecipação de cerca de 12 segundos, de modo que uma frase folgada empresta tempo a uma apertada e a velocidade muda aos poucos, sem saltos. Antes que o navegador toque qualquer coisa, o servidor sintetiza e mede cada frase, então o plano se baseia em durações reais, e não em estimativas. Se mesmo assim a dublagem atrasar, as frases seguintes tocam um pouco mais rápido; o vídeo só pausa quando a diferença passa de uns dois segundos. Ao pular para qualquer ponto, a dublagem retoma exatamente ali.

O design completo está em [docs/implementation.md](../implementation.md).

## Privacidade

O Tarjuman funciona localmente em primeiro lugar. Seus vídeos, legendas, palavras salvas, configurações e chave de API ficam na pasta `data/` do seu computador. O aplicativo se conecta ao YouTube (legendas e downloads), ao Google Translate e ao MyMemory (tradução), ao serviço de voz do Edge da Microsoft (fala) e, somente se você ativar, ao provedor de IA que escolher. Não há contas, análises nem rastreamento. A API recusa requisições de outros sites, e as configurações de IA só podem ser alteradas no computador que executa o aplicativo.

## Configuração

| Variável de ambiente | Padrão | Significado |
|---|---|---|
| `TARJUMAN_HOME` | pasta do projeto | Onde `data/` fica guardada |
| `TARJUMAN_PORT` | `4318` | Primeira porta a tentar (se estiver ocupada, passa para a próxima; a extensão acompanha) |
| `TARJUMAN_HOST` | `0.0.0.0` | Use `127.0.0.1` para deixar o aplicativo fora do seu Wi-Fi |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` ou `medium` para uma transcrição mais precisa (mais lenta) |
| `ANTHROPIC_API_KEY` | – | Usada para o Claude quando nenhuma chave está salva nas configurações |

## Estrutura do projeto

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Desenvolvimento

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

Leia [docs/specs.md](../specs.md) antes de alterar uma rota da API: tanto o aplicativo web quanto a extensão dependem dela.

## Feito com

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[modelos MDX-Net do Ultimate Vocal Remover](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## Licença

[MIT](../../LICENSE). O download de vídeos e legendas está sujeito aos termos de cada site. Use o Tarjuman com conteúdo que você tem permissão para assistir e adaptar.
