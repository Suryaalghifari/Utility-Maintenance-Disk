# install.ps1 — pasang disktools (Opsi A, Python) di Windows.
# Bikin shim per-command di .\bin lalu tambahkan ke PATH user, sehingga command
# bisa dipanggil langsung (disk-health, bloat-scan, …) tanpa `python -m disktools`.
#
# Pakai:  powershell -ExecutionPolicy Bypass -File .\install.ps1
[CmdletBinding()]
param(
    [switch]$NoPath   # bikin shim saja, jangan sentuh PATH
)

$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$bin  = Join-Path $repo 'bin'

# Command yang di-expose (harus sama dengan dispatcher di disktools\__main__.py).
$commands = @('disk-health', 'bloat-scan', 'disk-inspect', 'system-clean',
              'temp-clean', 'node-clean', 'chrome-clean', 'chrome-ai-clean',
              'trash-clean')

Write-Host "disktools installer" -ForegroundColor Cyan
Write-Host "  repo: $repo"

# --- 1. Python tersedia? -----------------------------------------------------
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "  x Python tidak ditemukan di PATH." -ForegroundColor Red
    Write-Host "    disktools butuh Python 3.12+. Pasang dari python.org atau 'winget install Python.Python.3.12'."
    exit 1
}
$ver = (& python --version) 2>&1
Write-Host "  python: $($py.Source)  ($ver)"

# --- 2. disktools importable dari repo? --------------------------------------
$env:PYTHONPATH = "$repo;$env:PYTHONPATH"
& python -c "import disktools; print('  disktools', disktools.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  x Gagal import disktools dari $repo" -ForegroundColor Red
    exit 1
}

# --- 3. Bikin shim .cmd ------------------------------------------------------
if (-not (Test-Path $bin)) { New-Item -ItemType Directory -Path $bin | Out-Null }

foreach ($cmd in $commands) {
    $shim = Join-Path $bin "$cmd.cmd"
    $body = @"
@echo off
setlocal
set "PYTHONPATH=$repo;%PYTHONPATH%"
python -m disktools $cmd %*
"@
    Set-Content -Path $shim -Value $body -Encoding ASCII
    Write-Host "  + $shim"
}

# Passthrough tunggal: `disktools <cmd> ...`
$passthru = Join-Path $bin 'disktools.cmd'
$body = @"
@echo off
setlocal
set "PYTHONPATH=$repo;%PYTHONPATH%"
python -m disktools %*
"@
Set-Content -Path $passthru -Value $body -Encoding ASCII
Write-Host "  + $passthru"

# --- 4. Tambah bin ke PATH user ---------------------------------------------
if ($NoPath) {
    Write-Host "  (-NoPath) PATH tidak diubah." -ForegroundColor Yellow
} else {
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $parts = @()
    if ($userPath) { $parts = $userPath -split ';' | Where-Object { $_ } }
    if ($parts -notcontains $bin) {
        $newPath = (@($bin) + $parts) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
        Write-Host "  + PATH user += $bin" -ForegroundColor Green
    } else {
        Write-Host "  = $bin sudah ada di PATH user"
    }
    # PENTING: SetEnvironmentVariable('User') tidak memperbarui terminal yang
    # sudah terbuka. Installer ini pun proses anak, jadi tak bisa meng-update PATH
    # sesi PARENT tempat kamu mengetik. Karena itu selalu ingatkan.
    Write-Host ""
    Write-Host "  Terminal yang SEKARANG terbuka belum melihat PATH baru." -ForegroundColor Yellow
    Write-Host "  -> Buka terminal baru, ATAU refresh sesi ini:" -ForegroundColor Yellow
    Write-Host "     `$env:Path = `"$bin;`$env:Path`""
}

Write-Host ""
Write-Host "Selesai. Command tersedia:" -ForegroundColor Green
foreach ($cmd in $commands) { Write-Host "  $cmd" }
Write-Host ""
Write-Host "Coba:  disk-health --all      |  bloat-scan      |  temp-clean --dry-run"
