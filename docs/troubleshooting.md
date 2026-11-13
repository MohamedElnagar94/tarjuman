# Troubleshooting

Problems met so far, with their cause and fix. Start with `python -m tarjuman doctor` (installed app: `Tarjuman.cmd doctor` in the install folder): it checks every component and says what is missing.

Where things are:

| | From source | Installed on Windows |
|---|---|---|
| Your data (videos, subtitles, settings) | `data/` in the project folder | `%LOCALAPPDATA%\Tarjuman\data` |
| Settings file | `.env` in the project folder | `%LOCALAPPDATA%\Tarjuman\.env` |
| Messages and errors | the console window | `%LOCALAPPDATA%\Tarjuman\data\tarjuman.log` |

## Installing on Windows

**"Setup was unable to create the directory ...\Temp\is-….tmp. Error 5: Access is denied."**
The installer file is in a folder that Windows marks as low-integrity (some sandboxing tools mark their working folders this way). Windows then runs the file with fewer rights, and it cannot write to your Temp folder. `icacls <file>` shows `Mandatory Label\Low Mandatory Level` when this is the case. Copy the installer to another folder, such as Downloads, and run the copy. Running as administrator does not help.

**"Windows protected your PC" / unknown publisher.**
The installer is not code-signed yet. Choose *More info*, then *Run anyway*.

**The app window does not open.**
The window is Microsoft Edge or Google Chrome in app mode. With neither installed, Tarjuman opens a normal browser tab instead. If nothing opens at all, read the end of `tarjuman.log`.

**Starting Tarjuman a second time.**
It opens a window on the copy that is already running, instead of starting another one.

**`update` fails in the installed app.**
The program is in Program Files, which only an administrator can change. Right-click `Tarjuman.cmd` in the install folder, choose *Run as administrator*, and run it with `update`.

**Updating.**
Settings → Updates checks GitHub and installs a new version after verifying its checksum; Windows asks for permission, Tarjuman closes, and it starts again updated. If it says the download does not match its checksum, nothing was installed: check again later, or download the installer from the Releases page yourself. A copy run from source updates with `git pull`.

## Linux (AppImage)

**"AppImages require FUSE to run".**
Install `libfuse2` (Debian, Ubuntu: `sudo apt install libfuse2`), or run it with `--appimage-extract-and-run`.

**It opened in the browser, not in a window.**
The window needs Chrome, Chromium or Edge. Without them Tarjuman uses your default browser and keeps running after the tab closes; stop it with `pkill -f "tarjuman app"`.

**Where is my data?** In `~/.local/share/Tarjuman` (or `$XDG_DATA_HOME/Tarjuman`). Deleting the AppImage leaves it there.

## Phone

**The phone says the site can't be reached.**
1. The phone and the computer must be on the same Wi-Fi.
2. On Windows, run `scripts\allow-phone.ps1` once as administrator: it marks your home Wi-Fi as Private and opens Tarjuman's ports (4318 to 4327) on Private networks only.
3. `TARJUMAN_HOST` must be `0.0.0.0` (the default); `127.0.0.1` keeps the app on the computer only.

**"This pairing code is no longer valid."**
A code works for 15 minutes (`TARJUMAN_PAIR_MINUTES`). Open Settings → Phone on the computer and scan the code shown there now.

**"Too many wrong codes from this device."**
After five wrong codes from one address, that address waits ten minutes. Then scan the current code.

**"This device is not paired with Tarjuman."**
Every device other than the computer itself is paired once, from Settings → Phone. Unpairing a phone there, or choosing *Unpair all devices*, brings this page back on it.

## Subtitles and translation

**The video has no captions.**
Tarjuman transcribes it with Whisper on your computer. The first time, the model is downloaded (about 145 MB for `base`). For better accuracy set `TARJUMAN_WHISPER_MODEL=small` or `medium`; they are slower and need more memory.

**Translation stops or goes slowly.**
The free translation services limit how much one address may ask for. Tarjuman waits and continues by itself, translating the lines around the playhead first. Lines already translated are saved and never asked for again.

**A translated line is wrong.**
Use the pencil next to the line. Your correction is kept and wins over the machine translation from then on.

## Dubbing

**No voice, or the voice changes.**
The online voices come from Microsoft's Edge voice service. When it fails, Tarjuman uses the local Arabic voice (Piper) and then Google. Run `python -m tarjuman update` to refresh the voice client.

**The offline Arabic voice is missing.**
It is downloaded once (about 60 MB): by `python -m tarjuman setup` from source, in the background on the first start of the installed app. `doctor` shows whether it is there.

**A word is pronounced wrong.**
Add it in Settings → Pronunciation.

## Downloads and files

**"Could not download the video from this link."**
Sites change often. Run `python -m tarjuman update` to refresh yt-dlp.

**"This link points inside your local network."**
Downloads refuse addresses on your own network. For a media server at home, set `TARJUMAN_FETCH_PRIVATE=1`.

**"Too many jobs are waiting."**
At most 20 jobs wait their turn (`TARJUMAN_MAX_QUEUE`). Let some finish, or cancel the ones you don't need.

**A job says it is waiting for another job.**
Whisper, dubbing and burning subtitles are heavy, so only two run together (`TARJUMAN_HEAVY_JOBS`). On a computer with little memory, set it to `1`.

**"The disk is full" or "The file is too large".**
Uploads are limited to 8 GB (`TARJUMAN_MAX_UPLOAD_GB`) and stop before less than 1 GB would be left free. Settings → Storage shows what takes space and clears the caches.

## Browser extension

**"Proceed with caution: this extension is not trusted by Enhanced Safe Browsing."**
The publisher is new to the Chrome Web Store. Chrome shows this for every new publisher until it has followed the store's policies for a few months, and only to people who turned on Enhanced Safe Browsing. The extension passed the store's review and its [source code](https://github.com/MohamedElnagar94/tarjuman/tree/main/extension) is open. Choose *Continue to install*.

**The popup says it is not connected.**
Tarjuman must be running on this computer. The extension finds it on ports 4318 to 4327 by itself.

**The extension is waiting for approval.**
Only the first extension that connects is trusted automatically. Approve another one in Settings → Extensions, on the computer.

**Nothing appears on a site's video.**
Open the popup on that page and allow the site. For a player inside a frame from another site, the popup asks for that site too.

## "An unexpected error happened. Reference: …"

The details are in the console window or in `tarjuman.log`, next to the same reference. Include those lines when you report the problem.

## Known limitations

- Translation needs the internet; there is no local translator yet.
- The local voice is one Arabic voice. Other languages and accents need the online voices.
- The Windows installer is not code-signed, and there is no installer for macOS or Linux yet (use `./start.sh`).
- The check that keeps downloads off your local network runs before the download starts; it does not inspect requests the downloader makes later.
