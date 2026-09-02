"""Commands (OS-agnostic presentation). Each command takes the active platform
backend + resolved options and renders. Backends supply raw numbers; commands
never branch on OS themselves.
"""
from __future__ import annotations

import os
import sys

from . import core
from .core import (Drive, human, size_dot, C_CYAN, C_DIM, C_RESET, C_BOLD,
                  C_GREEN, C_YELLOW)


def disk_health(backend, drives: list[Drive], selected: list[Drive]) -> None:
    core.title("Disk Health")
    core.info(f"OS terdeteksi: {core.OS}  ·  backend: {backend.__name__.split('.')[-1]}")
    core.hr()

    core.title(f"Drive terpasang ({len(drives)})")
    sel_ids = {d.id for d in selected}
    for d in drives:
        core.print_drive_row(d, marker="▶" if d.id in sel_ids else " ")

    for d in selected:
        core.hr()
        core.title(f"Recoverable di {d.id} {d.media_badge()}"
                   + (f'  "{d.label}"' if d.label else ""))
        areas = backend.cleanable_areas(d)
        if not areas:
            core.ok("Tidak ada cache/junk terukur di drive ini.")
            if not d.is_system:
                core.info("Drive data: pakai junk-report/bloat-scan (read-only) "
                          "untuk file besar.")
            continue

        recoverable = 0
        recs: list[tuple[str, str]] = []
        for a in areas:
            recoverable += a.bytes
            admin = f" {C_DIM}(admin){C_RESET}" if a.admin else ""
            note = f"  {C_DIM}{a.note}{C_RESET}" if a.note else ""
            print(f"  {size_dot(a.bytes)} {a.name:<22} {human(a.bytes):>10}{admin}{note}")
            if a.recommend and a.bytes >= core.SIZE_YELLOW:
                recs.append((a.recommend, f"{a.name} = {human(a.bytes)}"))

        print(f"\n  {C_BOLD}≈ {human(recoverable)}{C_RESET} bisa dibebaskan di {d.id}")
        if recs:
            core.title("Rekomendasi")
            for cmd, why in recs:
                print(f"  {C_CYAN}→ {cmd:<18}{C_RESET} {C_DIM}{why}{C_RESET}")
    print()


def _gather(backend, selected: list[Drive], area_key: str) -> list:
    """Every measured cleanable Area whose `recommend` == area_key, across drives."""
    out = []
    for d in selected:
        for a in backend.cleanable_areas(d):
            if a.recommend == area_key:
                out.append(a)
    return out


def _print_areas(matches: list, show_paths: bool = True) -> int:
    """Render areas with size dots; return their total bytes."""
    total = 0
    for a in matches:
        total += a.bytes
        admin = f" {C_DIM}(admin){C_RESET}" if a.admin else ""
        note = f"  {C_DIM}{a.note}{C_RESET}" if a.note else ""
        print(f"  {size_dot(a.bytes)} {a.name:<22} {human(a.bytes):>10}{admin}{note}")
        if show_paths:
            for p in a.existing:
                print(f"      {C_DIM}{p}{C_RESET}")
    return total


def clean(backend, selected: list[Drive], area_key: str, *, dry_run: bool,
          assume_yes: bool, warn_browser: bool = False) -> None:
    """Generic cleaner: reclaim every measured area whose `recommend` == area_key
    across the selected drives. Honors --dry-run and confirmation, reports freed.
    """
    label = {"temp-clean": "Temp", "chrome-clean": "Browser cache",
             "chrome-ai-clean": "Browser AI models",
             "node-clean": "Dev caches"}.get(area_key, area_key)
    core.title(f"{area_key}" + ("  (dry-run)" if dry_run else ""))

    matches = _gather(backend, selected, area_key)
    if not matches:
        core.ok(f"Tidak ada {label} untuk dibersihkan di drive terpilih "
                f"({', '.join(d.id for d in selected)}).")
        return

    if warn_browser and getattr(backend, "browser_running", lambda: False)():
        core.warn("Browser sedang jalan — tutup dulu agar cache bersih & profil aman.")

    total = _print_areas(matches)

    if dry_run:
        print(f"\n  {C_DIM}[dry-run]{C_RESET} akan membebaskan ≈ "
              f"{C_BOLD}{human(total)}{C_RESET} — tidak ada yang dihapus.")
        return

    if not core.confirm(f"Hapus ≈ {human(total)} di atas?", assume_yes):
        core.info("Dibatalkan — tidak ada yang dihapus.")
        return

    native = getattr(backend, "clean_native", None)
    native_freed = native(area_key, [p for a in matches for p in a.existing]) if native else None
    if native_freed is not None:
        core.ok(f"Dibebaskan {C_BOLD}{human(native_freed)}{C_RESET} via native command.")
        print()
        return

    freed_total = 0
    for a in matches:
        _, freed = core.reclaim(a.existing, dry_run=False)
        freed_total += freed
    core.ok(f"Dibebaskan {C_BOLD}{human(freed_total)}{C_RESET}.")
    print()


