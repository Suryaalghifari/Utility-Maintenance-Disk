# System Tools

Utility maintenance disk untuk developer. Jaga disk supaya tidak penuh: cek
dengan `disk-health`, lalu jalankan cleaner yang direkomendasikannya.

Ada **dua stack** dengan konsep sama:

| Stack | OS | Bahasa | Cara panggil |
|-------|----|--------|--------------|
| **`scripts/`** (asli) | Linux/Ubuntu | bash | `disk-health`, `system-clean`, … |
| **`disktools/`** (baru) | **Windows** (& Linux) | Python | `python -m disktools <cmd>` atau shim `disk-health` |

`disktools/` **auto-deteksi OS** saat dijalankan (`platform.system()`) dan pilih
backend yang sesuai. Di bawah "[Windows](#windows-disktools--python-auto-deteksi-os)".

## Install (Linux)

```bash
./install.sh
```

Meng-copy semua script ke `~/bin` dan memastikan `~/bin` ada di `PATH`
(fish/bash/zsh). Buka shell baru setelahnya. Di mesin lain: salin folder repo
ini, jalankan `./install.sh` — selesai.

## Windows (`disktools` — Python, auto-deteksi OS)

**Syarat:** Python 3.12+ terpasang (cek `python --version`).

### Cara menjalankan (langkah demi langkah)

**Langkah 1 — Install (sekali saja).** Dari folder repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Ini membuat shim tiap command di `.\bin` dan menambahkannya ke PATH user.
(Pakai `-NoPath` kalau tak mau menyentuh PATH — command tetap jalan lewat
`python -m disktools`.)

**Langkah 2 — Buka terminal BARU.** ⚠️ Penting: PATH baru **tidak** terbaca oleh
terminal yang sudah terbuka. Kalau kamu pakai **VS Code / Windows Terminal**,
tab baru pun belum cukup — **tutup total aplikasinya lalu buka lagi**, atau
refresh sesi ini tanpa buka terminal baru:

```powershell
$env:Path = "$PWD\bin;$env:Path"
```

**Langkah 3 — Cek terpasang.**

```powershell
disk-health --all      # kalau tabel drive muncul → sukses
```

Kalau muncul `disk-health : The term ... is not recognized`, itu **PATH belum
ke-refresh** — ulangi Langkah 2 (bukan error program).

**Langkah 4 — Pakai.** Alur yang disarankan: **lihat → intip → jalankan.**

```powershell
disk-health --all            # 1. LIHAT: semua drive (SSD/HDD) + apa yang bisa dibebaskan
system-clean --dry-run       # 2. INTIP: semua cleaner aman sekaligus (tak menghapus)
system-clean -y              # 3. JALANKAN: bersihkan + lapor total ruang bebas

# read-only / eksplorasi
bloat-scan                   # buru bloat senyap: model AI/cache + file model besar
disk-inspect -i              # selami folder + hapus terarah (default: folder home)

# cleaner satuan (semua dukung --dry-run dulu, dan minta konfirmasi)
temp-clean -y                # cache Temp
node-clean -y                # cache dev (npm/pip)
chrome-clean                 # cache browser (tutup browser dulu)
chrome-ai-clean              # model AI on-device browser
trash-clean --all -y         # kosongkan Recycle Bin semua drive
```

> **Tanpa install** juga bisa — panggil apa pun via `python -m disktools <command>`,
> mis. `python -m disktools disk-health --all`.

**Aturan aman:** cleaner **tidak akan menghapus** tanpa konfirmasi. Di terminal
biasa muncul `[y/N]`; kalau dijalankan non-interaktif (pipe/script) tanpa `-y`,
ia **menolak** dan tak menghapus apa pun. Selalu boleh `--dry-run` dulu.

**Pilih penyimpanan (Target: auto-detect drive).** Semua fixed drive dienumerasi
+ ditandai ⚡SSD / 💽HDD dan drive sistem `[sistem]`. Pilih via `--drive C[,D]`,
`--all`, atau prompt interaktif. Non-interaktif tanpa flag → default drive sistem.

**Command Windows saat ini** (bertahap; sisanya menyusul):

| Command | Fungsi | Hapus? |
|---------|--------|:---:|
| `disk-health` | Dashboard drive (SSD/HDD) + recoverable per-drive + rekomendasi | — (read-only) |
| `bloat-scan` | Buru bloat senyap (model AI/runtime/cache) + sapu file model besar | — (read-only) |
| `disk-inspect [path]` | Selami folder (♻ marker); `-i` = navigasi + hapus terarah | opsional (`-i`) |
| `system-clean` | Jalankan semua cleaner aman berurutan (1 konfirmasi) | ✔ |
| `temp-clean` | Cache Temp user + `C:\Windows\Temp` (admin) | ✔ |
| `node-clean` | Cache dev (`npm-cache`, `pip\Cache`) | ✔ |
| `chrome-clean` | Cache browser Chromium (Chrome/Edge/Brave) | ✔ |
| `chrome-ai-clean` | Model AI on-device browser (`OptGuideOnDeviceModel`, dll) | ✔ |
| `trash-clean` | Kosongkan Recycle Bin (`Clear-RecycleBin`) per drive | ✔ |

