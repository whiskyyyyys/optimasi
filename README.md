# Optimasi Windows v2.2.0 (Python 3.11 + Nuitka + Windows Installer)

Aplikasi desktop **Windows 10/11** bergaya **Obsidian Dark Fluent (PySide6)** dengan ikon vektor SVG untuk optimasi performa laptop & PC, **Deep RAM Optimizer & Auto-RAM Guard**, gaming FPS, emulator (MuMuPlayer/BlueStacks/LDPlayer), latensi jaringan, privasi/AI debloat, pembersihan cache, serta perbaikan sistem.

Dilengkapi **Windows Installer resmi (`OptimasiWindows-Setup-2.1.0.exe`)** dan **In-App Auto-Updater** yang mengecek & mengunduh update langsung dari GitHub Releases secara otomatis di dalam aplikasi tanpa perlu download manual.

---

## Yang Baru di v2.1.0

- **Redesain UI Obsidian Dark Fluent + Ikon Vektor SVG**:
  - Palet Obsidian/Zinc yang jauh lebih bersih & elegan, ikon vektor SVG tajam di seluruh navigasi & tombol, console log tersembunyi secara default dengan status bar ramping + **Floating Toast Notifications** di pojok kanan bawah.
- **Deep RAM Optimizer & Auto-RAM Guard (ISLC / MemReduct Style)**:
  - **Breakdown Memori Real-Time** (Active, Standby/Cache, Free, Commit) + Donut Gauge & Segmented Bar.
  - **Bersihkan RAM (Deep Clean)**: Gabungan Working-Set Trim + System File Cache Flush + Standby Memory List Purge (`NtSetSystemInformation`).
  - **Auto-Clean RAM Guard**: Pembersihan otomatis di latar belakang ketika pemakaian RAM melewati threshold (`70%` / `75%` / `80%` / `85%`).
  - **Per-App RAM Trimmer**: Tekan `Trim` pada aplikasi pemakan RAM untuk melegakan memori **tanpa menutup aplikasi**.
  - Tambahan tweak RAM baru: **Matikan Aplikasi Background Windows** & **Browser RAM Diet (Chrome & Edge Sleeping Tabs)**.

- **Tampilan Modern Commercial-Grade (PySide6 Dark Fluent)**:
  - Native Windows 11 Dark Titlebar (`DwmSetWindowAttribute`), animated **Circular Optimization Score Gauge (0–100, Grade S–D)**, grafik **Live Sparkline** real-time (CPU, RAM, Network KB/s), animated pill **ToggleSwitch**, dan **System Tray** dengan notifikasi Windows.
- **Real Windows App Installer (`Inno Setup 6`)**:
  - Terinstall rapi ke `%LOCALAPPDATA%\Programs\Optimasi Windows\`, lengkap dengan shortcut Start Menu, Desktop, dan Uninstaller di Windows Apps & Features.
- **In-App Auto-Updater (Tanpa Download Manual di GitHub)**:
  - Otomatis cek rilis terbaru di GitHub saat aplikasi dibuka, menampilkan banner notifikasi + tray toast, changelog lengkap, download progress bar, lalu menjalankan silent in-place upgrade & auto-restart.
- **Preset Khusus Laptop Modern (`Laptop Ryzen/iGPU Pro` & `Laptop Cool & Battery Saver`)**:
  - Dirancang aman untuk laptop seperti **AMD Ryzen 5 6600H + Radeon 660M iGPU + 16 GB RAM**: performa penuh saat colok charger (AC), hemat daya & adem saat baterai (DC), tetap menjaga **Memory Compression, Wi-Fi, Bluetooth, Sleep**, serta otomatis mendeteksi dan memprioritaskan game + emulator (**MuMuPlayer**, BlueStacks, LDPlayer, Steam, Epic, Riot, Roblox).
- **Fitur Baru Tambahan**:
  - **1-Click Game & Emulator Booster** (dengan tombol Restore Power Plan).
  - **Laptop Thermal AC/DC CPU Boost Controller** (`Cool & Quiet 99%/80%`, `Balanced Laptop`, `Max Turbo`).
  - **Live Top Processes Monitor** dengan proteksi proses sistem & tombol End Task.
  - **Multi-Region Ping Benchmark** (Cloudflare, Google, Quad9, AdGuard, Singapore, Tokyo).
  - **Installed UWP Bloatware Detector** & **Visual Undo Timeline**.

---

## Preset Profil Tersedia

| Preset | Cocok Untuk | Ringkasan |
|---|---|---|
| **Laptop Ryzen/iGPU Pro** | Laptop modern (ADVAN / Ryzen / Intel + iGPU 16GB) | AC 100% / DC 80%, AMD/Intel tuning, HAGS, GameDVR off, MuMuPlayer/Game boost, Nagle/TCP, AI/Edge debloat, Memory Compression tetap ON |
| **Laptop Cool & Battery Saver** | Kerja harian, kampus, baterai awet & kipas senyap | Cap CPU 99% AC / 80% DC (tanpa turbo spike panas), matikan telemetry & bloat |
| **Gaming & Emulator Max FPS** | Bermain game berat sambil colok charger | Ultimate Performance, unparked cores, MMCSS, Raw Mouse 1:1, Auto-Game/Emulator boost |
| **Safe Daily Driver** | Semua PC/Laptop | Optimasi harian nol risiko dengan revert penuh |

---

## Cara Install (Pengguna Windows)

1. Unduh **`OptimasiWindows-Setup-2.0.0.exe`** dari halaman **[GitHub Releases](https://github.com/whiskyyyyys/optimasi/releases/latest)**.
2. Jalankan installer seperti aplikasi Windows biasa (otomatis membuat shortcut Desktop & Start Menu).
3. Untuk update versi berikutnya, cukup klik notifikasi **"Update Sekarang"** langsung di dalam aplikasi!

---

## Menjalankan dari Source & Build Ulang (Python 3.11)

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\activate
pip install -r requirements.txt
pip install -e . --no-deps

# Jalankan GUI
python -m optimasi.main

# Jalankan unit tests
pytest -v

# Build Nuitka standalone + Inno Setup Installer
python build_nuitka.py --managed-gcc
```

---

## Kredit & Referensi
- **HI+OPTIMIZER V6** (`HI+OPTIMIZER.V6.bat`) oleh SoftDaisy (dipertahankan utuh di root repo).
- Referensi tweak komunitas: CTT WinUtil, Win11Debloat, AtlasOS / ReviOS guides, Privacy.sexy, dan TCP Optimizer.
