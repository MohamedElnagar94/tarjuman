# Lets phones on your home Wi-Fi open Tarjuman. Run once, as administrator:
#   right-click this file > "Run with PowerShell" and accept the Windows prompt,
#   or in an administrator PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\allow-phone.ps1
#
# 1. Marks the Wi-Fi you are on now as a Private (home) network. Do this only at home: on a Public
#    network (café, airport) Windows blocks incoming connections, which is what you want there.
# 2. Allows Tarjuman's ports (4318-4327) on Private networks only.

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`""
    exit
}

$wifi = Get-NetConnectionProfile | Where-Object { $_.IPv4Connectivity -eq 'Internet' } | Select-Object -First 1
if ($wifi -and $wifi.NetworkCategory -ne 'Private') {
    Set-NetConnectionProfile -InterfaceIndex $wifi.InterfaceIndex -NetworkCategory Private
    Write-Host "Network '$($wifi.Name)' is now Private (home)."
}
if (-not (Get-NetFirewallRule -DisplayName 'Tarjuman' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'Tarjuman' -Direction Inbound -Protocol TCP -LocalPort 4318-4327 `
        -Action Allow -Profile Private | Out-Null
    Write-Host 'Firewall: Tarjuman ports 4318-4327 allowed on Private networks.'
}
$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
    Select-Object -First 1).IPv4Address.IPAddress
Write-Host "`nOn your phone (same Wi-Fi) open:  http://${ip}:4318`n"
Read-Host 'Press Enter to close'
