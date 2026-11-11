# Builds the folder the Windows installer packs: Tarjuman with its own Python, every Python package,
# the built web app and the browser extension. A user of the installer needs neither Python nor Node.
#
#   powershell -ExecutionPolicy Bypass -File installer\build.ps1 [-Python <python.exe>] [-SkipExtension]
#
# Needs on the building machine: Python 3.11+ (the same version is bundled) and Node.js 20+.
# Output: build\windows\app  (then: iscc installer\tarjuman.iss)
param(
  [string]$Python = "",
  [switch]$SkipExtension
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "build\windows"
$app = Join-Path $out "app"

function Run([string]$exe, [string[]]$arguments, [string]$cwd = $root) {
  Push-Location $cwd
  try {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe $($arguments -join ' ') failed with exit code $LASTEXITCODE" }
  } finally { Pop-Location }
}

if (-not $Python) {
  $venv = Join-Path $root ".venv\Scripts\python.exe"
  $Python = if (Test-Path $venv) { $venv } else { "python" }
}
$pyVersion = (& $Python -c "import platform; print(platform.python_version())").Trim()
$pyTag = ($pyVersion.Split(".")[0..1] -join "")
Write-Host "Bundling Python $pyVersion"

if (Test-Path $app) { Remove-Item -Recurse -Force $app }
New-Item -ItemType Directory -Force (Join-Path $app "python") | Out-Null

# 1) Python itself: the official embeddable build, the same version as the one installing the packages.
$zip = Join-Path $out "python-$pyVersion-embed-amd64.zip"
if (-not (Test-Path $zip)) {
  Invoke-WebRequest "https://www.python.org/ftp/python/$pyVersion/python-$pyVersion-embed-amd64.zip" -OutFile $zip
}
Expand-Archive -Path $zip -DestinationPath (Join-Path $app "python") -Force
# The embeddable Python only looks where this file says: its own library, the packages, and Tarjuman.
@("python$pyTag.zip", ".", "Lib\site-packages", "..\backend", "import site") |
  Set-Content -Encoding ascii (Join-Path $app "python\python$pyTag._pth")

# 2) Every Python package, next to it. pip goes in too, so "tarjuman update" can refresh yt-dlp later.
$site = Join-Path $app "python\Lib\site-packages"
Run $Python @("-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", "--target", $site,
  "-r", (Join-Path $root "backend\requirements.txt"), "pip")
Get-ChildItem $site -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 3) Tarjuman's own code.
Copy-Item -Recurse (Join-Path $root "backend\tarjuman") (Join-Path $app "backend\tarjuman")
Copy-Item (Join-Path $root "backend\requirements.txt") (Join-Path $app "backend\requirements.txt")
Get-ChildItem (Join-Path $app "backend") -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
New-Item -ItemType Directory -Force (Join-Path $app "shared\dub-engine") | Out-Null
Copy-Item -Recurse (Join-Path $root "shared\dub-engine\src") (Join-Path $app "shared\dub-engine\src")
New-Item -ItemType Directory -Force (Join-Path $app "assets") | Out-Null
Copy-Item -Recurse (Join-Path $root "assets\brand") (Join-Path $app "assets\brand")

# 4) The web app, built.
$frontend = Join-Path $root "frontend"
Run "npm.cmd" @("ci", "--no-audit", "--no-fund") $frontend
Run "npm.cmd" @("run", "build") $frontend
New-Item -ItemType Directory -Force (Join-Path $app "frontend") | Out-Null
Copy-Item -Recurse (Join-Path $frontend "dist") (Join-Path $app "frontend\dist")

# 5) The browser extension, built, ready for "Load unpacked".
if (-not $SkipExtension) {
  $extension = Join-Path $root "extension"
  Run "npm.cmd" @("ci", "--no-audit", "--no-fund") $extension
  Run "npm.cmd" @("run", "build") $extension
  Copy-Item -Recurse (Join-Path $extension "dist") (Join-Path $app "extension")
}

# 6) The launcher and what a user may want to read or run.
Copy-Item (Join-Path $PSScriptRoot "Tarjuman.cmd") $app
# Marks this folder as the installed app: its data then lives in %LOCALAPPDATA%\Tarjuman.
Set-Content -Encoding ascii (Join-Path $app "installed.txt") "Tarjuman, installed. Data: %LOCALAPPDATA%\Tarjuman"
Copy-Item (Join-Path $root ".env.example") $app
Copy-Item (Join-Path $root "LICENSE") (Join-Path $app "LICENSE.txt")
Copy-Item (Join-Path $root "README.md") $app
New-Item -ItemType Directory -Force (Join-Path $app "scripts") | Out-Null
Copy-Item (Join-Path $root "scripts\allow-phone.ps1") (Join-Path $app "scripts")

# 7) Compile everything now, with the bundled Python. Otherwise the first start on the user's
#    computer spends minutes compiling thousands of files.
$bundled = Join-Path $app "python\python.exe"
& $bundled -m compileall -q -j 0 $site (Join-Path $app "backend") | Out-Null
& $bundled -c "import fastapi, uvicorn, tarjuman.api.app, tarjuman.desktop"
if ($LASTEXITCODE -ne 0) { throw "The bundled Python cannot import Tarjuman" }
& $bundled -m tarjuman --version | Out-Null  # the command line itself parses and starts
if ($LASTEXITCODE -ne 0) { throw "The bundled Tarjuman command does not start" }

$version = (& $Python -c "import re,sys; print(re.search(r'__version__ = .(.+?).$', open(sys.argv[1], encoding='utf-8').read(), re.M).group(1))" (Join-Path $root "backend\tarjuman\__init__.py")).Trim()
Set-Content -Encoding ascii (Join-Path $out "version.txt") $version
$size = [math]::Round(((Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum / 1MB))
Write-Host "Built Tarjuman $version in $app ($size MB)"
