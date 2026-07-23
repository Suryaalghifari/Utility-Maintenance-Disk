"""Entry point: detect OS -> load matching backend -> dispatch command.

    python -m disktools [command] [options]

Commands:
    disk-health   (default)  read-only dashboard: drives + recoverable space
    bloat-scan               read-only: silent bloat (AI models/caches) + big files
    disk-inspect [path]      drill into a folder; -i = navigate + targeted delete
    system-clean             run all safe cleaners in sequence (one confirmation)
    temp-clean               hapus cache Temp (user + Windows)
    node-clean               hapus cache dev (npm/pip)
    chrome-clean             hapus cache browser Chromium-family
    chrome-ai-clean          hapus model AI on-device browser
    trash-clean              kosongkan Recycle Bin / Trash

Options:
    --drive C[,D]   act on specific drive(s)
    --all           act on every fixed drive
    -i, --interactive  disk-inspect: navigate + delete mode
    -y, --yes       skip prompts (non-interactive -> system drive)
    -n, --dry-run   show actions without executing (no delete)
    -h, --help      this help
"""
from __future__ import annotations

import os
import sys

from . import commands, core


def _load_backend():
    if core.IS_WINDOWS:
        from . import platform_windows as be
        return be
    if core.IS_LINUX:
        from . import platform_linux as be
        return be
    core.err(f"OS '{core.OS}' belum didukung (baru Windows & Linux).")
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0

    drive_arg = None
    want_all = assume_yes = dry_run = interactive = False
    positionals: list[str] = []
    unknown: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-y", "--yes"):
            assume_yes = True
        elif a in ("-n", "--dry-run"):
            dry_run = True
        elif a in ("-i", "--interactive"):
            interactive = True
        elif a == "--all":
            want_all = True
        elif a == "--drive":
            i += 1
            drive_arg = argv[i] if i < len(argv) else None
        elif a.startswith("--drive="):
            drive_arg = a.split("=", 1)[1]
        elif not a.startswith("-"):
            positionals.append(a)
        else:
            unknown.append(a)
        i += 1

    if unknown:
        core.warn(f"Opsi tak dikenal diabaikan: {' '.join(unknown)}")

    command = positionals[0] if positionals else "disk-health"
    path_arg = os.path.expanduser(positionals[1]) if len(positionals) > 1 else None

    backend = _load_backend()

    drives = backend.list_drives()
    if not drives:
        core.err("Tidak ada fixed drive terdeteksi.")
        return 1

    if command in ("disk-health", "health"):
        selected = core.pick_drives(drives, drive_arg, want_all, assume_yes)
        commands.disk_health(backend, drives, selected)
        return 0

    if command in ("bloat-scan", "bloat"):
        commands.bloat_scan(backend)
        return 0

    if command in ("disk-inspect", "inspect"):
        # path precedence: positional > --drive root > user home
        if path_arg:
            start = path_arg
        elif drive_arg:
            start = drive_arg.split(",")[0].strip().rstrip(":").upper() + ":\\"
        else:
            start = os.path.expanduser("~")
        commands.disk_inspect(backend, start, interactive=interactive,
                              assume_yes=assume_yes)
        return 0

    if command in ("system-clean", "clean-all"):
        selected = core.pick_drives(drives, drive_arg, want_all, assume_yes)
        commands.system_clean(backend, selected, dry_run=dry_run, assume_yes=assume_yes)
        return 0

    if command in ("trash-clean", "trash"):
        selected = core.pick_drives(drives, drive_arg, want_all, assume_yes)
        commands.trash_clean(backend, selected, dry_run=dry_run, assume_yes=assume_yes)
        return 0

    cleaners = {
        "temp-clean": dict(warn_browser=False),
        "node-clean": dict(warn_browser=False),
        "chrome-clean": dict(warn_browser=True),
        "chrome-ai-clean": dict(warn_browser=True),
    }
    if command in cleaners:
        selected = core.pick_drives(drives, drive_arg, want_all, assume_yes)
        commands.clean(backend, selected, command, dry_run=dry_run,
                       assume_yes=assume_yes, **cleaners[command])
        return 0

    core.err(f"Command '{command}' belum ada. Coba: disk-health, bloat-scan, "
             "disk-inspect, system-clean, temp-clean, node-clean, chrome-clean, "
             "chrome-ai-clean, trash-clean")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
