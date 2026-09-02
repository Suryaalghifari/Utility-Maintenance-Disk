#!/usr/bin/env bash
# _lib.sh — shared helpers for system-tools. Sourced by the other commands,
# not executed directly.

# Colors: on only for an interactive TTY without NO_COLOR set.
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  C_RESET=$'\e[0m'; C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'
  C_RED=$'\e[31m'; C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_CYAN=$'\e[36m'
else
  C_RESET=; C_BOLD=; C_DIM=; C_RED=; C_GREEN=; C_YELLOW=; C_CYAN=
fi

# Behaviour flags (can be preset via env; parse_flags toggles them from argv).
ASSUME_YES="${ASSUME_YES:-0}"
DRY_RUN="${DRY_RUN:-0}"

# human BYTES -> "2.5GB"
human() { numfmt --to=iec --suffix=B --format='%.1f' "${1:-0}" 2>/dev/null || echo "${1:-0}B"; }

# path_bytes PATH... -> total bytes on disk (missing paths count as 0)
path_bytes() {
  local total=0 p sz
  for p in "$@"; do
    [[ -e "$p" ]] || continue
    sz=$(du -sb "$p" 2>/dev/null | awk 'NR==1{print $1}')
    total=$(( total + ${sz:-0} ))
  done
  echo "$total"
}

hr()    { printf '%s──────────────────────────────%s\n' "$C_DIM" "$C_RESET"; }
title() { printf '\n%s%s%s\n' "$C_BOLD" "$1" "$C_RESET"; }

# size_dot BYTES [yellow=300MB] [red=1GB]
size_dot() {
  local b="${1:-0}" y="${2:-314572800}" r="${3:-1073741824}"
  if   (( b >= r )); then printf '🔴'
  elif (( b >= y )); then printf '🟡'
  else                    printf '🟢'; fi
}

# adaptive_size BYTES -> tier used by bloat scans (small/large/huge).
adaptive_size() {
  local b="${1:-0}"
  if   (( b >= 5368709120 )); then printf 'huge'
  elif (( b >= 1073741824 )); then printf 'large'
  elif (( b >= 314572800 )); then printf 'medium'
  else                            printf 'small'; fi
}

# pct_dot PERCENT [yellow=80] [red=90]
pct_dot() {
  local p="${1:-0}" y="${2:-80}" r="${3:-90}"
  if   (( p >= r )); then printf '🔴'
  elif (( p >= y )); then printf '🟡'
  else                    printf '🟢'; fi
}

info() { printf '%s•%s %s\n' "$C_CYAN"   "$C_RESET" "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_GREEN"  "$C_RESET" "$*"; }
warn() { printf '%s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
err()  { printf '%s✗%s %s\n' "$C_RED"    "$C_RESET" "$*" >&2; }

# confirm "message" -> 0 if user agrees (auto-yes with -y / ASSUME_YES=1)
confirm() {
  [[ "$ASSUME_YES" == 1 ]] && return 0
  local ans
  printf '%s%s%s [y/N] ' "$C_YELLOW" "$1" "$C_RESET"
  read -r ans </dev/tty || return 1
  [[ "$ans" =~ ^[Yy]$ ]]
}

# run CMD... -> execute, or just print it under --dry-run
run() {
  if [[ "$DRY_RUN" == 1 ]]; then
    printf '%s[dry-run]%s %s\n' "$C_DIM" "$C_RESET" "$*"
  else
    "$@"
  fi
}

# parse_flags "$@" -> consumes -y/--yes and -n/--dry-run, leaves the rest in ARGS
parse_flags() {
  ARGS=()
  while (( $# )); do
    case "$1" in
      -y|--yes)     ASSUME_YES=1 ;;
      -n|--dry-run) DRY_RUN=1 ;;
      *)            ARGS+=("$1") ;;
    esac
    shift
  done
}

# --- Chromium-family browsers ------------------------------------------------
# "config-subpath|cache-subpath" under ~/.config and ~/.cache respectively.
_CHROMIUM_BROWSERS=(
  "google-chrome|google-chrome"
  "chromium|chromium"
  "chromium-browser|chromium-browser"
  "BraveSoftware/Brave-Browser|BraveSoftware/Brave-Browser"
  "microsoft-edge|microsoft-edge"
  "vivaldi|vivaldi"
  "opera|opera"
)

