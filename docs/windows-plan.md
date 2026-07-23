# Rencana Dukungan Windows (cross-platform)

Status: **RENCANA — belum diimplementasi.** Ditulis di mesin Linux; implementasi &
verifikasi Windows dilakukan nanti di laptop Windows.

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
| Python | `platform.system()` → `Windows` / `Linux` |

Masalah inti: **satu file skrip tak bisa jalan di kedua OS secara native** —
`.sh` butuh bash (tak ada di Windows native), `.ps1` butuh PowerShell (tak ada di
Linux by default). Hanya **Python** yang satu file bisa jalan di keduanya (asal
Python terpasang).

## Dua opsi arsitektur

### Opsi A — Rewrite Python lintas-OS  ⭐ (paling cocok untuk "auto-detect")

Satu basis kode. Struktur:

```
system-tools/
├── disktools/
│   ├── __main__.py        # entry: deteksi OS → dispatch
│   ├── core.py            # logika OS-agnostic (dashboard, inspect, format ukuran)
│   ├── platform_linux.py  # probe & aksi Linux (du, journalctl, snap, apt, ~/.config)
│   └── platform_windows.py# probe & aksi Windows (Get-Volume, %LOCALAPPDATA%, registry)
└── bin/disk-health …      # shim tipis yang memanggil python -m disktools <cmd>
```

- ✅ Satu tool, deteksi OS runtime, perilaku persis seperti yang diinginkan.
- ⚠️ Butuh Python terpasang. Windows tak bawa Python default (banyak dev punya).
- Ganti implementasi bash yang ada sekarang → effort besar.

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

## Langkah bila jadi dikerjakan

1. Pilih Opsi A (Python) atau B (PowerShell twin).
2. Mulai dari `disk-health` (read-only, aman) → validasi angka di Windows.
3. Lanjut `bloat-scan` + `chrome-ai-clean` (target yang paling bernilai).
4. Cleaner lain menyusul, uji satu per satu dengan mode dry-run.
