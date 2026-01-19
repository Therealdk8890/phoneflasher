$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r build-requirements.txt

pyinstaller --noconfirm --clean --onefile --windowed --name PhoneFlasher --distpath dist --workpath build src\phoneflasher.py

Write-Host "Built dist\PhoneFlasher.exe"