# browser_cache_dirs -> existing ~/.cache dirs for any installed Chromium browser
browser_cache_dirs() {
  local b d
  for b in "${_CHROMIUM_BROWSERS[@]}"; do
    d="$HOME/.cache/${b#*|}"
    [[ -d "$d" ]] && printf '%s\n' "$d"
  done
}

# browser_config_dirs -> existing ~/.config dirs for any installed Chromium browser
browser_config_dirs() {
  local b d
  for b in "${_CHROMIUM_BROWSERS[@]}"; do
    d="$HOME/.config/${b%|*}"
    [[ -d "$d" ]] && printf '%s\n' "$d"
  done
}

# browser_running -> 0 if any Chromium-family browser process is alive
browser_running() {
  pgrep -f 'chrome|chromium|brave|msedge|vivaldi|opera' >/dev/null 2>&1
}

# firefox_cache_dirs -> existing native and Snap Firefox cache roots.
firefox_cache_dirs() {
  local d
  for d in "$HOME/.cache/mozilla/firefox" "$HOME/snap/firefox/common/.cache"; do
    [[ -d "$d" ]] && printf '%s\n' "$d"
  done
}

firefox_running() {
  pgrep -x firefox >/dev/null 2>&1 || pgrep -x firefox-bin >/dev/null 2>&1
}

# Browser-profile subdirs that are reclaimable: GPU/shader caches, crx caches,
# and downloaded AI/ML components/models. Deleting loses NO personal data — the
# browser rebuilds caches, or re-downloads the model only if the feature is used.
_BROWSER_RECLAIMABLE_NAMES=(
  "GPUCache" "Code Cache" "GrShaderCache" "GraphiteDawnCache" "DawnCache"
  "DawnGraphiteCache" "DawnWebGPUCache" "ShaderCache" "component_crx_cache"
  "extensions_crx_cache" "OptGuideOnDeviceModel" "optimization_guide_model_store"
  "screen_ai"
)

# browser_reclaimable -> "bytes<TAB>path" for each reclaimable dir found under any
# installed Chromium-family browser config, biggest first.
browser_reclaimable() {
  local cfgs name expr=() d
  mapfile -t cfgs < <(browser_config_dirs)
  (( ${#cfgs[@]} )) || return 0
  for name in "${_BROWSER_RECLAIMABLE_NAMES[@]}"; do expr+=( -o -name "$name" ); done
  expr=("${expr[@]:1}")   # drop leading -o
  while IFS= read -r d; do
    [[ -d "$d" ]] || continue
    printf '%s\t%s\n' "$(du -sb "$d" 2>/dev/null | awk '{print $1}')" "$d"
  done < <(find "${cfgs[@]}" -maxdepth 3 -type d \( "${expr[@]}" \) -prune 2>/dev/null) | sort -rn
}

# top_dir DIR [N=6] -> "bytes<TAB>path" for the N biggest SUBDIRS of DIR
top_dir() {
  local dir="$1" n="${2:-6}"
  [[ -d "$dir" ]] || return 0
  du -x -b --max-depth=1 "$dir" 2>/dev/null \
    | awk -v self="$dir" '$2!=self' | sort -rn | head -n "$n"
}

# list_children DIR -> "bytes<TAB>path" for every immediate child (subdirs AND
# top-level files), biggest first. Complete breakdown of what a folder holds.
list_children() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  {
    du -x -b --max-depth=1 "$dir" 2>/dev/null | awk -v self="$dir" '$2!=self'
    find "$dir" -maxdepth 1 -type f -printf '%s\t%p\n' 2>/dev/null
  } | sort -rn
}

# is_cache_junk PATH -> 0 if the path is regenerable cache/junk (safe to delete):
# it just gets rebuilt on next use. Data/config returns 1.
is_cache_junk() {
  local p="$1" name; name=$(basename "$p")
  shopt -s nocasematch
  local r=1
  case "$name" in
    cache|.cache|caches|"code cache"|gpucache|*shadercache*|*shader_cache*|\
    cachestorage|scriptcache|mesa_shader_cache*|thumbnails|thumbnailcache|\
    crashpad|"crash reports"|logs|_logs|_cacache|tmp|temp|.tmp|.trash)
      r=0 ;;
  esac
  # Anything living inside a cache tree is cache too.
  if (( r )); then
    case "$p" in
      */.cache/*|*/Cache/*|*/CacheStorage/*|*/GPUCache/*|*/"Code Cache"/*|*/ShaderCache/*)
        r=0 ;;
    esac
  fi
  shopt -u nocasematch
  return $r
}
