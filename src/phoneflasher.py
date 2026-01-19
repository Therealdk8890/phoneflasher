import os
import queue
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

APP_NAME = "PhoneFlasher"
APP_AUTHOR = "Daniel Kissel"

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
DRIVERS_DIR = BASE_DIR / "drivers"
DOWNLOADS_DIR = BASE_DIR / "downloads"

PLATFORM_TOOLS_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
PLATFORM_TOOLS_ZIP = DOWNLOADS_DIR / "platform-tools-latest-windows.zip"

DRIVER_SOURCES = {
    "Google (Pixel) USB Driver": {
        "type": "zip",
        "urls": [
            "https://dl.google.com/android/repository/latest_usb_driver_windows.zip",
        ],
        "fallback_url": "https://developer.android.com/studio/run/win-usb",
    },
    "Samsung USB Driver": {
        "type": "exe",
        "urls": [
            "https://developer.samsung.com/assets/shared/contents/file/SAMSUNG_USB_Driver_for_Mobile_Phones.exe",
        ],
        "fallback_url": "https://developer.samsung.com/android-usb-driver",
    },
    "LG USB Driver": {
        "type": "exe",
        "urls": [
            "https://www.lg.com/us/support/assets/software/Drivers/LGMobileDriver_WHQL_Ver_4.9.9.exe",
        ],
        "fallback_url": "https://www.lg.com/us/support/help-library/lg-mobile-drivers-20150771213855",
    },
    "OnePlus USB Driver": {
        "type": "exe",
        "urls": [
            "https://download.oneplus.com/OnePlus_USB_Drivers_Setup.exe",
        ],
        "fallback_url": "https://www.oneplus.com/support/softwareupgrade",
    },
}


