"""
SetupScreen — formulario para configurar .env desde la TUI.
Closes #1
"""

import os
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Input, Label, Static
from textual.containers import Vertical, ScrollableContainer


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

_FIELDS = [
    ("GPG_SIGNER_EMAIL",      "Email del firmante (requerido)",          False, False),
    ("GPG_PRIVATE_KEY_PATH",  "Ruta a la clave privada .asc (requerido)", False, False),
    ("GPG_HOME",              "Directorio GPG (opcional, default ~/.gnupg)", True, False),
    ("KEYS_DIR",              "Directorio de claves públicas (opcional)", True, False),
    ("COLLABORATORS_FILE",    "Archivo de colaboradores (opcional)",      True, False),
]


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return values
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip()
    return values


def _write_env(values: dict[str, str]) -> None:
    lines = []
    for key, val in values.items():
        lines.append(f"{key}={val}")
    _ENV_PATH.write_text("\n".join(lines) + "\n")


class SetupScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Volver"),
        ("ctrl+s", "save", "Guardar"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(id="setup-container"):
                yield Static("Configuración del entorno", id="setup-title")
                yield Static(
                    "Los campos requeridos se guardan en el archivo .env del proyecto.",
                    id="setup-subtitle",
                )
                current = _read_env()
                for key, label, optional, _ in _FIELDS:
                    yield Label(
                        f"{label}{' *' if not optional else ''}",
                        classes="form-label",
                    )
                    yield Input(
                        value=current.get(key, ""),
                        placeholder=key,
                        id=f"input-{key}",
                    )
                with Vertical(classes="form-actions"):
                    yield Button("Guardar", id="btn-save", variant="success")
                    yield Button("Cancelar", id="btn-cancel")
                yield Static("", id="setup-status")  # errores de validación
        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        self._do_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._do_save()
        elif event.button.id == "btn-cancel":
            self.action_go_back()

    def _do_save(self) -> None:
        values: dict[str, str] = {}
        missing = []

        for key, _, optional, _ in _FIELDS:
            widget: Input = self.query_one(f"#input-{key}", Input)
            val = widget.value.strip()
            if val:
                values[key] = val
            elif not optional:
                missing.append(key)

        status = self.query_one("#setup-status", Static)

        if missing:
            status.update(f"[red]Faltan campos requeridos: {', '.join(missing)}[/red]")
            return

        try:
            _write_env(values)
            # Recargar variables de entorno en el proceso actual
            for key, val in values.items():
                os.environ[key] = val
            self.notify("Configuración guardada correctamente.", severity="information", title="Setup")
            self.app.pop_screen()
        except OSError as exc:
            status.update(f"[red]Error al guardar: {exc}[/red]")
