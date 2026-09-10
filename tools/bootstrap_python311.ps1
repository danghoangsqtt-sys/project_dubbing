[CmdletBinding()]
param(
    [ValidateSet("none", "base", "local")]
    [string]$Requirements = "local",
    [switch]$SkipPipUpgrade
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$bundledFfmpeg = Join-Path $repoRoot "bin\ffmpeg"
if (Test-Path -LiteralPath $bundledFfmpeg -PathType Container) {
    $env:PATH = "$bundledFfmpeg;$env:PATH"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )
    Write-Host "> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath"
    }
}

function Test-Python311 {
    param([Parameter(Mandatory = $true)][string]$PythonPath)
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        return $false
    }
    & $PythonPath -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
    return $LASTEXITCODE -eq 0
}

$launcher = Get-Command py.exe -ErrorAction SilentlyContinue
if (-not $launcher) {
    throw "Python Launcher (py.exe) is missing. Install Python 3.11 for the current user, then rerun: winget install --id Python.Python.3.11 --scope user"
}

& $launcher.Source -3.11 -c "import sys; print(sys.executable)" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "CPython 3.11 is not registered with py.exe. Install it, then rerun: winget install --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements"
}

if (Test-Path -LiteralPath $venvRoot) {
    if (-not (Test-Python311 -PythonPath $venvPython)) {
        throw "Existing .venv is not Python 3.11. Move it aside manually to preserve recoverability, then rerun this script."
    }
    Write-Host "Reusing valid Python 3.11 environment: .venv"
} else {
    Invoke-Checked $launcher.Source -3.11 -m venv $venvRoot
}

if (-not $SkipPipUpgrade) {
    Invoke-Checked $venvPython -m pip install --upgrade "pip>=24,<26" "setuptools>=75,<81" wheel
}

switch ($Requirements) {
    "base" {
        Invoke-Checked $venvPython -m pip install -r (Join-Path $repoRoot "requirements-base.txt")
    }
    "local" {
        Invoke-Checked $venvPython -m pip install -r (Join-Path $repoRoot "requirements-local.txt")
    }
    "none" {
        Write-Host "Skipping dependency installation."
    }
}

Invoke-Checked $venvPython -c "import sys; assert sys.version_info[:2] == (3, 11); print(sys.version); print(sys.executable)"

if ($Requirements -ne "none") {
    Invoke-Checked $venvPython -c "import importlib.util; import PySide6, requests, dotenv; assert all(importlib.util.find_spec(name) is not None for name in ('pydub', 'mpv')); print('Base GUI packages: OK (native media runtimes are checked separately by preflight)')"
}

Write-Host "CapCap Python 3.11 environment is ready."
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
