$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Write-Step {
    param([int]$Number, [string]$Message)
    Write-Host ""
    Write-Host "[$Number/5] $Message" -ForegroundColor Cyan
}

function Assert-LastCommand {
    param([string]$Description)
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Warranty Label Printer - Windows Setup" -ForegroundColor Green
Write-Host "This creates a local Python environment and runs read-only checks."
Write-Host "It will NOT print a label, calibrate a printer, or install a printer driver."

Write-Step 1 "Finding a supported 64-bit Python"
$launcher = Get-Command py -ErrorAction SilentlyContinue
if ($launcher) {
    $pythonExe = $launcher.Source
    $pythonPrefix = @("-3")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Host ""
        Write-Host "Python was not found." -ForegroundColor Red
        Write-Host "Install 64-bit Python 3.11 or newer from https://www.python.org/downloads/windows/"
        Write-Host "During installation, enable 'Add python.exe to PATH', then reopen PowerShell."
        exit 1
    }
    $pythonExe = $pythonCommand.Source
    $pythonPrefix = @()
}

& $pythonExe @pythonPrefix -c "import platform,sys; ok=sys.version_info >= (3,11) and platform.machine().lower() in {'amd64','x86_64'}; print(f'Python {platform.python_version()} ({platform.machine()})'); raise SystemExit(0 if ok else '64-bit Python 3.11 or newer is required.')"
Assert-LastCommand "Python compatibility check"

Write-Step 2 "Creating or refreshing the isolated .venv"
& $pythonExe @pythonPrefix -m venv "$PSScriptRoot\.venv"
Assert-LastCommand "Virtual environment creation"
$venvPython = "$PSScriptRoot\.venv\Scripts\python.exe"

Write-Step 3 "Installing pinned application dependencies"
& $venvPython -m pip install --upgrade pip
Assert-LastCommand "pip upgrade"
& $venvPython -m pip install -r "$PSScriptRoot\requirements-windows.txt"
Assert-LastCommand "Dependency installation"
$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "Node.js/npm is required for the locked HTTPS tunnel runtime. Install Node.js LTS and rerun setup."
}
& $npmCommand.Source ci --omit=dev --ignore-scripts
Assert-LastCommand "Locked tunnel dependency installation"

Write-Step 4 "Installing the application-managed Chromium browser"
& $venvPython -m playwright install chromium
Assert-LastCommand "Chromium installation"

Write-Step 5 "Running read-only system and printer checks"
& "$PSScriptRoot\warranty-windows.ps1" doctor
Assert-LastCommand "Diagnostic check"

Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "Next:"
Write-Host "  1. Bind the USB printer: .\warranty-windows.ps1 printer"
Write-Host "  2. Try virtual output:   .\warranty-windows.ps1 safe"
Write-Host "  3. Start normal mode:    .\warranty-windows.ps1 cli"
