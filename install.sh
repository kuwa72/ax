#!/bin/sh
# axs installer: curl -fsSL https://raw.githubusercontent.com/kuwa72/ax/main/install.sh | sh
# Env:
#   AXS_BIN_DIR  install target dir   (default: ~/.local/bin)
#   AXS_REF      git ref to fetch     (default: main)
#   AXS_SRC      full source URL      (overrides AXS_REF)
set -eu

AXS_BIN_DIR="${AXS_BIN_DIR:-$HOME/.local/bin}"
AXS_REF="${AXS_REF:-main}"
AXS_SRC="${AXS_SRC:-https://raw.githubusercontent.com/kuwa72/ax/$AXS_REF/axs}"

say()  { printf '%s\n' "$*"; }
warn() { printf 'axs: warn: %s\n' "$*" >&2; }

command -v python3 >/dev/null 2>&1 || warn "python3 not found in PATH (required)"
command -v fzf     >/dev/null 2>&1 || warn "fzf not found in PATH (required, >=0.44)"

mkdir -p "$AXS_BIN_DIR"
dst="$AXS_BIN_DIR/axs"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$AXS_SRC" -o "$dst"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dst" "$AXS_SRC"
else
    warn "neither curl nor wget found"
    exit 1
fi
chmod +x "$dst"

say "axs: installed to $dst"
case ":$PATH:" in
    *":$AXS_BIN_DIR:"*) ;;
    *) say "axs: add to PATH: export PATH=\"$AXS_BIN_DIR:\$PATH\"" ;;
esac
