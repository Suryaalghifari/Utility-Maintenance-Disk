"""OS-agnostic helpers: OS detection, formatting, status dots, the Drive model,
and the interactive drive picker. Nothing here touches a specific OS directly —
platform backends provide the raw numbers, core.py presents them.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
from dataclasses import dataclass, field

# --- OS detection ------------------------------------------------------------
# platform.system() is the reliable cross-runtime signal (works on PS 5.1 too,
# unlike $IsWindows which only exists on PowerShell 6+). Returns 'Windows',
# 'Linux', or 'Darwin'.
OS = platform.system()
IS_WINDOWS = OS == "Windows"
IS_LINUX = OS == "Linux"


# --- Colors: on only for an interactive TTY without NO_COLOR ------------------
def _use_color() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


if _use_color():
    C_RESET, C_BOLD, C_DIM = "\033[0m", "\033[1m", "\033[2m"
    C_RED, C_GREEN, C_YELLOW, C_CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[36m"
else:
    C_RESET = C_BOLD = C_DIM = C_RED = C_GREEN = C_YELLOW = C_CYAN = ""

# Size thresholds (bytes) — mirror the bash suite / claude.md.
MB = 1024 * 1024
GB = 1024 * MB
SIZE_YELLOW = 300 * MB
SIZE_RED = 1 * GB
# Disk-usage percent thresholds.
PCT_YELLOW = 80
PCT_RED = 90

# bloat-scan: model/weight files worth flagging, and the "big file" threshold.
BLOAT_EXTS = (".gguf", ".onnx", ".safetensors", ".bin", ".pt", ".pth",
              ".ckpt", ".h5", ".pb", ".tflite", ".mlmodel")
BIG_FILE_THRESHOLD = 200 * MB


def walk_big_files(roots: list[str], threshold: int = BIG_FILE_THRESHOLD,
                   exts: tuple[str, ...] = BLOAT_EXTS,
                   limit: int = 40) -> list[tuple[int, str]]:
    """Sweep `roots` for model/weight files >= threshold. Read-only. Skips
    symlinks/junctions and swallows access errors. Bounded to `limit` hits so a
    huge tree can't produce an unbounded list.
    """
    hits: list[tuple[int, str]] = []
    exts_l = tuple(e.lower() for e in exts)

    def _walk(path: str) -> None:
        if len(hits) >= limit:
            return
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if len(hits) >= limit:
                        return
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            _walk(entry.path)
                        elif entry.name.lower().endswith(exts_l):
                            sz = entry.stat(follow_symlinks=False).st_size
                            if sz >= threshold:
                                hits.append((sz, entry.path))
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
            return

    for r in roots:
        if r and os.path.isdir(r):
            _walk(r)
    hits.sort(key=lambda t: -t[0])
    return hits[:limit]


def dir_size(path: str) -> int:
    """Sum of regular-file sizes under `path`. Skips reparse points (junctions/
    symlinks) so we never loop or double-count, and swallows access errors.
    Shared by every platform backend — pure stdlib, read-only.
    """
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        total += dir_size(entry.path)
                    else:
                        total += entry.stat(follow_symlinks=False).st_size
                except (PermissionError, FileNotFoundError, OSError):
                    continue
    except (PermissionError, FileNotFoundError, NotADirectoryError, OSError):
        return total
    return total


def human(n: int | float) -> str:
    """Bytes -> '2.5 GB' (IEC, 1 decimal)."""
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024 or unit == "PB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} PB"


def size_dot(b: int, yellow: int = SIZE_YELLOW, red: int = SIZE_RED) -> str:
    return "🔴" if b >= red else "🟡" if b >= yellow else "🟢"


def pct_dot(p: float, yellow: int = PCT_YELLOW, red: int = PCT_RED) -> str:
    return "🔴" if p >= red else "🟡" if p >= yellow else "🟢"


def title(s: str) -> None:
    print(f"\n{C_BOLD}{s}{C_RESET}")


def hr() -> None:
    print(f"{C_DIM}──────────────────────────────{C_RESET}")


def info(s: str) -> None:
    print(f"{C_CYAN}•{C_RESET} {s}")


def ok(s: str) -> None:
    print(f"{C_GREEN}✓{C_RESET} {s}")


def warn(s: str) -> None:
    print(f"{C_YELLOW}!{C_RESET} {s}")


def err(s: str) -> None:
    print(f"{C_RED}✗{C_RESET} {s}", file=sys.stderr)


# --- Drive model -------------------------------------------------------------
@dataclass
class Drive:
    """A mounted, fixed volume the user might inspect or clean."""

    id: str           # 'C:' on Windows, mountpoint like '/' or '/home' on Linux
    label: str        # volume label (may be empty)
    media: str        # 'SSD' | 'HDD' | 'Unknown'
    size: int         # total bytes
    free: int         # free bytes
    is_system: bool   # True for the OS/system drive (auto-clean focus)

    @property
    def used(self) -> int:
        return max(self.size - self.free, 0)

    @property
    def used_pct(self) -> float:
        return round(100 * self.used / self.size) if self.size else 0.0

    def media_badge(self) -> str:
        icon = {"SSD": "⚡", "HDD": "💽"}.get(self.media, "❔")
        return f"{icon} {self.media}"


@dataclass
class Area:
    """A named bucket of paths (cache/junk/bloat) a backend measures or reclaims."""

    name: str
    paths: list[str]
    recommend: str = ""          # command/hint that reclaims it
    note: str = ""
    admin: bool = False          # needs Administrator/root
    safe: bool = True            # True = regenerable cache/junk; False = real dependency
    bytes: int = 0               # filled in by measurement
    existing: list[str] = field(default_factory=list)  # paths that actually exist here


def print_drive_row(d: Drive, marker: str = " ") -> None:
    sys_tag = f"{C_CYAN}[sistem]{C_RESET}" if d.is_system else ""
    label = f'"{d.label}"' if d.label else ""
    print(
        f"  {marker} {pct_dot(d.used_pct)} {C_BOLD}{d.id}{C_RESET} {label:<10} "
        f"{d.media_badge():<8} {human(d.size):>9} · {human(d.free):>9} free · "
        f"{d.used_pct:>3.0f}% used {sys_tag}"
    )


# --- Delete framework (shared by every cleaner) ------------------------------
def confirm(msg: str, assume_yes: bool) -> bool:
    """Ask before destructive work. Auto-yes with -y. On a non-interactive stream
    without -y, refuse (safe default) rather than hang."""
    if assume_yes:
        return True
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        warn("Non-interaktif: butuh -y untuk konfirmasi. Dilewati (tidak menghapus).")
        return False
    try:
        ans = input(f"{C_YELLOW}{msg}{C_RESET} [y/N] ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def _on_rm_error(func, path, exc):
    """rmtree handler: clear the read-only bit (common on Windows) and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def _delete_children(path: str) -> None:
    """Delete everything INSIDE `path` but keep `path` itself — safe for TEMP,
    Cache, and model dirs alike (never removes the parent the OS expects)."""
    try:
        entries = list(os.scandir(path))
    except OSError:
        return
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False):
                shutil.rmtree(e.path, onexc=_on_rm_error)
            else:
                try:
                    os.remove(e.path)
                except PermissionError:
                    os.chmod(e.path, stat.S_IWRITE)
                    os.remove(e.path)
        except OSError:
            continue


