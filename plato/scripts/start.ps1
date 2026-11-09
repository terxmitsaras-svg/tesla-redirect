<#
.SYNOPSIS
  Start PLATO (API + web app) on Windows. Ctrl+C stops both.

.PARAMETER Lan
  Let devices on your network (phones, tablets, other PCs) connect. Windows Firewall will ask
  for permission the first time; allow "Private networks" only.

.EXAMPLE
  .\scripts\start.ps1
  .\scripts\start.ps1 -Lan -ApiPort 8000 -WebPort 3000
#>
param([switch]$Lan, [int]$ApiPort = 8000, [int]$WebPort = 3000)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$OnWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or $IsWindows
$VenvPy = if ($OnWindows) { Join-Path $Root '.venv\Scripts\python.exe' } else { Join-Path $Root '.venv/bin/python' }
$Server = Join-Path $Root 'frontend/.next/standalone/server.js'
$BindHost = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }

if (-not (Test-Path $VenvPy)) { Write-Host "Not installed yet. Run .\scripts\install.ps1" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Server)) { Write-Host "Web app not built. Run .\scripts\install.ps1" -ForegroundColor Red; exit 1 }

$env:HOSTNAME = $BindHost
$env:PORT = "$WebPort"
$env:NODE_ENV = 'production'
$common = @{ PassThru = $true }
if ($OnWindows) { $common.NoNewWindow = $true }

$api = Start-Process -FilePath $VenvPy -WorkingDirectory (Join-Path $Root 'backend') @common `
  -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', $BindHost, '--port', "$ApiPort")
$web = Start-Process -FilePath 'node' -WorkingDirectory (Split-Path -Parent $Server) @common -ArgumentList @('server.js')

try {
  $ready = $false
  for ($i = 0; $i -lt 60 -and -not $ready; $i++) {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/api/health" -TimeoutSec 1 | Out-Null; $ready = $true }
    catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $ready) { throw "The API did not start on port $ApiPort." }

  Write-Host ''
  Write-Host 'PLATO is running' -ForegroundColor Cyan
  Write-Host "  Open:   http://localhost:$WebPort"
  if ($Lan) {
    $ips = @()
    if (Get-Command Get-NetIPAddress -ErrorAction SilentlyContinue) {
      $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -ExpandProperty IPAddress
    } else {
      $ips = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
        Where-Object { $_.AddressFamily -eq 'InterNetwork' -and $_.ToString() -notlike '127.*' } |
        ForEach-Object { $_.ToString() }
    }
    foreach ($ip in $ips) { Write-Host "  Phone/tablet on the same Wi-Fi:  http://${ip}:$WebPort" }
    Write-Host '  Anyone on this network can reach the sign-in page. Use only on networks you trust.' -ForegroundColor Yellow
  }
  Write-Host "  API:    http://localhost:$ApiPort/docs"
  Write-Host '  Stop:   Ctrl+C'
  Write-Host ''
  while (-not $api.HasExited -and -not $web.HasExited) { Start-Sleep -Milliseconds 500 }
  if ($api.HasExited) { Write-Host "The API exited (code $($api.ExitCode))." -ForegroundColor Red }
  if ($web.HasExited) { Write-Host "The web app exited (code $($web.ExitCode))." -ForegroundColor Red }
} finally {
  foreach ($p in @($api, $web)) {
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  }
  Write-Host 'PLATO stopped.'
}