def ensure_dirs():
    for path in (TOOLS_DIR, DRIVERS_DIR, DOWNLOADS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def platform_tools_paths():
    adb = TOOLS_DIR / "platform-tools" / "adb.exe"
    fastboot = TOOLS_DIR / "platform-tools" / "fastboot.exe"
    return adb, fastboot


def is_windows():
    return os.name == "nt"


def open_path(path):
    try:
        os.startfile(path)  # noqa: S606
    except Exception:
        return False
    return True


class PhoneFlasherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {APP_AUTHOR}")
        self.geometry("980x720")
        self.resizable(True, True)

        self.log_queue = queue.Queue()
        self._build_ui()
        self._start_log_pump()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=(12, 0))

        title = ttk.Label(header, text=APP_NAME, font=("Segoe UI", 18, "bold"))
        author = ttk.Label(header, text=f"by {APP_AUTHOR}", font=("Segoe UI", 10))
        subtitle = ttk.Label(
            header,
            text="ADB/Fastboot flasher for Samsung, Pixel, LG, and OnePlus",
            font=("Segoe UI", 10),
        )
        title.pack(anchor="w")
        author.pack(anchor="w")
        subtitle.pack(anchor="w")

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.setup_tab = ttk.Frame(notebook)
        self.flash_tab = ttk.Frame(notebook)
        self.log_tab = ttk.Frame(notebook)

        notebook.add(self.setup_tab, text="Setup")
        notebook.add(self.flash_tab, text="Flash")
        notebook.add(self.log_tab, text="Logs")

        self._build_setup_tab()
        self._build_flash_tab()
        self._build_log_tab()

    def _build_setup_tab(self):
        tools_frame = ttk.LabelFrame(self.setup_tab, text="Platform Tools")
        tools_frame.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(
            tools_frame,
            text="Download and extract ADB/Fastboot to the local tools folder.",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        tools_buttons = ttk.Frame(tools_frame)
        tools_buttons.pack(anchor="w", padx=8, pady=(0, 8))

        ttk.Button(
            tools_buttons, text="Download Platform Tools", command=self.download_platform_tools
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            tools_buttons, text="Open Tools Folder", command=lambda: self._open_folder(TOOLS_DIR)
        ).pack(side=tk.LEFT)

        drivers_frame = ttk.LabelFrame(self.setup_tab, text="USB Drivers")
        drivers_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(
            drivers_frame,
            text="Download and install the drivers for each brand. Installer executables may require admin rights.",
            wraplength=820,
        ).pack(anchor="w", padx=8, pady=(8, 4))

        ttk.Button(
            drivers_frame, text="Download All Drivers", command=self.download_all_drivers
        ).pack(anchor="w", padx=8, pady=(0, 8))

        for driver_name in DRIVER_SOURCES:
            row = ttk.Frame(drivers_frame)
            row.pack(fill=tk.X, padx=8, pady=6)

            ttk.Label(row, text=driver_name, width=28).pack(side=tk.LEFT)
            ttk.Button(
                row,
                text="Download",
                command=lambda name=driver_name: self.download_driver(name),
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                row,
                text="Install",
                command=lambda name=driver_name: self.install_driver(name),
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                row,
                text="Open Folder",
                command=lambda name=driver_name: self._open_driver_folder(name),
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                row,
                text="Open Vendor Page",
                command=lambda name=driver_name: self._open_driver_page(name),
            ).pack(side=tk.LEFT)

    def _build_flash_tab(self):
        device_frame = ttk.LabelFrame(self.flash_tab, text="Device Status")
        device_frame.pack(fill=tk.X, padx=8, pady=8)

        buttons = ttk.Frame(device_frame)
        buttons.pack(anchor="w", padx=8, pady=(8, 4))

        ttk.Button(buttons, text="Refresh Devices", command=self.refresh_devices).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(buttons, text="Reboot to Bootloader", command=self.reboot_bootloader).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(buttons, text="Reboot to System", command=self.reboot_system).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(buttons, text="Fastboot Reboot", command=self.fastboot_reboot).pack(
            side=tk.LEFT
        )

        status_frame = ttk.Frame(device_frame)
        status_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Label(status_frame, text="ADB:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, text="Fastboot:").grid(row=1, column=0, sticky="w")

        self.adb_status = ttk.Label(status_frame, text="Not checked")
        self.fastboot_status = ttk.Label(status_frame, text="Not checked")

        self.adb_status.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.fastboot_status.grid(row=1, column=1, sticky="w", padx=(8, 0))

        flash_frame = ttk.LabelFrame(self.flash_tab, text="Flash Images")
        flash_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(
            flash_frame,
            text="Select image files to flash with fastboot. Only selected slots will be flashed.",
            wraplength=820,
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self.flash_entries = {}
        for label, key in (
            ("Boot image", "boot"),
            ("Recovery image", "recovery"),
            ("System image", "system"),
            ("Vendor image", "vendor"),
        ):
            row = ttk.Frame(flash_frame)
            row.pack(fill=tk.X, padx=8, pady=4)

            ttk.Label(row, text=label, width=14).pack(side=tk.LEFT)
            entry = ttk.Entry(row)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            ttk.Button(
                row,
                text="Browse",
                command=lambda e=entry: self._browse_file(e),
            ).pack(side=tk.LEFT)
            self.flash_entries[key] = entry

        action_row = ttk.Frame(flash_frame)
        action_row.pack(anchor="w", padx=8, pady=8)

        ttk.Button(action_row, text="Flash Selected", command=self.flash_selected).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(action_row, text="Wipe Data", command=self.fastboot_wipe).pack(
            side=tk.LEFT
        )

        ttk.Label(
            flash_frame,
            text="Warning: Flashing can brick your device. Always use brand-specific firmware.",
            foreground="#b54b00",
        ).pack(anchor="w", padx=8, pady=(0, 8))

    def _build_log_tab(self):
        self.log_output = ScrolledText(self.log_tab, height=18)
        self.log_output.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.log_output.configure(state="disabled")

    def _start_log_pump(self):
        self.after(100, self._flush_log)

    def _flush_log(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_output.configure(state="normal")
            timestamp = time.strftime("%H:%M:%S")
            self.log_output.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_output.see(tk.END)
            self.log_output.configure(state="disabled")
        self.after(100, self._flush_log)

    def log(self, message):
        self.log_queue.put(message)

    def _run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def _open_folder(self, path):
        if not open_path(str(path)):
            messagebox.showerror(APP_NAME, "Failed to open folder.")

    def _open_driver_page(self, driver_name):
        url = DRIVER_SOURCES[driver_name]["fallback_url"]
        try:
            os.startfile(url)  # noqa: S606
        except Exception:
            messagebox.showerror(APP_NAME, "Failed to open vendor page.")

    def _open_driver_folder(self, driver_name):
        driver_dir = DRIVERS_DIR / driver_name.replace(" ", "_").lower()
        driver_dir.mkdir(parents=True, exist_ok=True)
        self._open_folder(driver_dir)

    def _browse_file(self, entry):
        file_path = filedialog.askopenfilename(
            title="Select image",
            filetypes=[("Image files", "*.img"), ("All files", "*.*")],
        )
        if file_path:
            entry.delete(0, tk.END)
            entry.insert(0, file_path)

    def download_platform_tools(self):
        self._run_in_thread(self._download_platform_tools)

    def _download_platform_tools(self):
        ensure_dirs()
        self.log("Downloading platform-tools...")
        success = self._download_first_available([PLATFORM_TOOLS_URL], PLATFORM_TOOLS_ZIP)
        if not success:
            self.log("Failed to download platform-tools.")
            return
        self.log("Extracting platform-tools...")
        try:
            with zipfile.ZipFile(PLATFORM_TOOLS_ZIP, "r") as zip_ref:
                zip_ref.extractall(TOOLS_DIR)
        except zipfile.BadZipFile:
            self.log("Downloaded platform-tools zip is corrupted.")
            return
        self.log("Platform-tools extracted.")

    def download_all_drivers(self):
        self._run_in_thread(self._download_all_drivers)

    def _download_all_drivers(self):
        for driver_name in DRIVER_SOURCES:
            self.log(f"Downloading {driver_name}...")
            self._download_driver(driver_name)

    def download_driver(self, driver_name):
        self._run_in_thread(self._download_driver, driver_name)

    def _download_driver(self, driver_name):
        ensure_dirs()
        info = DRIVER_SOURCES[driver_name]
        driver_dir = DRIVERS_DIR / driver_name.replace(" ", "_").lower()
        driver_dir.mkdir(parents=True, exist_ok=True)

        ext = ".zip" if info["type"] == "zip" else ".exe"
        dest = driver_dir / f"{driver_name.replace(' ', '_').lower()}{ext}"

        success = self._download_first_available(info["urls"], dest)
        if not success:
            self.log(f"Failed to download {driver_name}. Opening vendor page.")
            self._open_driver_page(driver_name)
            return

        if info["type"] == "zip":
            try:
                with zipfile.ZipFile(dest, "r") as zip_ref:
                    zip_ref.extractall(driver_dir)
                self.log(f"Extracted {driver_name} driver zip.")
            except zipfile.BadZipFile:
                self.log(f"Downloaded {driver_name} zip is corrupted.")
        else:
            self.log(f"Saved {driver_name} installer.")

    def install_driver(self, driver_name):
        info = DRIVER_SOURCES[driver_name]
        driver_dir = DRIVERS_DIR / driver_name.replace(" ", "_").lower()
        if not driver_dir.exists():
            messagebox.showinfo(APP_NAME, "Please download the driver first.")
            return

        if info["type"] == "zip":
            self.log(
                f"{driver_name} is a zip. Open the folder and install via Device Manager."
            )
            self._open_driver_folder(driver_name)
            return

        installers = list(driver_dir.glob("*.exe"))
        if not installers:
            messagebox.showinfo(APP_NAME, "Installer not found. Download the driver first.")
            return

        installer = installers[0]
        self.log(f"Launching {installer.name}...")
        try:
            os.startfile(str(installer))  # noqa: S606
        except Exception:
            messagebox.showerror(APP_NAME, "Failed to launch installer.")

    def _download_first_available(self, urls, dest):
        for url in urls:
            try:
                self._download_file(url, dest)
                if dest.exists() and dest.stat().st_size > 0:
                    return True
            except Exception as exc:
                self.log(f"Download failed: {url} ({exc})")
        return False

    def _download_file(self, url, dest):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": f"{APP_NAME}/1.0"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            total_header = response.getheader("Content-Length")
            total = int(total_header) if total_header and total_header.isdigit() else 0
            downloaded = 0
            last_logged = -1
            chunk_size = 256 * 1024
            with open(dest, "wb") as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = int((downloaded / total) * 100)
                        bucket = percent // 10
                        if bucket > last_logged:
                            last_logged = bucket
                            self.log(f"Downloading {dest.name}: {bucket * 10}%")

    def refresh_devices(self):
        self._run_in_thread(self._refresh_devices)

    def _refresh_devices(self):
        adb_path, fastboot_path = platform_tools_paths()
        adb_out = self._run_cmd([str(adb_path), "devices"]) if adb_path.exists() else ""
        fastboot_out = (
            self._run_cmd([str(fastboot_path), "devices"]) if fastboot_path.exists() else ""
        )

        adb_status = "No device" if "\tdevice" not in adb_out else "Device connected"
        fastboot_status = (
            "No device" if not fastboot_out.strip() else "Device connected"
        )

        self.after(0, self._set_device_status, adb_status, fastboot_status)

        if not adb_path.exists() or not fastboot_path.exists():
            self.log("Platform-tools not installed. Download them in Setup.")
        else:
            self.log("Refreshed device status.")

    def _set_device_status(self, adb_status, fastboot_status):
        self.adb_status.configure(text=adb_status)
        self.fastboot_status.configure(text=fastboot_status)

    def reboot_bootloader(self):
        self._run_in_thread(self._adb_command, "reboot", "bootloader")

    def reboot_system(self):
        self._run_in_thread(self._adb_command, "reboot")

    def fastboot_reboot(self):
        self._run_in_thread(self._fastboot_command, "reboot")

    def fastboot_wipe(self):
        if not messagebox.askyesno(
            APP_NAME,
            "This will wipe user data. Continue?",
        ):
            return
        self._run_in_thread(self._fastboot_command, "-w")

    def flash_selected(self):
        selections = {}
        for key, entry in self.flash_entries.items():
            value = entry.get().strip()
            if value:
                selections[key] = value

        if not selections:
            messagebox.showinfo(APP_NAME, "Select at least one image to flash.")
            return

        self._run_in_thread(self._flash_images, selections)

    def _flash_images(self, selections):
        for partition, image_path in selections.items():
            self.log(f"Flashing {partition} from {image_path}...")
            self._fastboot_command("flash", partition, image_path)

        self.log("Flash sequence complete.")

    def _adb_command(self, *args):
        adb_path, _ = platform_tools_paths()
        if not adb_path.exists():
            self.log("ADB not found. Download platform-tools first.")
            return
        self._run_cmd([str(adb_path), *args])

    def _fastboot_command(self, *args):
        _, fastboot_path = platform_tools_paths()
        if not fastboot_path.exists():
            self.log("Fastboot not found. Download platform-tools first.")
            return
        self._run_cmd([str(fastboot_path), *args])

    def _run_cmd(self, cmd):
        self.log(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            self.log("Command not found.")
            return ""

        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if output:
            self.log(output)
        return output


if __name__ == "__main__":
    ensure_dirs()
    app = PhoneFlasherApp()
    if not is_windows():
        messagebox.showwarning(
            APP_NAME,
            "This app is designed for Windows. Some features may not work on this OS.",
        )
    app.mainloop()
