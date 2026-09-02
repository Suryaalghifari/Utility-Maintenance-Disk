"""Windows backend: drive enumeration (with SSD/HDD media type) and read-only
measurement of cleanable areas. Rich disk facts come from PowerShell
(Get-Volume / Get-PhysicalDisk); sizes are measured in pure Python so nothing
here mutates the system.
"""
from __future__ import annotations

import json
import os
import subprocess

from .core import Area, Drive, dir_size, walk_big_files

_PS_LIST_DRIVES = r"""
$out = Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } | ForEach-Object {
    $dl = $_.DriveLetter
    $media = 'Unknown'
    try {
        $disk = Get-Partition -DriveLetter $dl -ErrorAction Stop | Get-Disk -ErrorAction Stop
        $pd = Get-PhysicalDisk | Where-Object { $_.DeviceId -eq $disk.Number }
        if ($pd -and $pd.MediaType) { $media = [string]$pd.MediaType }
    } catch {}
    [pscustomobject]@{
        Id    = "$dl`:"
        Label = [string]$_.FileSystemLabel
        Media = $media
        Size  = [int64]$_.Size
        Free  = [int64]$_.SizeRemaining
    }
}
ConvertTo-Json @($out) -Depth 3
"""


def _powershell(script: str) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True,
    )
    return proc.stdout


def system_drive_id() -> str:
    return (os.environ.get("SystemDrive") or "C:").upper()


def list_drives() -> list[Drive]:
    raw = _powershell(_PS_LIST_DRIVES).strip()
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):          # PS emits a bare object for a single row
        data = [data]
    sysid = system_drive_id().rstrip(":").upper()
    drives = [
        Drive(
            id=d["Id"], label=d.get("Label") or "", media=d.get("Media") or "Unknown",
            size=int(d.get("Size") or 0), free=int(d.get("Free") or 0),
            is_system=d["Id"].rstrip(":").upper() == sysid,
        )
        for d in data
    ]
    # System drive first, then biggest.
    drives.sort(key=lambda d: (not d.is_system, -d.size))
    return drives


# --- Read-only size measurement ----------------------------------------------
def browser_running() -> bool:
    """True if any Chromium-family browser process is alive (deleting its cache
    while running can corrupt the profile — callers warn, don't block)."""
    out = _powershell(
        "if (Get-Process chrome,msedge,brave,chromium,vivaldi,opera "
        "-ErrorAction SilentlyContinue) { 'yes' } else { 'no' }"
    ).strip()
    return out == "yes"


def _glob_profiles(base: str, sub: str) -> list[str]:
    """base\\*\\sub for every browser profile dir under base (User Data)."""
    out = []
    if not os.path.isdir(base):
        return out
    try:
        for name in os.listdir(base):
            p = os.path.join(base, name, sub)
            if os.path.isdir(p):
                out.append(p)
    except OSError:
        pass
    return out


def _drive_of(path: str) -> str:
    return os.path.splitdrive(os.path.abspath(path))[0].upper()


def cleanable_areas(drive: Drive) -> list[Area]:
    """Curated, bounded cleanable buckets that physically live on `drive`.
    Read-only here: we only measure. Deleting is a separate cleaner's job.
    """
    local = os.environ.get("LOCALAPPDATA", "")
    temp = os.environ.get("TEMP", "")
    dl = drive.id.rstrip(":").upper() + ":"

    chrome_ud = os.path.join(local, "Google", "Chrome", "User Data")
    edge_ud = os.path.join(local, "Microsoft", "Edge", "User Data")
    brave_ud = os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data")

    browser_cache: list[str] = []
    browser_ai: list[str] = []
    for ud in (chrome_ud, edge_ud, brave_ud):
        for sub in ("Cache", "Code Cache", "GPUCache",
                    os.path.join("Service Worker", "CacheStorage")):
            browser_cache += _glob_profiles(ud, sub)
        for sub in ("OptGuideOnDeviceModel", "optimization_guide_model_store",
                    "screen_ai"):
            browser_ai += _glob_profiles(ud, sub)

    candidates: list[Area] = [
        Area("Temp (user)", [temp],
             recommend="temp-clean", note="aman: file sementara"),
        Area("Temp (Windows)", [r"C:\Windows\Temp"],
             recommend="temp-clean", admin=True),
        Area("Recycle Bin", [os.path.join(dl + "\\", "$Recycle.Bin")],
             recommend="trash-clean"),
        Area("Browser cache", browser_cache, recommend="chrome-clean"),
        Area("Browser AI models", browser_ai, recommend="chrome-ai-clean",
             note="re-download kalau fitur AI dipakai lagi"),
        Area("Dev caches (npm/pip)", [
            os.path.join(local, "npm-cache"),
            os.path.join(local, "pip", "Cache"),
        ], recommend="node-clean"),
        Area("Windows Update cache",
             [r"C:\Windows\SoftwareDistribution\Download"],
             recommend="winupdate-clean", admin=True, note="stop wuauserv dulu"),
        Area("Thumbnail cache",
             [os.path.join(local, "Microsoft", "Windows", "Explorer")],
             recommend="thumb-clean"),
    ]

    areas: list[Area] = []
    for a in candidates:
        # Keep only paths that (a) exist and (b) sit on the selected drive.
        a.existing = [p for p in a.paths if p and os.path.exists(p)
                      and _drive_of(p) == dl]
        if not a.existing:
            continue
        a.bytes = sum(dir_size(p) for p in a.existing)
        if a.bytes > 0:
            areas.append(a)
    areas.sort(key=lambda a: -a.bytes)
    return areas


