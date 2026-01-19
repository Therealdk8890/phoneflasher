# PhoneFlasher

Windows GUI tool to download ADB/Fastboot, install USB drivers, and flash images for Samsung, Pixel, LG, and OnePlus devices.

## What it does
- Downloads Google platform-tools (ADB/Fastboot) automatically
- Downloads USB drivers for Samsung, Pixel (Google), LG, and OnePlus
- Flashes selected images via fastboot (boot, recovery, system, vendor)
- Provides quick device status checks (adb/fastboot)

## Requirements
- Windows 10/11
- Python 3.10+ (Tkinter is included in standard Python installs)

## Run
```bash
py -3 src\phoneflasher.py
```

## Build a single .exe (Windows)
```bash
build.bat
```

or from PowerShell:
```powershell
./build.ps1
```

The executable will be at `dist\PhoneFlasher.exe`.

## Notes
- Driver installers may require admin rights.
- If a vendor changes a download URL, the app will open the official page as a fallback.
- Flashing can brick devices. Use firmware specific to your model and verify checksums.

## Folder layout
- `src/phoneflasher.py` - GUI app
- `src/tools/` - platform-tools extraction target
- `src/drivers/` - downloaded drivers
- `src/downloads/` - cached downloads
