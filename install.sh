#!/usr/bin/env bash
# install.sh — copy the tools into ~/bin and make sure ~/bin is on PATH.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts"
DEST="$HOME/bin"

mkdir -p "$DEST"
cp "$SRC"/* "$DEST"/
chmod +x "$DEST"/*
# _lib.sh is sourced, not run — no need for it to be executable, but harmless.

echo "Installed to $DEST:"
ls -1 "$DEST" | grep -v '^_lib.sh$' | sed 's/^/  /'

ensure_path_posix() {   # $1 = rc file
  local rc="$1"
  [[ -e "$rc" ]] || return 0
  grep -q 'HOME/bin' "$rc" 2>/dev/null && return 0
  echo 'export PATH="$HOME/bin:$PATH"' >> "$rc"
  echo "  + added ~/bin to PATH in $rc"
}

echo
echo "PATH setup:"
# fish
if command -v fish >/dev/null 2>&1; then
  fish -c 'contains "$HOME/bin" $fish_user_paths; or fish_add_path "$HOME/bin"' 2>/dev/null \
    && echo "  fish: ~/bin on PATH"
fi
# bash / zsh
ensure_path_posix "$HOME/.bashrc"
ensure_path_posix "$HOME/.zshrc"

echo
echo "Done. Open a new shell (or run 'disk-health' now if ~/bin is already on PATH)."