**Flag:** `--drive C[,D]` / `--all` (pilih drive) · `-n`/`--dry-run` (intip) ·
`-y`/`--yes` (skip konfirmasi) · `-i` (disk-inspect interaktif) · `NO_COLOR=1`.

### Mode interaktif `disk-inspect -i`

| Ketik | Aksi |
|-------|------|
| `<nomor>` | Masuk ke folder itu |
| `b` | Back — folder sebelumnya (juga: `u`, `0`, Enter) |
| `d <nomor>` | Hapus 1 item (mis. `d 2`) |
| `d 1 3 5` / `d 2-6` | Hapus beberapa / rentang |
| `d all` | Hapus **semua item `♻`** (cache/junk) di folder itu |
| `q` | Keluar |

Item `♻` = cache/junk regenerable (aman). Folder sensitif (`.ssh`, `.config`,
`Windows`, `$Recycle.Bin`, …) otomatis dilindungi dari penghapusan.

> Backend Linux `disktools` sudah ditulis tetapi **belum diverifikasi di mesin
> Linux** — untuk Linux, pakai stack bash `scripts/` yang matang. Detail rencana &
> status: [docs/windows-plan.md](docs/windows-plan.md).

## Alur pemakaian (Linux / bash)

```bash
# 1. LIHAT — dashboard mendalam: ke mana disk pergi, per aplikasi + rekomendasi
disk-health

# 2. BERSIHKAN — jalankan command yang muncul di bagian "Recommended",
#    atau semua cleaner aman sekaligus:
system-clean

# 3. SELAM MANUAL (opsional) — telusuri sendiri, putuskan hapus atau tidak
disk-inspect               # TANPA argumen → jelajah SEMUA folder $HOME interaktif
disk-inspect dbeaver       # cari & bedah data aplikasi tertentu
disk-inspect dbeaver -i    # mode interaktif untuk app: navigasi + hapus terarah

# 4. BURU BLOAT SENYAP (opsional) — model AI/runtime/cache yang numpuk diam-diam
bloat-scan                 # read-only; lihat apa yang tumbuh tanpa Anda sadari
chrome-ai-clean --disable  # hapus model AI Chrome (~4GB) + setop unduh ulang

# 5. SAMPAH LAMA (opsional) — tampilkan file besar/lama untuk Anda review sendiri
junk-report                # read-only, tidak menghapus apa pun
```

`disk-health` sekarang membedah tiap area: `$HOME`, per-browser (cache /
service worker / profil + **komponen & model AI internal** yang sering diunduh
diam-diam, mis. model on-device Chrome ~4 GB), dev-cache
(npm/pnpm/pip/composer/playwright), journal, snap, docker, apt, trash — lalu
memetakan tiap temuan besar ke command yang tepat.

### Kontrol mode interaktif (`disk-inspect -i`)

| Ketik | Aksi |
|-------|------|
| `<nomor>` | Masuk ke folder itu (menyelam lebih dalam) |
| `b` | **Back** — kembali ke folder sebelumnya (juga: `u`, `0`, atau Enter) |
| `d <nomor>` | Hapus 1 item — mis. `d 2` (juga bisa `d2`) |
| `d 1 3 5` | Hapus beberapa item sekaligus |
| `d 2-6` | Hapus rentang nomor |
| `d all` | Hapus **semua item bertanda `♻`** di folder itu (data dilewati) |
| `d` | Tanya dulu mau hapus yang mana |
| `q` | Keluar |

Hapus (berapa pun jumlahnya) menampilkan daftar + total ukuran dan minta **satu**
konfirmasi `[y/N]`. Item di luar `$HOME` atau folder sensitif (`.config`, `.ssh`,
`.gnupg`, …) otomatis ditolak/dilewati. `d all` **hanya** menyentuh item `♻`
(cache/junk) — data/konfigurasi Anda aman.

## Arti warna

Titik warna di `disk-health` / `disk-inspect` menandakan seberapa besar sebuah
item — makin merah, makin layak diperiksa/dibersihkan.

**Untuk ukuran folder/file:**

| Warna | Ukuran | Arti |
|:---:|---|---|
| 🟢 | < 300 MB | Kecil — aman diabaikan |
| 🟡 | 300 MB – 1 GB | Sedang — pantau |
| 🔴 | ≥ 1 GB | Besar — kandidat utama dibersihkan |

**Untuk pemakaian disk (baris Root):**

