#!/bin/sh
# ax installer: curl -fsSL https://raw.githubusercontent.com/kuwa72/ax/main/install.sh | sh
# Env:
#   AX_BIN_DIR  install target dir   (default: ~/.local/bin)
#   AX_REF      git ref to fetch     (default: main)
#   AX_SRC      full source URL      (overrides AX_REF)
set -eu

AX_BIN_DIR="${AX_BIN_DIR:-$HOME/.local/bin}"
AX_REF="${AX_REF:-main}"
AX_SRC="${AX_SRC:-https://raw.githubusercontent.com/kuwa72/ax/$AX_REF/ax}"

say()  { printf '%s\n' "$*"; }
warn() { printf 'ax: warn: %s\n' "$*" >&2; }

command -v python3 >/dev/null 2>&1 || warn "python3 not found in PATH (required)"
command -v fzf     >/dev/null 2>&1 || warn "fzf not found in PATH (required, >=0.44)"

mkdir -p "$AX_BIN_DIR"
dst="$AX_BIN_DIR/ax"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$AX_SRC" -o "$dst"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dst" "$AX_SRC"
else
    warn "neither curl nor wget found"
    exit 1
fi
chmod +x "$dst"

say "ax: installed to $dst"
case ":$PATH:" in
    *":$AX_BIN_DIR:"*) ;;
    *) say "ax: add to PATH: export PATH=\"$AX_BIN_DIR:\$PATH\"" ;;
esac
