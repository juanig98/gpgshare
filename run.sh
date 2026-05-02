#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET}  $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
info() { echo -e "${CYAN}→${RESET}  $*"; }

# ── 1. Entorno virtual ────────────────────────────────────────────────────────

if [ ! -d ".venv" ]; then
    warn "Entorno virtual no encontrado — ejecutando scripts/install.sh..."
    echo ""
    bash scripts/install.sh
    echo ""
fi

source .venv/bin/activate

# ── 2. Clave privada ──────────────────────────────────────────────────────────

PRIVATE_KEY_PATH=""

if [ -f ".env" ]; then
    PRIVATE_KEY_PATH="$(grep -E '^GPG_PRIVATE_KEY_PATH=' .env | cut -d= -f2- | tr -d '[:space:]')"
fi

PRIVATE_KEY_PATH="${PRIVATE_KEY_PATH/#\~/$HOME}"

if [ -z "$PRIVATE_KEY_PATH" ] || [ ! -f "$PRIVATE_KEY_PATH" ]; then
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────┐${RESET}"
    echo -e "${YELLOW}│  No se encontró una clave privada GPG       │${RESET}"
    echo -e "${YELLOW}└─────────────────────────────────────────────┘${RESET}"
    echo ""
    if [ -z "$PRIVATE_KEY_PATH" ]; then
        info "GPG_PRIVATE_KEY_PATH no está definido en .env"
    else
        info "El archivo '${BOLD}$PRIVATE_KEY_PATH${RESET}' no existe"
    fi
    echo ""
    echo -e "  Se va a crear una clave GPG nueva para tu usuario."
    echo -e "  ${CYAN}Presioná Enter para continuar o Ctrl+C para cancelar.${RESET}"
    echo ""
    read -r -p "  → "
    echo ""
    bash scripts/generate-key.sh
    echo ""
fi

# ── 3. Lanzar TUI ─────────────────────────────────────────────────────────────

ok "Entorno listo — iniciando gpgshare..."
echo ""
exec gpgshare tui
