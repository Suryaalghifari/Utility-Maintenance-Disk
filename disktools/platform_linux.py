"""Linux backend: drive enumeration (SSD/HDD via /sys rotational) and read-only
measurement of cleanable areas. Parallel to platform_windows so core.py and the
commands stay OS-agnostic. Verify on a real Linux box — written to match the
existing bash suite's targets (~/.cache, ~/.npm, journal, Trash, apt).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .core import Area, Drive, dir_size, walk_big_files

# Pseudo/virtual filesystems that are not real fixed storage.
_SKIP_FSTYPES = {
    "tmpfs", "devtmpfs", "proc", "sysfs", "cgroup", "cgroup2", "overlay",
    "squashfs", "devpts", "mqueue", "debugfs", "tracefs", "securityfs",
    "pstore", "autofs", "bpf", "configfs", "fusectl", "hugetlbfs", "efivarfs",
    "ramfs", "binfmt_misc", "fuse.gvfsd-fuse", "fuse.portal",
}


def system_drive_id() -> str:
    return "/"


def _rotational(device: str) -> str:
    """Map a device node (/dev/sda1) to SSD/HDD via /sys/block/<base>/queue/rotational."""
    base = os.path.basename(device)
    if not base:
        return "Unknown"
    # Strip trailing partition digits: sda1 -> sda ; nvme0n1p2 -> nvme0n1
    disk = base
    if disk.startswith("nvme"):
        disk = disk.split("p")[0]
    else:
        disk = disk.rstrip("0123456789")
    rot = f"/sys/block/{disk}/queue/rotational"
    try:
        with open(rot) as f:
            return "HDD" if f.read().strip() == "1" else "SSD"
    except OSError:
        return "Unknown"


def list_drives() -> list[Drive]:
    seen: dict[str, Drive] = {}
    try:
        with open("/proc/mounts") as f:
            mounts = f.readlines()
    except OSError:
        return []
    for line in mounts:
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mount, fstype = parts[0], parts[1], parts[2]
        if fstype in _SKIP_FSTYPES or not device.startswith("/dev/"):
            continue
        if mount in seen:
            continue
        try:
            u = shutil.disk_usage(mount)
        except OSError:
            continue
        seen[mount] = Drive(
            id=mount, label="", media=_rotational(device),
            size=u.total, free=u.free, is_system=(mount == "/"),
        )
    drives = list(seen.values())
    drives.sort(key=lambda d: (not d.is_system, -d.size))
    return drives


def browser_running() -> bool:
    """True if any Chromium-family browser process is alive."""
    try:
        r = subprocess.run(
            ["pgrep", "-f", "chrome|chromium|brave|msedge|vivaldi|opera"],
            capture_output=True,
        )
        return r.returncode == 0
    except (OSError, FileNotFoundError):
        return False


def _on_mount(path: str, mount: str) -> bool:
    """True if `path` resolves onto the filesystem mounted at `mount`."""
    try:
        return os.stat(path).st_dev == os.stat(mount).st_dev
    except OSError:
        return False


def cleanable_areas(drive: Drive) -> list[Area]:
    home = os.path.expanduser("~")
    uid = os.getuid() if hasattr(os, "getuid") else 0

    if drive.is_system:
        candidates = [
            Area("Browser cache", [
                os.path.join(home, ".cache", "google-chrome"),
                os.path.join(home, ".cache", "chromium"),
                os.path.join(home, ".cache", "BraveSoftware"),
            ], recommend="chrome-clean"),
            Area("Dev caches (npm/pip/pnpm)", [
                os.path.join(home, ".npm", "_cacache"),
                os.path.join(home, ".cache", "pip"),
                os.path.join(home, ".cache", "pnpm"),
            ], recommend="node-clean"),
            Area("Trash", [os.path.join(home, ".local", "share", "Trash")],
                 recommend="trash-clean"),
        ]
    else:
        # A data mount: the standard reclaimable thing is its own per-user Trash.
        candidates = [
            Area("Trash (drive ini)",
                 [os.path.join(drive.id, f".Trash-{uid}")],
                 recommend="trash-clean"),
        ]

    areas: list[Area] = []
    for a in candidates:
        a.existing = [p for p in a.paths if p and os.path.exists(p)
                      and _on_mount(p, drive.id)]
        if not a.existing:
            continue
        a.bytes = sum(dir_size(p) for p in a.existing)
        if a.bytes > 0:
            areas.append(a)
    areas.sort(key=lambda a: -a.bytes)
    return areas


# --- bloat-scan (read-only) --------------------------------------------------
def _pnpm_store_path() -> str:
    """Ask pnpm for active store. Empty when pnpm is unavailable."""
    try:
        result = subprocess.run(
            ["pnpm", "store", "path"], capture_output=True, text=True, timeout=5,
        )
        return os.path.realpath(result.stdout.strip()) if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _node_modules_candidates(home: str) -> list[str]:
    """Find project node_modules without descending into hidden/runtime trees."""
    found: list[str] = []
    skip = {"snap", "node_modules"}
    for root, dirs, _ in os.walk(home):
        if "node_modules" in dirs:
            found.append(os.path.join(root, "node_modules"))
        # Hidden top-level trees usually hold active tool/runtime state, not source trees.
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        if len(Path(root).relative_to(home).parts) >= 4:
            dirs[:] = []
    return found


def _bloat_candidates() -> list[Area]:
    home = os.path.expanduser("~")
    active_store = _pnpm_store_path()
    stores_root = os.path.join(home, ".local", "share", "pnpm", "store")
    stores = []
    try:
        stores = [e.path for e in os.scandir(stores_root) if e.is_dir()]
    except OSError:
        pass

    areas = [
        Area("npm cache", [os.path.join(home, ".npm", "_cacache")],
             recommend="node-clean", action="SAFE CLEAN",
             note="alasan: package cache regenerable; bersihkan via npm cache clean"),
        Area("npx execution cache", [os.path.join(home, ".npm", "_npx")],
             action="PRUNE", note="alasan: sandbox paket npx regenerable; review versi lama"),
        Area("Firefox Snap cache", [os.path.join(home, "snap", "firefox", "common", ".cache")],
             action="SAFE CLEAN", note="alasan: cache browser regenerable; tutup Firefox dulu"),
        Area("HuggingFace cache", [os.path.join(home, ".cache", "huggingface")],
             action="PRUNE", note="alasan: model bisa diunduh ulang; bandwidth mahal"),
        Area("Ollama models", [os.path.join(home, ".ollama", "models")], safe=False,
             action="INSPECT", note="alasan: model runtime lokal aktif, bukan junk"),
        Area("Torch cache", [os.path.join(home, ".cache", "torch")], action="PRUNE",
             note="alasan: dependency dapat diunduh ulang; cek proyek aktif"),
        Area("VS Code extensions", [os.path.join(home, ".vscode", "extensions")], safe=False,
             action="INSPECT", note="alasan: extension runtime aktif, bukan cache"),
        Area("Neovim data", [os.path.join(home, ".local", "share", "nvim")], safe=False,
             action="INSPECT", note="alasan: plugin/runtime Neovim aktif, bukan junk"),
        Area("uv tool data", [os.path.join(home, ".local", "share", "uv")], safe=False,
             action="INSPECT", note="alasan: runtime/tool uv aktif; gunakan uv tool/cache command"),
        Area("Gradle caches", [os.path.join(home, ".gradle", "caches")], action="PRUNE",
             note="alasan: dependency build regenerable; gunakan gradle cleanup bila tersedia"),
    ]
    for store in stores:
        if not active_store:
            areas.append(Area("pnpm store", [store], safe=False, action="INSPECT",
                              note="alasan: status store aktif tidak diketahui; "
                                   "pnpm store path tidak tersedia"))
        elif os.path.realpath(store) == active_store:
            areas.append(Area("pnpm active store", [store], safe=False, action="INSPECT",
                              note="alasan: store aktif menurut pnpm store path, jangan hapus"))
        else:
            areas.append(Area("pnpm legacy store", [store], action="PRUNE",
                              note="alasan: bukan store aktif; review lalu pnpm store prune"))
    for path in _node_modules_candidates(home):
        areas.append(Area("project node_modules", [path], action="PRUNE",
                          note="alasan: artifact dependency regenerable; pastikan proyek tidak aktif"))
    return areas


def bloat_locations() -> list[Area]:
    areas: list[Area] = []
    for a in _bloat_candidates():
        a.existing = [p for p in a.paths if p and os.path.isdir(p)]
        if not a.existing:
            continue
        a.bytes = sum(dir_size(p) for p in a.existing)
        if a.bytes > 0:
            areas.append(a)
    areas.sort(key=lambda a: -a.bytes)
    return areas


def bloat_roots() -> list[str]:
    home = os.path.expanduser("~")
    return [
        os.path.join(home, ".cache"),
        os.path.join(home, ".ollama"),
        os.path.join(home, "Downloads"),
        os.path.join(home, ".local", "share"),
    ]


def big_files(threshold: int | None = None) -> list[tuple[int, str]]:
    from .core import BIG_FILE_THRESHOLD
    return walk_big_files(bloat_roots(), threshold or BIG_FILE_THRESHOLD)


def clean_native(area_key: str, paths: list[str]) -> int | None:
    """Use package-manager cleanup APIs. None means no native implementation."""
    if area_key != "node-clean":
        return None
    before = sum(dir_size(p) for p in paths)
    home = os.path.expanduser("~")
    commands = [
        (["npm", "cache", "clean", "--force"], "npm",
         os.path.join(home, ".npm", "_cacache")),
        (["pip3", "cache", "purge"], "pip3",
         os.path.join(home, ".cache", "pip")),
    ]
    ran = False
    normalized = {os.path.realpath(p) for p in paths}
    for argv, executable, owned_path in commands:
        if os.path.realpath(owned_path) in normalized and shutil.which(executable):
            subprocess.run(argv, check=False)
            ran = True
    if not ran:
        return None
    after = sum(dir_size(p) for p in paths)
    return max(before - after, 0)


def empty_trash(drive: Drive, dry_run: bool) -> tuple[int, int]:
    """Empty the Trash on `drive`. System drive → ~/.local/share/Trash; a data
    mount → its per-user .Trash-<uid>. Returns (before, freed)."""
    from .core import reclaim
    home = os.path.expanduser("~")
    uid = os.getuid() if hasattr(os, "getuid") else 0
    trash = (os.path.join(home, ".local", "share", "Trash") if drive.is_system
             else os.path.join(drive.id, f".Trash-{uid}"))
    if not os.path.isdir(trash):
        return 0, 0
    return reclaim([trash], dry_run)
