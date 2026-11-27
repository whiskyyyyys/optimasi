# Optimasi Windows (Python 3.11 + Nuitka)

Aplikasi desktop Windows 10/11 modern untuk **optimasi performa, gaming FPS, latency jaringan, privasi, debloat AI/Telemetry, pembersihan cache/RAM, dan perbaikan sistem**.

Dibangun ulang secara modular dari script `HI+OPTIMIZER.V6.bat` dan diperkaya dengan berbagai tweak optimasi Windows populer yang terverifikasi (CTT WinUtil, Win11Debloat, AtlasOS/ReviOS safe tweaks, Privacy.sexy, TCP Optimizer, dan SSD/DirectX maintenance), menggunakan **Python 3.11** dan dikompilasi menjadi native executable `.exe` lewat **Nuitka**.

---

## Fitur Utama

### 1. Dashboard, Safety & One-Click Profiles
- **Hardware Telemetry Live**: Deteksi otomatis CPU, RAM, Disk C:, GPU Vendor (`NVIDIA` / `AMD` / `INTEL`), OS Build, dan Power Plan aktif.
- **Safety First**:
  - Tombol **System Restore Point** (`Checkpoint-Computer`) & **Registry Backup** (`reg export`).
  - **Dry-Run Mode**: Simulasi aman semua tweak tanpa mengubah Registry atau Services.
  - **Auto Undo Snapshot**: Setiap eksekusi tweak menyimpan snapshot JSON di `%USERPROFILE%\Documents\OptimasiBackups\sessions\` yang bisa di-revert kapan saja.
  - **Admin / UAC Elevation** langsung dari header aplikasi.
- **3 One-Click Profiles**:
  - `Safe Daily Driver` (Recommended)
  - `Gaming & Low Latency Pro`
  - `Extreme / Potato PC Max FPS`

### 2. CPU & Power
- Unlock & aktifkan **Ultimate Performance Power Plan**.
- Disable **CPU Core Parking** (100% active cores) & **Power Throttling**.
- Tuning `Win32PrioritySeparation` (`0x26` / 38) untuk prioritas frame foreground.
- Profil khusus **Intel CPU Safe / Extreme** & **AMD Ryzen CPPC Scheduler**.
- Disable Hibernation (menghemat 4–16 GB SSD) & USB Selective Suspend / PCIe ASPM.

### 3. GPU & Gaming
- Enable **HAGS** (Hardware-Accelerated GPU Scheduling) + `TdrDelay` crash guard.
- **Optimizations for Windowed Games** (`SwapEffectUpgradeEnable=1`) & DirectFlip.
- Disable **GameDVR** & background Xbox screen capture.
- **MMCSS Gaming Priority** (`SystemResponsiveness=10`, `NetworkThrottlingIndex=0xFFFFFFFF`).
- Profil khusus **NVIDIA** (Safe & Extreme preemption), **AMD Radeon** (ULPS/StutterMode/Adrenalin debloat), dan **Intel GPU**.
- **Auto-Detect Installed Games** (Steam, Epic, Riot Valorant, Roblox, osu!) -> set High Performance GPU & High CPU Priority.
- **GPU MSI Mode** (Message Signaled Interrupts) & opsional **Disable VBS/Memory Integrity**.

### 4. Network & DNS
- Disable **Nagle's Algorithm** (`TcpAckFrequency=1`, `TCPNoDelay=1`) di seluruh interface aktif.
- **TCP/IP Gaming Stack** (`netsh int tcp`: RSS, FastOpen, Timestamps off, RSC off, MaxSynRetransmissions=2).
- **AFD Socket Buffer Tuning** & **Disable NIC Energy Efficient Ethernet (`*EEE`)**.
- **Quick DNS Switcher** (`Cloudflare 1.1.1.1`, `Google 8.8.8.8`, `Quad9`, `AdGuard`, `DHCP`) + **Live Ping Benchmark**.

### 5. Privacy & Debloat
- Matikan **Windows Telemetry** (`AllowTelemetry=0`, `DiagTrack`, `dmwappushservice`, CEIP Scheduled Tasks).
- Matikan **Windows 11 Copilot & AI Recall Snapshots**.
- **Debloat Microsoft Edge** (matikan Startup Boost, Background Mode, Shopping & Sidebar bloat).
- **Telemetry Hosts Blocker** (36+ domain telemetry Microsoft/MSN dalam blok bersih & reversible di file `hosts`).
- **Selective UWP Bloatware Remover** (Cortana, Clipchamp, Bing News/Weather, Solitaire, Copilot App, dll. tanpa menghapus Microsoft Store/Terminal) & OneDrive toggle.

### 6. RAM, Storage, Cleaner & System Repair
- **Auto-Tune `SvcHostSplitThresholdInKB`** sesuai total RAM fisik.
- `DisablePagingExecutive=1`, Memory Compression toggle, NTFS `disablelastaccess` & `disable8dot3`.
- **Junk & Shader Cache Scanner/Cleaner**: User/Windows Temp, Prefetch, DirectX/NVIDIA/AMD Shader Cache, Explorer Thumbnail Cache, Windows Update Cache, CrashDumps, dan Browser Caches.
- **Trim RAM Working Sets** (`EmptyWorkingSet`) secara instan.
- **System Repair Tools**: `DISM /RestoreHealth`, `DISM /StartComponentCleanup`, `sfc /scannow`, `SSD ReTrim`, `Flush DNS`, dan `Winsock/TCP Reset`.
- **Startup Programs Manager** (HKCU & HKLM Run toggle).

---

## Struktur Proyek

```text
Optimasi/
├── HI+OPTIMIZER.V6.bat          # Script referensi asli (dipertahankan utuh)
├── assets/app.ico               # Ikon aplikasi Windows multi-resolusi
├── src/optimasi/
│   ├── main.py                  # Entrypoint CLI & GUI (--dry-run, --self-test, --version)
│   ├── core/
│   │   ├── admin.py             # Deteksi Admin & UAC elevation
│   │   ├── backup.py            # Restore Point, Registry Export, & Session Undo
│   │   ├── cleaner.py           # Junk scanner/cleaner, RAM trim, DISM/SFC/TRIM
│   │   ├── executor.py          # Engine eksekusi (winreg, subprocess, dry-run, undo)
│   │   └── system_info.py       # Snapshot CPU, RAM, Disk, GPU vendor, OS, Power Plan
│   ├── tweaks/
│   │   ├── models.py            # Action & Tweak models
│   │   ├── cpu_power.py         # CPU & Power tweaks
│   │   ├── gpu_gaming.py        # GPU, DirectX, GameDVR, MSI Mode, Auto-Game boost
│   │   ├── network_dns.py       # Nagle, TCP/IP, AFD, NIC, DNS, Ping test
│   │   ├── privacy_debloat.py   # Telemetry, AI/Copilot, Edge, Hosts, AppX debloat
│   │   ├── ram_storage.py       # SvcHost auto-tuner, Kernel RAM, NTFS/SSD
│   │   ├── services_system.py   # UI tweaks & Windows Services presets
│   │   └── startup.py           # Startup Run manager
│   └── ui/
│       ├── theme.py             # Dark Slate/Cyan UI theme
│       ├── widgets.py           # StatCard & TweakCard components
│       └── app.py               # CustomTkinter desktop app
├── tests/test_optimasi.py       # Pytest unit & dry-run integration tests
├── build_nuitka.py              # Script kompilasi Nuitka (Python 3.11)
├── build.bat                    # One-click Windows build script
├── pyproject.toml
└── requirements.txt
```

---

## Menjalankan dari Source (Python 3.11)

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\activate
pip install -r requirements.txt
pip install -e . --no-deps

# Jalankan GUI
python -m optimasi.main

# Jalankan dengan mode simulasi (Dry-Run)
python -m optimasi.main --dry-run

# Jalankan unit tests
pytest -q
```

## Build Menjadi `.exe` (Nuitka + Python 3.11)

```powershell
.\.venv311\Scripts\python.exe build_nuitka.py
```
Hasil build berada di `dist\OptimasiWindows.exe` (atau unduh langsung dari halaman **GitHub Releases**).

---

## Kredit & Referensi
- **HI+OPTIMIZER V6** oleh SoftDaisy (`HI+OPTIMIZER.V6.bat`)
- Inspirasi tweak open-source komunitas: Chris Titus Tech (WinUtil), Win11Debloat, AtlasOS / ReviOS guides, dan Privacy.sexy.