# --- bloat-scan (read-only): silent bloat locations + big-file sweep ----------
def _bloat_candidates() -> list[Area]:
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    home = os.environ.get("USERPROFILE", "")
    chrome_ud = os.path.join(local, "Google", "Chrome", "User Data")

    ai_models: list[str] = []
    for sub in ("OptGuideOnDeviceModel", "optimization_guide_model_store", "screen_ai"):
        ai_models += _glob_profiles(chrome_ud, sub)

    return [
        Area("Chrome AI on-device models", ai_models,
             recommend="chrome-ai-clean", action="PRUNE",
             note="re-download bila fitur AI dipakai"),
        Area("HuggingFace cache", [os.path.join(home, ".cache", "huggingface")],
             recommend="(hapus manual)", action="PRUNE",
             note="re-download model saat dipakai"),
        Area("Ollama models", [os.path.join(home, ".ollama", "models")],
             safe=False, note="model LLM lokal — dependency, bukan sampah"),
        Area("Torch cache", [os.path.join(home, ".cache", "torch")],
             action="PRUNE", note="re-download bila dipakai"),
        Area("VS Code extensions", [os.path.join(home, ".vscode", "extensions")],
             safe=False, note="extension aktif — dependency"),
        Area("VSIX cache", [os.path.join(roaming, "Code", "CachedExtensionVSIXs")],
             recommend="(hapus manual)", action="PRUNE"),
        Area("Electron apps (per-user)", [os.path.join(local, "Programs")],
             safe=False, note="aplikasi terpasang (VS Code/Discord/…) — bukan sampah"),
        Area("Gradle caches", [os.path.join(home, ".gradle", "caches")],
             action="PRUNE", note="re-download dependency saat build"),
        Area(".nuget packages", [os.path.join(home, ".nuget", "packages")],
             safe=False, note="dependency .NET"),
        Area("Docker data", [os.path.join(local, "Docker")],
             safe=False, note="pakai docker-clean, jangan hapus manual"),
    ]


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
    """Directories the big-file (model/weight) sweep should walk. Bounded to
    likely-bloat trees so the scan stays fast instead of walking whole drives."""
    local = os.environ.get("LOCALAPPDATA", "")
    home = os.environ.get("USERPROFILE", "")
    return [
        os.path.join(home, ".cache"),
        os.path.join(home, ".ollama"),
        os.path.join(home, "Downloads"),
        os.path.join(local, "Google", "Chrome", "User Data"),
        os.path.join(home, "AppData", "Local", "Programs"),
    ]


def big_files(threshold: int | None = None) -> list[tuple[int, str]]:
    from .core import BIG_FILE_THRESHOLD
    return walk_big_files(bloat_roots(), threshold or BIG_FILE_THRESHOLD)


def empty_trash(drive: Drive, dry_run: bool) -> tuple[int, int]:
    """Empty the Recycle Bin on `drive` via Clear-RecycleBin (the sanctioned API —
    deleting $Recycle.Bin\\<SID> by hand hits ACL/ownership issues). Returns
    (before, freed)."""
    letter = drive.id.rstrip(":").upper()
    rb = os.path.join(letter + ":\\", "$Recycle.Bin")
    before = dir_size(rb) if os.path.isdir(rb) else 0
    if dry_run or before == 0:
        return before, before
    _powershell(
        f"Clear-RecycleBin -DriveLetter {letter} -Force -ErrorAction SilentlyContinue"
    )
    after = dir_size(rb) if os.path.isdir(rb) else 0
    return before, max(before - after, 0)