def trash_clean(backend, selected: list[Drive], *, dry_run: bool,
                assume_yes: bool) -> None:
    """Empty the Recycle Bin / Trash on each selected drive."""
    core.title("trash-clean" + ("  (dry-run)" if dry_run else ""))
    sizes = [(d, backend.empty_trash(d, dry_run=True)[0]) for d in selected]
    sizes = [(d, b) for d, b in sizes if b > 0]
    if not sizes:
        core.ok("Recycle Bin / Trash sudah kosong di drive terpilih.")
        return
    total = 0
    for d, b in sizes:
        total += b
        print(f"  {size_dot(b)} {d.id:<6} {human(b):>10}")
    if dry_run:
        print(f"\n  {C_DIM}[dry-run]{C_RESET} akan membebaskan ≈ "
              f"{C_BOLD}{human(total)}{C_RESET}.")
        return
    if not core.confirm(f"Kosongkan Recycle Bin ({human(total)})?", assume_yes):
        core.info("Dibatalkan.")
        return
    freed = sum(backend.empty_trash(d, dry_run=False)[1] for d, _ in sizes)
    core.ok(f"Dibebaskan {C_BOLD}{human(freed)}{C_RESET}.")
    print()


# Safe, regenerable cleaners run by system-clean (browser AI models excluded —
# they re-download and cost bandwidth, so stay an explicit opt-in like on Linux).
_SAFE_STEPS = ["temp-clean", "node-clean", "chrome-clean"]


def system_clean(backend, selected: list[Drive], *, dry_run: bool,
                 assume_yes: bool) -> None:
    """Run every safe cleaner in sequence: measure all, one confirmation, then
    reclaim, reporting the combined space freed."""
    core.title("system-clean" + ("  (dry-run)" if dry_run else ""))
    core.info("Cleaner aman & regenerable: " + ", ".join(_SAFE_STEPS) + ", trash-clean")

    if getattr(backend, "browser_running", lambda: False)():
        core.warn("Browser sedang jalan — tutup dulu agar cache browser bersih total.")

    step_areas = {key: _gather(backend, selected, key) for key in _SAFE_STEPS}
    trash = [(d, backend.empty_trash(d, dry_run=True)[0]) for d in selected]
    trash = [(d, b) for d, b in trash if b > 0]

    grand = 0
    for key in _SAFE_STEPS:
        matches = step_areas[key]
        if not matches:
            continue
        core.title(f"· {key}")
        grand += _print_areas(matches, show_paths=False)
    if trash:
        core.title("· trash-clean")
        for d, b in trash:
            grand += b
            print(f"  {size_dot(b)} {d.id:<6} {human(b):>10}")

    if grand == 0:
        core.ok("Tidak ada yang bisa dibersihkan — disk sudah bersih.")
        return

    print(f"\n  {C_BOLD}Total kandidat ≈ {human(grand)}{C_RESET}")
    if dry_run:
        print(f"  {C_DIM}[dry-run]{C_RESET} tidak ada yang dihapus.")
        return
    if not core.confirm(f"Jalankan semua cleaner di atas ({human(grand)})?", assume_yes):
        core.info("Dibatalkan — tidak ada yang dihapus.")
        return

    freed = 0
    native = getattr(backend, "clean_native", None)
    for key in _SAFE_STEPS:
        paths = [p for a in step_areas[key] for p in a.existing]
        native_freed = native(key, paths) if native and paths else None
        if native_freed is not None:
            freed += native_freed
            continue
        for a in step_areas[key]:
            _, f = core.reclaim(a.existing, dry_run=False)
            freed += f
    for d, _ in trash:
        freed += backend.empty_trash(d, dry_run=False)[1]
    core.ok(f"Selesai. Dibebaskan {C_BOLD}{human(freed)}{C_RESET}.")
    print()


def _parse_delete_spec(spec: str, items: list) -> list:
    """Turn 'all' / '2' / '1 3 5' / '2-6' into the referenced item dicts."""
    if spec == "all":
        return [i for i in items if i["junk"]]
    targets = []
    for tok in spec.replace(",", " ").split():
        if "-" in tok:
            a, b = tok.split("-", 1)
            if a.isdigit() and b.isdigit():
                targets += items[int(a) - 1:int(b)]
        elif tok.isdigit():
            n = int(tok)
            if 1 <= n <= len(items):
                targets.append(items[n - 1])
    return targets


def _render_listing(cur: str, items: list) -> int:
    core.title(f"disk-inspect: {cur}")
    if not items:
        core.ok("(kosong atau tak terbaca)")
        return 0
    safe_total = 0
    for idx, i in enumerate(items, 1):
        if i["junk"]:
            mark, safe_total = f"{C_GREEN}♻{C_RESET}", safe_total + i["size"]
        else:
            mark = " "
        kind = "📁" if i["is_dir"] else "  "
        name = (i["name"][:38] + "…") if len(i["name"]) > 39 else i["name"]
        print(f"  [{idx:>2}] {size_dot(i['size'])} {mark} {kind} {name:<40} "
              f"{human(i['size']):>10}")
    if safe_total > 0:
        print(f"  {C_DIM}♻ aman dihapus di sini: {human(safe_total)}{C_RESET}")
    return safe_total