| Warna | Terpakai | Arti |
|:---:|---|---|
| 🟢 | < 80% | Sehat |
| 🟡 | 80–89% | Mulai penuh |
| 🔴 | ≥ 90% | Kritis — segera bersihkan |

⚪ = tidak tersedia / tidak bisa diukur (mis. Docker saat daemon mati).

**Penanda aman-hapus (`disk-inspect`):**

Item bertanda **`♻ aman hapus`** adalah cache/junk yang regenerasi otomatis
(mis. `.cache`, `Code Cache`, `_cacache`, `thumbnails`, `logs`) — aman dibuang,
akan dibuat ulang saat dibutuhkan. Di mode interaktif, total yang aman dihapus di
folder aktif juga ditampilkan (`♻ aman dihapus di sini: …`). Item **tanpa** tanda
ini = data/konfigurasi Anda → hati-hati.

> Warna hanya soal **ukuran**, bukan "sampah atau bukan". Folder 🔴 besar bisa saja
> data penting (mis. `~/snap/firefox` = profil Anda). Pakai `disk-inspect` untuk
> memastikan isinya sebelum menghapus.

## Commands (Linux / bash)

### Lihat & lacak
| Command | Fungsi |
|---------|--------|
| `disk-health` | Dashboard mendalam: rincian pemakaian per aplikasi + total recoverable + rekomendasi |
| `disk-inspect [path\|app]` | **Tanpa argumen → jelajah semua `$HOME` interaktif.** Beri path/nama app untuk bedah spesifik. `-i` = navigasi + hapus terarah, `--depth N` = kedalaman |
| `bloat-scan [MIN_MB]` | **Read-only.** Buru "bloat senyap": model AI, komponen browser, cache installer, runtime besar + sapu file besar apa pun (default ≥ 200 MB) |
| `junk-report [DAYS] [MB]` | **Read-only.** Daftar folder terbesar + file besar-&-lama untuk Anda review (default 90 hari, 100 MB) |

### Cleaner (aman, selalu konfirmasi)
| Command | Membersihkan | Butuh sudo |
|---------|--------------|:---:|
| `chrome-clean` | Cache browser Chromium (Chrome/Chromium/Brave/Edge/Vivaldi) | — |
| `chrome-sw-clean` | Service Worker cache tiap profil browser | — |
| `chrome-ai-clean [--disable]` | Hapus model AI on-device Chrome (bisa **~4 GB**). `--disable` = pasang policy agar tak diunduh ulang | `--disable` saja |
| `node-clean` | Cache npm/pnpm/pip/composer | — |
| `trash-clean` | Isi Trash (home + drive ter-mount) | — |
| `journal-clean [SIZE]` | Vacuum journald (default sisakan `200M`) | ✔ |
| `apt-clean` | Cache `.deb` + autoremove paket orphan/kernel lama | ✔ |
| `docker-clean [--all]` | `docker system prune` (`--all` = + image & volume) | grup docker |
| `snap-clean` | Revisi snap lama + set `refresh.retain=2` | ✔ |

### Orkestrasi
| Command | Fungsi |
|---------|--------|
| `system-clean` | Jalankan semua cleaner aman berurutan |
| `update-cleaner` | Update dari repo lalu install ulang |

## Flag global

Berlaku untuk semua cleaner:

| Flag | Arti |
|------|------|
| `-y`, `--yes` | Lewati semua konfirmasi (non-interaktif) |
| `-n`, `--dry-run` | Tampilkan yang akan dijalankan, **tanpa** mengeksekusi |
| `NO_COLOR=1` | Matikan warna |

Contoh:

```bash
disk-health                 # lihat kondisi + rekomendasi
chrome-clean -n             # intip apa yang akan dihapus (aman)
node-clean                  # bebaskan cache npm/pnpm/pip/composer
journal-clean 100M          # sisakan hanya 100 MB log
system-clean -y             # bersih total tanpa tanya
docker-clean --all          # prune docker paling agresif
disk-inspect ~/.vscode      # bedah folder tertentu
disk-inspect slack -i       # selami data app, hapus manual sambil jalan
junk-report 30 200          # file >200MB & >30 hari tak disentuh
```

## Prinsip

- Cleaner **selalu konfirmasi** sebelum menghapus (kecuali `-y`), dan lapor
  ruang yang dibebaskan.
- **Tidak ada auto-hapus file berdasarkan umur.** File lama belum tentu sampah,
  jadi `junk-report` hanya *menampilkan* — keputusan hapus tetap di tangan Anda.
- Tool yang tidak terpasang (mis. `pnpm`, `snap`, `docker`) di-skip otomatis →
  aman dipindah ke mesin Ubuntu/Linux lain.
- Untuk browser, tutup dulu sebelum `chrome-clean` supaya cache tak langsung
  dibuat ulang.
- `update-cleaner` mencari repo di `~/Projects/system-tools`; ubah lewat env
  `SYSTEM_TOOLS_DIR` bila lokasinya beda.
