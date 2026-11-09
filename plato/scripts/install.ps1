<#
.SYNOPSIS
  PLATO installer for Windows (Windows PowerShell 5.1 or PowerShell 7). Also runs under pwsh on macOS/Linux.

.DESCRIPTION
  Installs the API, the web app and the `plato` terminal client. Safe to re-run: it updates
  dependencies and keeps your existing .env and database.

  If scripts are blocked, run it once like this (affects only this run):
    powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1

.PARAMETER Python
  Python executable to use (default: auto-detect 3.11+ via the py launcher or PATH).
#>
param([string]$Python = $env:PLATO_PYTHON)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root '.venv'
$OnWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or $IsWindows

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m) { Write-Host "OK  $m" -ForegroundColor Green }
function Fail($m) { Write-Host "ERROR  $m" -ForegroundColor Red; exit 1 }
function Hint {
  if ($OnWindows) {
    Write-Host '  winget install -e --id Python.Python.3.12'
    Write-Host '  winget install -e --id OpenJS.NodeJS.LTS'
    Write-Host '  (then open a NEW PowerShell window and re-run this script)'
  } elseif ($IsMacOS) { Write-Host '  brew install python@3.12 node' }
  else { Write-Host '  Install Python 3.11+ and Node.js 20.9+ with your package manager.' }
}
# Run a native command and stop on failure (PowerShell 5.1 has no $PSNativeCommandUseErrorActionPreference).
function Run([string]$exe, [string[]]$argv) {
  & $exe @argv
  if ($LASTEXITCODE -ne 0) { Fail "'$exe $($argv -join ' ')' failed (exit $LASTEXITCODE)" }
}

Info "PLATO installer - PowerShell $($PSVersionTable.PSVersion)"

# ---------------------------------------------------------------- Python >= 3.11
$candidates = @()
if ($Python) { $candidates += ,@($Python) }
if ($OnWindows) { $candidates += ,@('py', '-3.13'); $candidates += ,@('py', '-3.12'); $candidates += ,@('py', '-3.11') }
$candidates += ,@('python3'); $candidates += ,@('python')
$Py = $null
foreach ($c in $candidates) {
  $exe = $c[0]; $pre = @(); if ($c.Count -gt 1) { $pre = $c[1..($c.Count - 1)] }
  if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
  # The Windows Store "python" stub opens the Store instead of running; the version probe filters it out.
  # No double quotes inside the code: Windows PowerShell 5.1 mangles them when calling native programs.
  $out = & $exe @pre -c 'import sys; print(sys.executable if sys.version_info >= (3, 11) else str())' 2>$null
  if ($LASTEXITCODE -eq 0 -and "$out".Trim()) { $Py = "$out".Trim(); break }
}
if (-not $Py) { Write-Host 'Python 3.11+ is required:'; Hint; exit 1 }
Ok "Python $(& $Py -c 'import platform; print(platform.python_version())') ($Py)"

# ---------------------------------------------------------------- Node >= 20.9
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Write-Host 'Node.js 20.9+ is required:'; Hint; exit 1 }
$nodeVer = [version]((& node -v).Trim().TrimStart('v'))
if ($nodeVer -lt [version]'20.9.0') { Write-Host "Node.js $nodeVer is too old; 20.9+ is required:"; Hint; exit 1 }
Ok "Node.js $(node -v)"
# npm.cmd, not npm.ps1: the .ps1 shim is blocked under the default Windows execution policy.
$Npm = if ($OnWindows) { 'npm.cmd' } else { 'npm' }

# ---------------------------------------------------------------- backend + CLI
Info "Installing the API and the plato CLI into $Venv"
$VenvPy = if ($OnWindows) { Join-Path $Venv 'Scripts\python.exe' } else { Join-Path $Venv 'bin/python' }
if (-not (Test-Path $VenvPy)) { Run $Py @('-m', 'venv', $Venv) }
Run $VenvPy @('-m', 'pip', 'install', '-q', '--upgrade', 'pip')
Run $VenvPy @('-m', 'pip', 'install', '-q', '-r', (Join-Path $Root 'backend/requirements.txt'))
Run $VenvPy @('-m', 'pip', 'install', '-q', (Join-Path $Root 'cli'))
Ok 'API and CLI installed'

# ---------------------------------------------------------------- web app
Info 'Building the web app'
Push-Location (Join-Path $Root 'frontend')
try {
  $env:NEXT_TELEMETRY_DISABLED = '1'
  Run $Npm @('ci', '--no-audit', '--no-fund', '--loglevel=error')
  Run $Npm @('run', 'build', '--silent')
} finally { Pop-Location }
Ok 'Web app built'

# ---------------------------------------------------------------- configuration
$EnvFile = Join-Path $Root '.env'
if (-not (Test-Path $EnvFile)) {
  $gen = @'
import secrets, sys
from pathlib import Path
from cryptography.fernet import Fernet
root = Path(sys.argv[1])
text = (root / ".env.example").read_text(encoding="utf-8")
text = text.replace("PLATO_JWT_SECRET=change-me-to-a-long-random-string", f"PLATO_JWT_SECRET={secrets.token_urlsafe(48)}")
text = text.replace("PLATO_ENCRYPTION_KEY=\n", f"PLATO_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n", 1)
text += f"\n# Local database (created by the installer)\nPLATO_DATABASE_URL=sqlite+aiosqlite:///{(root / 'plato.db').as_posix()}\n"
(root / ".env").write_text(text, encoding="utf-8")
'@
  $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "plato-env-$PID.py"
  Set-Content -Path $tmp -Value $gen -Encoding UTF8
  try { Run $VenvPy @($tmp, $Root) } finally { Remove-Item $tmp -ErrorAction SilentlyContinue }
  if ($OnWindows) {
    # Restrict .env (it holds secrets) to the current user.
    & icacls $EnvFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
  } else { & chmod 600 $EnvFile }
  Ok 'Created .env with fresh secrets (keep it private)'
} else { Ok 'Kept existing .env' }

$PlatoExe = if ($OnWindows) { Join-Path $Venv 'Scripts\plato.exe' } else { Join-Path $Venv 'bin/plato' }
Write-Host ''
Info 'PLATO is installed.'
Write-Host "  Start:         .\scripts\start.ps1          (this computer only)"
Write-Host "                 .\scripts\start.ps1 -Lan     (also phones/tablets on your Wi-Fi)"
Write-Host "  Terminal app:  $PlatoExe --help"
