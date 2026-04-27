#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# gpgshare — install.sh
# Sets up the development environment from scratch.
# ─────────────────────────────────────────────────────────────────────────────

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "${RED}✗${RESET}  $*" >&2; exit 1; }
info() { echo -e "  $*"; }

echo -e "${BOLD}gpgshare — setup${RESET}"
echo "──────────────────────────────────────"

# ── 1. Python ─────────────────────────────────────────────────────────────────

PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

[ -z "$PYTHON" ] && fail "Python 3.11+ not found. Install it from https://python.org and re-run."
ok "Python $($PYTHON --version 2>&1 | awk '{print $2}') → $PYTHON"

# ── 2. GPG ────────────────────────────────────────────────────────────────────

if ! command -v gpg &>/dev/null; then
    fail "GPG not found. Install it (e.g. 'sudo apt install gnupg' or 'brew install gnupg') and re-run."
fi
ok "GPG $(gpg --version | head -1 | awk '{print $3}')"

# ── 3. Virtual environment ────────────────────────────────────────────────────

VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at $VENV_DIR — skipping creation."
else
    info "Creating virtual environment at $VENV_DIR..."
    "$PYTHON" -m venv "$VENV_DIR"
    ok "Virtual environment created."
fi

VENV_PIP="$VENV_DIR/bin/pip"

# ── 4. Dependencies ───────────────────────────────────────────────────────────

info "Installing dependencies..."
"$VENV_PIP" install --quiet --upgrade pip
"$VENV_PIP" install --quiet -e ".[dev]"
ok "Dependencies installed."

# ── 5. .env ───────────────────────────────────────────────────────────────────

if [ -f ".env" ]; then
    warn ".env already exists — skipping copy."
else
    cp .env.example .env
    ok ".env created from .env.example."
    warn "Edit .env and set GPG_PRIVATE_KEY_PATH and GPG_SIGNER_EMAIL before running gpgshare."
fi

# ── 6. GPG key check ──────────────────────────────────────────────────────────

if gpg --list-secret-keys --with-colons 2>/dev/null | grep -q "^sec"; then
    key_count=$(gpg --list-secret-keys --with-colons 2>/dev/null | grep -c "^sec" || true)
    ok "$key_count private key(s) found in GPG keyring."
else
    warn "No private keys found in GPG keyring."
    info "Generate one with:  gpg --full-generate-key"
    info "Or import one with: gpg --import your-private-key.asc"
fi

# ── 7. Summary ────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Setup complete.${RESET}"
echo ""
echo "Next steps:"
info "1. Edit ${BOLD}.env${RESET} with your GPG key path and signer email."
info "2. Run the CLI:  ${BOLD}.venv/bin/gpgshare --help${RESET}"
info "3. Run the TUI:  ${BOLD}.venv/bin/gpgshare tui${RESET}"
info "4. Run tests:    ${BOLD}.venv/bin/pytest${RESET}"
echo ""
info "Tip: activate the venv with  ${BOLD}source .venv/bin/activate${RESET}"