def disk_inspect(backend, start: str, *, interactive: bool, assume_yes: bool) -> None:
    """Drill into a folder tree; -i adds navigation + targeted delete (like the
    Linux disk-inspect). Read-only unless you explicitly delete."""
    start = os.path.abspath(start)
    if not os.path.isdir(start):
        core.err(f"Bukan folder: {start}")
        return
    root, cur, stack = start, start, []

    if interactive and not (sys.stdin.isatty() and sys.stdout.isatty()):
        core.warn("Mode -i butuh terminal interaktif; menampilkan listing saja.")
        interactive = False

    while True:
        core.info("menghitung ukuran…")
        items = core.list_children(cur)
        _render_listing(cur, items)
        if not interactive:
            core.info("Tambah -i untuk navigasi & hapus terarah.")
            return

        try:
            ans = input(f"\n  {C_CYAN}[nomor]{C_RESET}=masuk  {C_CYAN}d N{C_RESET}=hapus  "
                        f"{C_CYAN}d all{C_RESET}=hapus ♻  {C_CYAN}b{C_RESET}=back  "
                        f"{C_CYAN}q{C_RESET}=keluar > ").strip()
        except EOFError:
            return

        if ans in ("q", "quit"):
            return
        if ans in ("", "b", "u", "0"):
            if stack:
                cur = stack.pop()
            elif cur != root:
                cur = os.path.dirname(cur)
            else:
                core.info("Sudah di folder awal.")
            continue

        if ans.startswith("d"):
            spec = ans[1:].strip().lower()
            if not spec:
                core.info("Contoh: d 2 · d 1 3 5 · d 2-6 · d all")
                continue
            targets = _parse_delete_spec(spec, items)
            targets = [t for t in targets if not core.is_sensitive(t["path"])]
            if not targets:
                core.info("Tidak ada item valid (atau semua terlindung).")
                continue
            total = sum(t["size"] for t in targets)
            core.title(f"Akan menghapus {len(targets)} item · {human(total)}")
            for t in targets:
                print(f"  {size_dot(t['size'])} {t['name']}  {human(t['size'])}")
            if not core.confirm("Hapus semua di atas?", assume_yes):
                core.info("Dibatalkan.")
                continue
            freed = sum(core.delete_item(t["path"]) for t in targets)
            core.ok(f"Dibebaskan {human(freed)}.")
            continue

        if ans.isdigit():
            n = int(ans)
            if 1 <= n <= len(items):
                it = items[n - 1]
                if it["is_dir"]:
                    stack.append(cur)
                    cur = it["path"]
                else:
                    core.info(f"'{it['name']}' adalah file (pakai d {n} untuk hapus).")
            else:
                core.warn("Nomor di luar daftar.")
            continue

        core.warn("Perintah tak dikenal. Pakai: nomor, d N, d all, b, q.")


def bloat_scan(backend, threshold: int | None = None) -> None:
    """READ-ONLY: hunt silent bloat — AI models, runtimes, caches — plus a sweep
    of oversized model/weight files. Deletes nothing."""
    core.title("Bloat Scan (read-only)")
    core.info(f"OS: {core.OS}  ·  ambang file besar: {human(core.BIG_FILE_THRESHOLD)}")

    core.hr()
    core.title("Lokasi bloat senyap")
    locs = backend.bloat_locations()
    if not locs:
        core.ok("Tidak ada lokasi bloat terukur.")
    else:
        safe_total = 0
        core.info("Threshold adaptif: medium ≥300 MB · large ≥1 GB · huge ≥5 GB")
        for a in locs:
            action = a.action or ("SAFE CLEAN" if a.safe else "INSPECT")
            tier = ("huge" if a.bytes >= 5 * core.GB else
                    "large" if a.bytes >= core.GB else
                    "medium" if a.bytes >= core.SIZE_YELLOW else "small")
            if action == "SAFE CLEAN":
                tag = f"{C_GREEN}{action}{C_RESET}"
                safe_total += a.bytes
            elif action == "PRUNE":
                tag = f"{C_YELLOW}{action}{C_RESET}"
            else:
                tag = f"{C_CYAN}{action}{C_RESET}"
            note = f"  {C_DIM}{a.note}{C_RESET}" if a.note else ""
            print(f"  {size_dot(a.bytes)} [{tier:<6}] {tag:<10} {a.name:<24} "
                  f"{human(a.bytes):>10}  {a.existing[0]}{note}")
        print(f"\n  {C_BOLD}≈ {human(safe_total)}{C_RESET} SAFE CLEAN; "
              f"PRUNE wajib review/native command; INSPECT bukan junk.")

    core.hr()
    core.title("File model/weight besar")
    bigs = backend.big_files(threshold)
    if not bigs:
        core.ok("Tidak ada file model besar di lokasi yang disapu.")
    else:
        for sz, path in bigs:
            print(f"  {size_dot(sz)} {human(sz):>10}  {path}")
        core.info(f"{len(bigs)} file — keputusan hapus di tanganmu (bukan auto).")
    print()