def reclaim(paths: list[str], dry_run: bool) -> tuple[int, int]:
    """Free `paths` by clearing their contents. Returns (measured_before, freed).
    Under dry_run nothing is deleted and freed is the estimate (== before).
    Freed is measured before/after so locked files that survive aren't counted.
    """
    before = sum(dir_size(p) for p in paths)
    if dry_run:
        return before, before
    for p in paths:
        _delete_children(p)
    after = sum(dir_size(p) for p in paths)
    return before, max(before - after, 0)


def delete_item(path: str) -> int:
    """Delete one item WHOLESALE (dir or file) and return bytes freed. Used by
    disk-inspect where the user targets a specific child."""
    def _sz(p):
        if os.path.isdir(p) and not os.path.islink(p):
            return dir_size(p)
        try:
            return os.path.getsize(p)
        except OSError:
            return 0
    before = _sz(path)
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, onexc=_on_rm_error)
        else:
            try:
                os.remove(path)
            except PermissionError:
                os.chmod(path, stat.S_IWRITE)
                os.remove(path)
    except OSError:
        pass
    return max(before - _sz(path), 0)


# --- Cache/junk classification + folder listing (for disk-inspect) -----------
_JUNK_NAMES = {
    "cache", ".cache", "caches", "code cache", "gpucache", "cachestorage",
    "scriptcache", "thumbnails", "thumbnailcache", "crashpad", "crash reports",
    "logs", "_logs", "_cacache", "tmp", "temp", ".tmp", ".trash",
}
_JUNK_PATH_SEGMENTS = (
    "/.cache/", "/cache/", "/cachestorage/", "/gpucache/", "/code cache/",
    "/shadercache/", "/service worker/",
)
# Names we never auto-delete even if big — user data / config / credentials.
_SENSITIVE_NAMES = {
    ".ssh", ".gnupg", ".config", ".aws", ".kube", ".docker", ".password-store",
    "windows", "system32", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information",
}


