# Rencana Dukungan Windows (cross-platform)

Status: **SEDANG DIIMPLEMENTASI (Opsi A — Python).** Divalidasi & mulai dikerjakan
di mesin Windows nyata (Win11, PowerShell 5.1, 2 disk: C: SSD-sistem + D: HDD-data).
Lihat **[Status implementasi](#status-implementasi)** di bawah untuk yang sudah jalan.

## Tujuan

Satu suite yang **mendeteksi OS otomatis** saat dijalankan (Windows atau Linux),
lalu memakai cara ukur/hapus yang sesuai. Command & konsep sama di kedua OS:
`disk-health`, `disk-inspect`, `bloat-scan`, `chrome-clean`, `chrome-ai-clean`, dst.

Arsitektur sekarang (bash + GNU coreutils) **hanya Linux**. Windows butuh
implementasi terpisah — tapi konsep/altitude-nya identik, tinggal ganti "mesin".

## Cara deteksi OS

| Runtime | Deteksi |
|---------|---------|
| POSIX sh/bash | `uname -s` → `Linux` / `MINGW*`/`MSYS*` (Git Bash) |
| PowerShell 6+ | `$IsWindows`, `$IsLinux` |
| PowerShell 5.1 (Win10/11 default) | `$env:OS -eq 'Windows_NT'` atau `[Environment]::OSVersion.Platform` |
| **Python** ⭐ (dipakai) | `platform.system()` → `Windows` / `Linux` / `Darwin` |

> ⚠️ **Koreksi (divalidasi di mesin nyata):** `$IsWindows`/`$IsLinux` **hanya ada
> di PowerShell 6+**. Windows 10/11 default-nya **PowerShell 5.1**, di mana
> `$IsWindows` bernilai `$null` → `if ($IsWindows)` akan **salah** menganggap
> "bukan Windows". Karena Opsi A dipilih, deteksi memakai `platform.system()`
> (Python), jadi persoalan ini tak relevan lagi untuk runtime utama.

Masalah inti: **satu file skrip tak bisa jalan di kedua OS secara native** —
`.sh` butuh bash (tak ada di Windows native), `.ps1` butuh PowerShell (tak ada di
Linux by default). Hanya **Python** yang satu file bisa jalan di keduanya (asal
Python terpasang).

## Dua opsi arsitektur

### Opsi A — Rewrite Python lintas-OS  ✅ **DIPILIH** (paling cocok untuk "auto-detect")

Satu basis kode. Struktur **nyata (sudah dibuat):**

```
system-tools/
├── disktools/
│   ├── __main__.py         # entry: deteksi OS → parse flag → dispatch command
│   ├── core.py             # OS-agnostic: format, status-dot, Drive model,
│   │                       #   pick_drives (user pilih drive), dir_size, reclaim
│   ├── commands.py         # presentasi command (disk-health, bloat-scan, cleaners)
│   ├── platform_linux.py   # probe & aksi Linux (/proc/mounts, /sys, ~/.cache, Trash)
│   └── platform_windows.py # probe & aksi Windows (Get-Volume/Get-PhysicalDisk,
│                           #   %LOCALAPPDATA%, $Recycle.Bin)
├── bin/                    # shim per-command (disk-health.cmd, bloat-scan.cmd, …)
└── install.ps1             # bikin shim + tambah bin ke PATH (Windows)
```

- ✅ Satu tool, deteksi OS runtime, perilaku persis seperti yang diinginkan.
- ✅ Zero **extra**-dependency: stdlib Python saja; detail disk Windows lewat
  PowerShell (`Get-Volume`/`Get-PhysicalDisk`), Linux lewat `/proc` + `/sys`.
- ⚠️ Butuh Python terpasang. Windows tak bawa Python default (banyak dev punya;
  di mesin ini Python 3.14 sudah ada).
- Bash lama **tidak dihapus** — `disktools/` additive, ditulis berdampingan.

### Opsi B — Kembar native (bash + PowerShell) dengan spec bersama

- `scripts/` (bash, Linux) — yang sudah ada.
- `scripts-windows/` (`.ps1`, Windows) — port dari spec di bawah.
- `install.sh` (Linux) & `install.ps1` (Windows) — masing-masing install stack yang benar.
- "Deteksi" terjadi di installer (pilih stack sesuai OS), bukan runtime satu file.

- ✅ Zero-dependency: bash pasti ada di Linux, PowerShell pasti ada di Win10/11.
- ✅ Bisa dikerjakan bertahap; yang Linux tak perlu diubah.
- ⚠️ Dua basis kode yang harus dijaga sinkron.

**Rekomendasi:** kalau target utama "satu command auto-detect" → **Opsi A (Python)**.
Kalau mau cepat & tanpa dependency baru → **Opsi B (PowerShell twin)**.

## Pemetaan konsep → Windows

| Konsep (Linux) | Padanan Windows | Catatan |
|---|---|---|
| pemakaian disk (`df`) | `Get-Volume` / `Get-PSDrive C` | |
| ukuran folder (`du -sb`) | `Get-ChildItem -Recurse -File -Force \| Measure Length -Sum` | lambat; alternatif: `du.exe` Sysinternals |
| `~/.cache`, `~/.config` | `%LOCALAPPDATA%`, `%APPDATA%` | `C:\Users\<u>\AppData\Local` & `\Roaming` |
| Trash (`~/.local/share/Trash`) | `Clear-RecycleBin -Force` | |
| `chrome-clean` | `%LOCALAPPDATA%\Google\Chrome\User Data\<Profile>\Cache` | + `Code Cache`, `GPUCache` |
| `chrome-sw-clean` | `…\<Profile>\Service Worker\CacheStorage` | |
| `chrome-ai-clean` (OptGuide 4GB) | `…\User Data\OptGuideOnDeviceModel` | + `optimization_guide_model_store`, `screen_ai` |
| policy anti-download AI | Registry `HKLM\SOFTWARE\Policies\Google\Chrome` → DWORD `GenAILocalFoundationalModelSettings=1` | butuh admin; cek `chrome://policy` |
| `node-clean` | `npm cache clean`, `pip cache purge`, pnpm store | cache di `%LOCALAPPDATA%\npm-cache`, `%LOCALAPPDATA%\pip\Cache` |
| `docker-clean` | `docker system prune` | Docker Desktop; sama |
| `journal-clean` | Event Logs: `wevtutil el` + `wevtutil cl <log>`; CBS logs | tak ada journald |
| `apt-clean` | `cleanmgr /sagerun`, `DISM /Online /Cleanup-Image /StartComponentCleanup` | admin |
| `snap-clean` | winget cache / Microsoft Store cache (`wsreset`) | tak ada snap |
| `bloat-scan` | sama, lokasi model Windows (lihat bawah) | |
| `junk-report` | sama; sapu file besar via `Get-ChildItem -Recurse` | |
| konfirmasi `/dev/tty` | `Read-Host` | |
| cek browser jalan (`pgrep`) | `Get-Process chrome -ErrorAction SilentlyContinue` | |

## Cleaner khusus Windows (belum ada padanan Linux — tambahan)

| Target | Cara | Perkiraan |
|---|---|---|
| Temp user & sistem | hapus `$env:TEMP`, `C:\Windows\Temp` | sering ratusan MB–GB |
| Windows Update cache | stop `wuauserv` → hapus `C:\Windows\SoftwareDistribution\Download` | bisa GB |
| Component store (WinSxS) | `DISM /Online /Cleanup-Image /StartComponentCleanup` | GB |
| `Windows.old` (bekas upgrade) | `cleanmgr` / DISM | belasan GB |
| Delivery Optimization | `Delete-DeliveryOptimizationCache -Force` | |
| Thumbnail cache | hapus `%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db` | |
| Recycle Bin | `Clear-RecycleBin -Force` | |

## Lokasi "silent bloat" Windows (untuk bloat-scan)

- `…\User Data\OptGuideOnDeviceModel` (model AI Chrome, ~GB)
- `%LOCALAPPDATA%\Programs\*` (aplikasi Electron per-user, mis. VS Code, Discord)
- `%USERPROFILE%\.vscode\extensions`, `%APPDATA%\Code\CachedExtensionVSIXs`
- `%USERPROFILE%\.cache\huggingface`, `.ollama\models`, `torch`
- `%USERPROFILE%\.gradle\caches`, `.nuget\packages`, `.android`
- `%LOCALAPPDATA%\Microsoft\WindowsApps`, `%LOCALAPPDATA%\Docker`
- Sapu heuristik: file `*.gguf *.onnx *.safetensors *.bin *.pt weights*` ≥ ambang

## Prinsip yang dipertahankan lintas-OS

- Read-only untuk yang tak yakin; hapus selalu konfirmasi + lapor ruang bebas.
- Tak auto-hapus berdasarkan umur file.
- Tandai cache/junk yang aman (`♻`).
- Operasi butuh admin/root ditandai jelas (di Windows: butuh "Run as Administrator").

## Peringatan pengujian

Semua yang Windows **harus diverifikasi di mesin Windows** — tak bisa dites dari
Linux. Path registry & cmdlet di atas berdasarkan Win10/11 standar; konfirmasi
`GenAILocalFoundationalModelSettings` di `chrome://policy` setelah set.

## Status implementasi

Paket `disktools/` (Opsi A). Perilaku disk: **user pilih drive mana pun**
(`--drive C[,D]`, `--all`, atau prompt; non-interaktif → drive sistem).

| Command | Status | Catatan |
|---|---|---|
| deteksi OS | ✅ jalan | `platform.system()` → backend Windows/Linux |
| enumerasi drive + SSD/HDD | ✅ jalan (Windows) | `Get-Volume`+`Get-PhysicalDisk`; Linux `/proc`+`/sys` (belum diuji di Linux) |
| `disk-health` | ✅ jalan (read-only) | dashboard drive + recoverable per-drive + rekomendasi |
| `bloat-scan` | ✅ jalan (read-only) | lokasi silent-bloat + sapu file model besar (`.gguf/.onnx/.safetensors/…`) |
| `disk-inspect` | ✅ jalan | listing folder (♻ marker); `-i` navigasi + hapus terarah (`d N`, `d 2-6`, `d all`) |
| `system-clean` | ✅ jalan (hapus) | orkestrasi temp+node+chrome+trash, 1 konfirmasi, lapor total freed |
| `temp-clean` | ✅ jalan (hapus) | dry-run + konfirmasi + lapor freed |
| `node-clean` | ✅ jalan (hapus) | cache npm/pip |
| `chrome-clean` | ✅ jalan (hapus) | warning kalau browser jalan |
| `chrome-ai-clean` | ✅ jalan (hapus) | hapus model on-device; policy `--disable` (registry, admin) belum |
| `trash-clean` | ✅ jalan (hapus) | `Clear-RecycleBin` per drive |
| cleaner lain (snap/apt/journal/docker) | ⬜ belum/N-A | padanan Windows: cleanmgr/DISM/wevtutil (menyusul) |
| verifikasi backend Linux | ⬜ belum | wajib diuji di mesin Ubuntu nyata |

## Langkah bila jadi dikerjakan

1. ✅ Pilih Opsi A (Python) atau B (PowerShell twin). → **Opsi A dipilih.**
2. ✅ Mulai dari `disk-health` (read-only, aman) → validasi angka di Windows.
3. ✅ Lanjut `bloat-scan` + `chrome-ai-clean` (target yang paling bernilai).
4. ◻ Cleaner lain menyusul, uji satu per satu dengan mode dry-run.
5. ◻ Verifikasi seluruh backend Linux di mesin Ubuntu.
