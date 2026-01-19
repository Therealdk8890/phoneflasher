@echo off
setlocal

if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r build-requirements.txt

pyinstaller --noconfirm --clean --onefile --windowed --name PhoneFlasher --distpath dist --workpath build src\phoneflasher.py

echo Built dist\PhoneFlasher.exe
endlocal
