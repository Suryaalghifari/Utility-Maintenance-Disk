# System Tools — Rencana

Suite CLI untuk **maintenance disk** di Ubuntu (mesin developer). Tujuannya: disk
tidak pernah penuh. Alur pakai: jalankan `disk-health` → lihat yang 🔴/🟡 →
jalankan cleaner yang direkomendasikan (atau `system-clean` untuk semua).

## Struktur

```
system-tools/
├── install.sh          # copy scripts/* → ~/bin, set PATH (fish/bash/zsh)
├── README.md           # cara pakai
├── claude.md           # rencana ini
├── docs/
│   └── windows-plan.md # rencana dukungan Windows (auto-deteksi OS)
└── scripts/
    ├── _lib.sh         # helper (warna, ukuran, konfirmasi, dry-run,
    │                   #   deteksi browser Chromium-family, top_dir)
    ├── disk-health     # dashboard MENDALAM: bedah per-app + recoverable + rekomendasi
    ├── disk-inspect    # selami 1 folder/app; -i interaktif (navigasi + hapus terarah)
    ├── bloat-scan      # READ-ONLY: buru model AI/runtime/cache senyap + sapu file besar
    ├── junk-report     # READ-ONLY: daftar folder besar + file besar-&-lama
    ├── chrome-clean    # cache browser (chrome/chromium/brave/edge/vivaldi)
    ├── chrome-sw-clean # Service Worker CacheStorage tiap profil browser
    ├── chrome-ai-clean # hapus model AI on-device Chrome (~4GB); --disable setop unduh ulang
    ├── trash-clean     # kosongkan Trash (home + drive ter-mount)
    ├── apt-clean       # apt cache + autoremove orphan/kernel lama (sudo)
    ├── snap-clean      # buang revisi snap disabled + set retain=2
    ├── docker-clean    # docker system prune (opsi --all + volumes)
    ├── journal-clean   # vacuum journald (default sisakan 200M)
    ├── node-clean      # cache npm(~/.npm)/pnpm/pip/composer
    ├── system-clean    # jalankan semua cleaner aman berurutan
    └── update-cleaner  # git pull + install ulang
```

## Portabilitas (Ubuntu/Linux lain)

- Path `$HOME`-relative; tiap tool dijaga `command -v` → auto-skip bila absen.
- Browser dideteksi otomatis (chrome/chromium/brave/edge/vivaldi/opera).
- Butuh GNU coreutils + (opsional) systemd/apt/snap/docker — standar di Ubuntu.
- Pindah mesin: copy repo → `./install.sh`.

## Filosofi "sampah lama"

- Auto-hapus HANYA kategori aman & regenerable: cache, Trash, apt, journal.
- TIDAK auto-hapus file berdasarkan umur (lama ≠ sampah). `junk-report`
  read-only menampilkan kandidat; keputusan hapus di tangan user.

## Dukungan Windows (rencana)

Kode sekarang Linux-only (bash + GNU coreutils). Rencana lintas-platform dengan
**auto-deteksi OS** (Windows/Linux) — arsitektur (Python unified vs PowerShell
twin), pemetaan tiap command ke padanan Windows, dan cleaner khusus Windows —
ada di **[docs/windows-plan.md](docs/windows-plan.md)**. Status: rencana, belum
diimplementasi; verifikasi harus di mesin Windows.

## Konvensi bersama (`_lib.sh`)

- Semua script bash `#!/usr/bin/env bash` + `set -euo pipefail`.
- Source `_lib.sh` dari direktori script sendiri (jalan di repo maupun `~/bin`).
- Flag global: `-y/--yes` (skip konfirmasi), `-n/--dry-run` (tampilkan, jangan eksekusi).
- Warna otomatis mati kalau bukan TTY / `NO_COLOR`.
- Operasi destruktif → selalu `confirm` dulu (kecuali `-y`).
- Operasi butuh root ditandai jelas dan pakai `sudo` eksplisit.
- Setiap cleaner lapor **ruang yang dibebaskan** (before/after).

## Ambang status (disk-health)

| Item | 🟢 hijau | 🟡 kuning | 🔴 merah |
|------|---------|----------|---------|
| Root disk usage | < 80% | 80–89% | ≥ 90% |
| Ukuran cache/dir | < 300 MB | 300 MB–1 GB | ≥ 1 GB |

## Detail tiap cleaner (berdasarkan sistem nyata)

| Command | Target | Root? |
|---------|--------|-------|
| `chrome-clean` | `~/.cache/google-chrome` (~2.5 GB) | tidak |
| `chrome-sw-clean` | `~/.config/google-chrome/*/Service Worker` | tidak |
| `snap-clean` | revisi `disabled` dari `snap list --all` | ya (sudo) |
| `docker-clean` | `docker system prune` (butuh daemon) | grup docker |
| `journal-clean` | `journalctl --vacuum-size` (~526 MB) | ya (sudo) |
| `node-clean` | npm/pnpm/pip/composer cache | tidak |

Catatan lingkungan: shell = **fish**, `~/bin` sudah di PATH, `pnpm` belum
terpasang (script skip otomatis kalau tool tidak ada).

## Status

- [x] Probe sistem (path, tool terpasang, ukuran nyata)
- [x] `_lib.sh` (+ deteksi browser + `top_dir`)
- [x] `disk-health` MENDALAM (bedah per-app + rekomendasi per-temuan)
- [x] cleaner: chrome / chrome-sw / snap / docker / journal / node
- [x] cleaner baru: `trash-clean`, `apt-clean`
- [x] `junk-report` (read-only, sampah lama)
- [x] `disk-inspect` (selam per-folder/app + mode interaktif hapus terarah)
- [x] deteksi model AI internal browser di `disk-health` (mis. OptGuide 4GB)
- [x] `chrome-ai-clean` (hapus model + `--disable` policy anti unduh-ulang, portable)
- [x] `bloat-scan` (buru bloat senyap: model/runtime/cache + sapu file besar)
- [x] portabilitas: auto-deteksi browser, guard tool
- [x] `system-clean`, `update-cleaner`
- [x] `install.sh` fish-aware
- [x] Uji semua dengan `--dry-run`
- [x] Terpasang ke `~/bin`
- [ ] (opsional) cron/systemd-timer untuk `disk-health` mingguan
