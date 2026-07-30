$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = "$PSScriptRoot\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Run .\setup-windows.ps1 first."
}

& $python main.py --mode cli @args
exit $LASTEXITCODE
