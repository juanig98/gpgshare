#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# generate-key.sh — genera un par de claves GPG y configura gpgshare.
# ---------------------------------------------------------------------------

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}✓${RESET}  $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
fail() { echo -e "${RED}✗${RESET}  $*" >&2; exit 1; }
info() { echo -e "${CYAN}→${RESET}  $*"; }
step() { echo -e "\n${BOLD}$*${RESET}"; }

CURRENT_USER="$(whoami)"
GPG_DIR="$HOME/.gnupg"
PRIVATE_KEY_FILE="$GPG_DIR/${CURRENT_USER}-private-key.asc"
PUBLIC_KEY_FILE="$GPG_DIR/${CURRENT_USER}-public-key.asc"

echo ""
echo -e "${BOLD}gpgshare — Generador de clave GPG${RESET}"
echo "──────────────────────────────────────"
echo -e "  Usuario : ${CYAN}$CURRENT_USER${RESET}"
echo -e "  Destino : ${CYAN}$GPG_DIR${RESET}"
echo ""
echo -e "  Se abrirá el asistente interactivo de GPG."
echo -e "  ${YELLOW}Recomendaciones:${RESET}"
echo -e "    · Tipo de clave : RSA and RSA ${CYAN}(opción 1, default)${RESET}"
echo -e "    · Tamaño        : ${CYAN}4096 bits${RESET}"
echo -e "    · Expiración    : ${CYAN}0${RESET} (sin expiración) o según tu política"
echo -e "    · UID           : usá tu email de trabajo"
echo ""
read -r -p "  Presioná Enter para abrir el asistente de GPG..."

# 1. Generar la clave de forma interactiva
step "Paso 1 — Generando clave GPG..."
gpg --full-generate-key

# 2. Mostrar claves disponibles
step "Paso 2 — Claves secretas disponibles"
echo ""
gpg --list-secret-keys --keyid-format LONG
echo ""
info "Copiá el KEY_ID largo de la clave que acabás de crear"
echo -e "     ${CYAN}(ejemplo: ABC123DEF456789A — 16 caracteres hexadecimales)${RESET}"
echo ""
read -r -p "  KEY_ID → " KEY_ID

[[ -z "$KEY_ID" ]] && fail "No ingresaste un KEY_ID."

# 3. Exportar clave privada
step "Paso 3 — Exportando claves..."
echo ""
info "Exportando clave privada → ${BOLD}$PRIVATE_KEY_FILE${RESET}"
warn "GPG puede pedirte tu passphrase para proteger el archivo."
gpg --armor --export-secret-keys "$KEY_ID" > "$PRIVATE_KEY_FILE"
chmod 600 "$PRIVATE_KEY_FILE"
ok "Clave privada exportada"

# 4. Exportar clave pública
info "Exportando clave pública  → ${BOLD}$PUBLIC_KEY_FILE${RESET}"
gpg --armor --export "$KEY_ID" > "$PUBLIC_KEY_FILE"
chmod 644 "$PUBLIC_KEY_FILE"
ok "Clave pública exportada"

# 5. Obtener el email asociado al key ID
SIGNER_EMAIL="$(gpg --list-secret-keys --keyid-format LONG "$KEY_ID" 2>/dev/null \
  | grep -oE '[^<>]+@[^<>]+' | head -1 || true)"

# 6. Actualizar el .env
step "Paso 4 — Actualizando configuración..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$PROJECT_DIR/.env.example" ]]; then
        cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
        info "Creado .env desde .env.example"
    else
        touch "$ENV_FILE"
    fi
fi

set_env_var() {
    local key="$1" value="$2"
    if grep -qE "^#?${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak -E "s|^#?${key}=.*|${key}=${value}|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

set_env_var "GPG_PRIVATE_KEY_PATH" "$PRIVATE_KEY_FILE"
[[ -n "$SIGNER_EMAIL" ]] && set_env_var "GPG_SIGNER_EMAIL" "$SIGNER_EMAIL"
ok ".env actualizado"

# 7. Resumen
echo ""
echo -e "${GREEN}┌─────────────────────────────────────────────────────────┐${RESET}"
echo -e "${GREEN}│  ✓  Clave generada y configuración actualizada           │${RESET}"
echo -e "${GREEN}└─────────────────────────────────────────────────────────┘${RESET}"
echo ""
echo -e "  ${BOLD}GPG_PRIVATE_KEY_PATH${RESET} = $PRIVATE_KEY_FILE"
[[ -n "$SIGNER_EMAIL" ]] && echo -e "  ${BOLD}GPG_SIGNER_EMAIL${RESET}     = $SIGNER_EMAIL"
echo ""
echo -e "  ${YELLOW}Clave pública para compartir con colaboradores:${RESET}"
echo -e "  ${CYAN}$PUBLIC_KEY_FILE${RESET}"
echo ""

# 8. Verificar si ya está registrado como colaborador
step "Paso 5 — Verificando registro como colaborador..."
COLLAB_FILE="$PROJECT_DIR/collaborators.yaml"
REGISTERED=false

if [[ -n "$SIGNER_EMAIL" ]] && [[ -f "$COLLAB_FILE" ]]; then
    if grep -qi "$SIGNER_EMAIL" "$COLLAB_FILE"; then
        REGISTERED=true
    fi
fi

if [[ "$REGISTERED" == true ]]; then
    ok "Ya estás registrado como colaborador con ${CYAN}$SIGNER_EMAIL${RESET}"
else
    echo ""
    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${YELLOW}│  ⚠  No estás registrado como colaborador                 │${RESET}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${RESET}"
    echo ""
    if [[ -z "$SIGNER_EMAIL" ]]; then
        info "No se pudo detectar tu email — registrate manualmente:"
        echo -e "  ${CYAN}gpgshare add-key <alias> <email> $PUBLIC_KEY_FILE${RESET}"
    else
        info "Para que tus compañeros puedan enviarte mensajes, necesitás"
        info "registrar tu clave pública en el proyecto."
        echo ""
        read -r -p "  ¿Querés registrarte ahora? Tu alias (ej: juan): " ALIAS
        if [[ -n "$ALIAS" ]]; then
            VENV_GPGSHARE="$PROJECT_DIR/.venv/bin/gpgshare"
            if [[ -x "$VENV_GPGSHARE" ]]; then
                "$VENV_GPGSHARE" add-key "$ALIAS" "$SIGNER_EMAIL" "$PUBLIC_KEY_FILE" \
                    && ok "Registrado como '${BOLD}$ALIAS${RESET}' — commiteá collaborators.yaml y abrí un Pull Request." \
                    || warn "No se pudo registrar automáticamente. Ejecutá manualmente:"
            else
                warn "Entorno no activado. Ejecutá manualmente:"
            fi
            echo -e "  ${CYAN}gpgshare add-key $ALIAS $SIGNER_EMAIL $PUBLIC_KEY_FILE${RESET}"
        else
            warn "Sin alias — podés registrarte luego con:"
            echo -e "  ${CYAN}gpgshare add-key <alias> $SIGNER_EMAIL $PUBLIC_KEY_FILE${RESET}"
        fi
    fi
fi
echo ""
