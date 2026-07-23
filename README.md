# System Tools

Utility maintenance disk untuk developer Linux/Ubuntu. Jaga disk supaya tidak
penuh: cek dengan `disk-health` (pelacak mendalam), lalu jalankan cleaner yang
direkomendasikannya. Portabel — jalan di mesin Ubuntu/Linux lain apa adanya
(tool yang tidak ada otomatis di-skip; browser Chrome/Chromium/Brave/Edge/Vivaldi
terdeteksi otomatis).

## Install

```bash
./install.sh
```

Meng-copy semua script ke `~/bin` dan memastikan `~/bin` ada di `PATH`
(fish/bash/zsh). Buka shell baru setelahnya. Di mesin lain: salin folder repo
ini, jalankan `./install.sh` — selesai.

## Alur pemakaian

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
| `u` | Naik satu level ke atas |
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

## Commands

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