def is_cache_junk(path: str) -> bool:
    """True if `path` is regenerable cache/junk (safe to delete — it rebuilds)."""
    name = os.path.basename(path.rstrip("/\\")).lower()
    if name in _JUNK_NAMES:
        return True
    if "shadercache" in name or "shader_cache" in name or name.startswith("mesa_shader_cache"):
        return True
    low = path.replace("\\", "/").lower()
    return any(seg in low for seg in _JUNK_PATH_SEGMENTS)


def is_sensitive(path: str) -> bool:
    """True if `path` should never be offered for deletion (config/creds/system)."""
    return os.path.basename(path.rstrip("/\\")).lower() in _SENSITIVE_NAMES


def list_children(directory: str) -> list[dict]:
    """Immediate children of `directory` (dirs AND files) with sizes, biggest
    first. Read-only. Each item: {name, path, size, is_dir, junk}."""
    items: list[dict] = []
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return items
    for e in entries:
        try:
            is_dir = e.is_dir(follow_symlinks=False)
            size = dir_size(e.path) if is_dir else e.stat(follow_symlinks=False).st_size
        except OSError:
            continue
        items.append({
            "name": e.name, "path": e.path, "size": size,
            "is_dir": is_dir, "junk": is_cache_junk(e.path),
        })
    items.sort(key=lambda x: -x["size"])
    return items


# --- Interactive drive picker (per the chosen behavior: user picks any drive) -
def pick_drives(drives: list[Drive], drive_arg: str | None, want_all: bool,
                assume_yes: bool) -> list[Drive]:
    """Resolve which drives to act on.

    Precedence: explicit --drive / --all flags, else an interactive prompt on a
    TTY, else (non-interactive) default to the system drive so scripts/pipes
    never hang. Matches the 'user picks any drive' behavior.
    """
    if want_all:
        return drives
    if drive_arg:
        want = {x.strip().rstrip(":").upper() for x in drive_arg.split(",")}
        chosen = [d for d in drives if d.id.rstrip(":").upper() in want or d.id in want]
        if not chosen:
            err(f"Drive '{drive_arg}' tidak ditemukan. Ada: "
                + ", ".join(d.id for d in drives))
            sys.exit(2)
        return chosen

    if not (sys.stdin.isatty() and sys.stdout.isatty()) or assume_yes:
        # Non-interactive: default to the system drive (the auto-clean focus).
        return [d for d in drives if d.is_system] or drives

    title("Drive terpasang")
    for i, d in enumerate(drives, 1):
        print(f"  [{i}] ", end="")
        print_drive_row(d)
    print(f"\n  Pilih: nomor / huruf (mis. C), 'all', atau Enter = drive sistem")
    ans = input("  > ").strip()
    if not ans:
        return [d for d in drives if d.is_system] or drives
    if ans.lower() == "all":
        return drives
    if ans.isdigit() and 1 <= int(ans) <= len(drives):
        return [drives[int(ans) - 1]]
    return pick_drives(drives, ans, False, assume_yes)
