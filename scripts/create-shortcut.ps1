# Creates a "Tarjuman" shortcut on the desktop. It starts start.cmd through cmd.exe (signed by
# Microsoft), so Windows doesn't show the "publisher could not be verified" prompt for the script.
#   powershell -ExecutionPolicy Bypass -File scripts\create-shortcut.ps1
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop 'Tarjuman.lnk'))
$lnk.TargetPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
$lnk.Arguments = '/c "' + (Join-Path $root 'start.cmd') + '"'
$lnk.WorkingDirectory = $root
$lnk.IconLocation = (Join-Path $root 'assets\brand\icon.ico') + ',0'
$lnk.Description = 'Tarjuman: watch any video in Arabic'
$lnk.Save()
Write-Host "Created $($lnk.FullName)"
