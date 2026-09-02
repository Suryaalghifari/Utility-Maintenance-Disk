# System Tools

CLI untuk melihat pemakaian disk, menemukan bloat, dan membersihkan cache secara
aman. Mendukung Linux/Ubuntu dan Windows.

## Pilih stack

| OS | Stack | Jalankan |
|---|---|---|
| Linux/Ubuntu | Bash matang (`scripts/`) | `disk-health` |
| Windows | Python lintas-OS (`disktools/`) | `disk-health --all` atau `python -m disktools disk-health --all` |

`disk-health`, `bloat-scan`, dan `junk-report` bersifat read-only. Cleaner selalu
meminta konfirmasi kecuali memakai `--yes`. Gunakan `--dry-run` untuk melihat
aksi tanpa menghapus data.

## Mulai cepat: Linux

```bash
./install.sh

# buka shell baru, lalu:
disk-health              # lihat pemakaian dan rekomendasi
system-clean --dry-run   # simulasi semua cleaner aman
system-clean             # jalankan dengan konfirmasi
```

`install.sh` menyalin command ke `~/bin` dan menambahkan path untuk fish, bash,
atau zsh.

## Mulai cepat: Windows

Syarat: Python 3.12+.

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Tutup dan buka kembali VS Code/Windows Terminal agar PATH baru terbaca. Untuk
memakai sesi PowerShell aktif:

```powershell
$env:Path = "$PWD\bin;$env:Path"
disk-health --all
system-clean --dry-run
system-clean
```

Tanpa instalasi:

```powershell
python -m disktools disk-health --all
```

Pilih drive dengan `--drive C[,D]`; gunakan `--all` untuk semua fixed drive.
Detail implementasi Windows: [docs/windows-plan.md](docs/windows-plan.md).

## Alur kerja

```bash
disk-health                 # 1. lihat area besar dan ruang recoverable
bloat-scan                  # 2. klasifikasikan cache, artifact, runtime, dan file besar
disk-inspect <path>         # 3. bedah folder tertentu
system-clean --dry-run      # 4. verifikasi rencana pembersihan
system-clean                # 5. bersihkan setelah konfirmasi
```

Contoh inspeksi:

```bash
disk-inspect ~/.local
disk-inspect ~/snap --depth 3
disk-inspect -i             # navigasi dan hapus terarah
disk-inspect dbeaver -i     # cari aplikasi lalu buka mode interaktif
```

## Memahami hasil

Ukuran dan keamanan dipisahkan. Folder merah berarti besar, bukan otomatis
sampah.

| Indikator ukuran | Nilai |
|---|---|
| Hijau | kurang dari 300 MB |
| Kuning | 300 MB sampai kurang dari 1 GB |
| Merah | minimal 1 GB |

Untuk disk: hijau di bawah 80%, kuning 80–89%, merah minimal 90%.

`bloat-scan` memakai klasifikasi berikut:

| Kelas | Arti | Tindakan |
|---|---|---|
| `SAFE CLEAN` | Cache/temp/log regenerable | Jalankan cleaner terkait |
| `PRUNE` | Artifact dapat dibuat ulang tetapi mungkin masih dipakai | Review lalu prune memakai package manager |
| `INSPECT` | Data, runtime aktif, atau file belum terbukti junk | Periksa; jangan hapus hanya karena besar |

Item `♻ aman hapus` dalam `disk-inspect` adalah cache/junk regenerable. Item tanpa
penanda dianggap data atau konfigurasi.

## Command Linux

### Pemeriksaan

| Command | Fungsi |
|---|---|
| `disk-health` | Dashboard pemakaian, recoverable space, dan rekomendasi |
| `bloat-scan [MIN_MB]` | Scan read-only dengan klasifikasi; file besar default minimal 200 MB |
| `disk-inspect [path\|app]` | Bedah folder; `-i` interaktif, `--depth N` mengatur kedalaman |
| `junk-report [DAYS] [MB]` | Daftar read-only file besar dan lama; default 90 hari/100 MB |

### Cleaner

| Command | Target |
|---|---|
| `chrome-clean` | Cache Chrome/Chromium/Brave/Edge/Vivaldi/Opera |
| `chrome-sw-clean` | Service Worker CacheStorage Chromium |
| `firefox-clean` | Cache Firefox native dan Snap |
| `chrome-ai-clean [--disable]` | Model AI browser; `--disable` mencegah unduh ulang via policy |
| `node-clean` | Cache npm, pnpm, pip, dan Composer |
| `trash-clean` | Trash home dan drive ter-mount |
| `journal-clean [SIZE]` | Vacuum journald; default sisakan 200 MB |
| `apt-clean` | Cache `.deb` dan paket orphan/kernel lama |
| `docker-clean [--all]` | Docker prune; `--all` lebih agresif |
| `snap-clean` | Revisi Snap disabled dan `refresh.retain=2` |
| `system-clean` | Jalankan seluruh cleaner aman berurutan |
| `update-cleaner` | Pull repo lalu instal ulang |

Tutup browser sebelum membersihkan cache. `chrome-ai-clean --disable`, apt,
journal, dan Snap dapat membutuhkan `sudo`.

## Command Windows

| Command | Fungsi |
|---|---|
| `disk-health` | Dashboard drive SSD/HDD, recoverable space, dan rekomendasi |
| `bloat-scan` | Scan read-only dengan klasifikasi `SAFE CLEAN`/`PRUNE`/`INSPECT` |
| `disk-inspect [path]` | Bedah folder; `-i` membuka mode interaktif |
| `system-clean` | Jalankan cleaner aman dengan satu konfirmasi |
| `temp-clean` | Temp user dan `C:\Windows\Temp` |
| `node-clean` | Cache npm dan pip |
| `chrome-clean` | Cache browser Chromium |
| `chrome-ai-clean` | Model AI on-device Chromium |
| `trash-clean` | Recycle Bin per drive |

## Flag

| Flag | Fungsi |
|---|---|
| `-n`, `--dry-run` | Tampilkan aksi tanpa menghapus |
| `-y`, `--yes` | Lewati konfirmasi |
| `--drive C[,D]` | Pilih drive Windows |
| `--all` | Pilih semua fixed drive Windows |
| `-i` | Mode interaktif `disk-inspect` |
| `NO_COLOR=1` | Matikan warna |

## Mode interaktif `disk-inspect -i`

| Input | Aksi |
|---|---|
| `<nomor>` | Masuk ke folder |
| `b`, `u`, `0`, atau Enter | Kembali |
| `d <nomor>` | Hapus item terpilih |
| `d 1 3 5` atau `d 2-6` | Hapus beberapa item |
| `d all` | Hapus semua item `♻` di folder aktif |
| `q` | Keluar |

Penghapusan menampilkan daftar dan total ukuran, lalu meminta satu konfirmasi.
Folder sensitif seperti `.ssh`, `.gnupg`, `.config`, `Windows`, dan
`$Recycle.Bin` dilindungi.

## Prinsip keamanan

- Ukuran menunjukkan prioritas, bukan keamanan penghapusan.
- Tidak ada penghapusan otomatis berdasarkan umur file.
- Cleaner hanya menyentuh target terukur dan regenerable.
- Tool/platform yang tidak tersedia dilewati dengan aman.
- Gunakan cleaner atau package-manager native; jangan hapus store/runtime secara
  massal.

## Pengembangan

```bash
npm run test
```

Test menjalankan unit test Python dan pemeriksaan sintaks seluruh script Bash.
