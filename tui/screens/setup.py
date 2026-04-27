"""
SetupScreen — formulario para configurar .env desde la TUI.
Closes #1, #2
"""

import os
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Input, Label, Static, Select
from textual.containers import Vertical, ScrollableContainer
from textual import work


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

_FIELDS = [
    ("GPG_SIGNER_EMAIL",      "Email del firmante (requerido)",             False),
    ("GPG_PRIVATE_KEY_PATH",  "Ruta a la clave privada .asc (requerido)",   False),
    ("GPG_HOME",              "Directorio GPG (opcional, default ~/.gnupg)", True),
    ("KEYS_DIR",              "Directorio de claves públicas (opcional)",    True),
    ("COLLABORATORS_FILE",    "Archivo de colaboradores (opcional)",         True),
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
    lines = [f"{k}={v}" for k, v in values.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n")


def _canonical_filename(email: str) -> str:
    return email.lower().replace("@", "-").replace(".", "-") + ".asc"


def _uid_label(uid: str) -> str:
    """Return 'Name <email>' or the raw uid string."""
    return uid if uid else "(sin identificador)"


class SetupScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Volver"),
        ("ctrl+s", "save", "Guardar config"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(id="setup-container"):
                # ── Sección 1: .env ──────────────────────────────────────
                yield Static("Configuración del entorno", id="setup-title")
                yield Static(
                    "Los campos requeridos se guardan en el archivo .env del proyecto.",
                    id="setup-subtitle",
                )
                current = _read_env()
                for key, label, optional in _FIELDS:
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
                    yield Button("Guardar configuración", id="btn-save", variant="success")
                    yield Button("Cancelar", id="btn-cancel")
                yield Static("", id="setup-status")

                # ── Sección 2: Registrar mi clave pública ────────────────
                yield Static("Registrar mi clave pública", id="register-title")
                yield Static(
                    "Exporta tu clave pública al directorio keys/ y te registra como colaborador.",
                    id="register-subtitle",
                )
                yield Label("Seleccionar clave GPG *", classes="form-label")
                yield Select(
                    options=[],
                    prompt="Cargando claves...",
                    id="select-key",
                    allow_blank=True,
                )
                yield Label("Alias (tu nombre en el registro) *", classes="form-label")
                yield Input(placeholder="ej: juan", id="input-alias")
                with Vertical(classes="form-actions"):
                    yield Button("Registrar mi clave", id="btn-register", variant="primary")
                yield Static("", id="register-status")

        yield Footer()

    def on_mount(self) -> None:
        self._load_keys()

    @work(thread=True)
    def _load_keys(self) -> None:
        from gpgshare.crypto import list_secret_keys
        cfg = getattr(self.app, "_cfg", None)
        gpg_home = cfg.gpg_home if cfg else None
        keys = list_secret_keys(gpg_home)
        self.app.call_from_thread(self._populate_select, keys)

    def _populate_select(self, keys: list[dict]) -> None:
        select: Select = self.query_one("#select-key", Select)
        cfg = getattr(self.app, "_cfg", None)
        signer_email = cfg.signer_email if cfg else _read_env().get("GPG_SIGNER_EMAIL", "")

        options = []
        preselect = None
        for k in keys:
            label = k["uids"][0] if k["uids"] else k["keyid"]
            options.append((label, k["keyid"]))
            if signer_email and any(signer_email.lower() in uid.lower() for uid in k["uids"]):
                preselect = k["keyid"]

        if not options:
            select.set_options([("No se encontraron claves secretas en el keyring", "")])
            return

        select.set_options(options)
        if preselect:
            select.value = preselect

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        self._do_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-save":
                self._do_save()
            case "btn-cancel":
                self.action_go_back()
            case "btn-register":
                self._do_register()

    def _do_save(self) -> None:
        values: dict[str, str] = {}
        missing = []

        for key, _, optional in _FIELDS:
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
            for key, val in values.items():
                os.environ[key] = val
            self.notify("Configuración guardada correctamente.", severity="information", title="Setup")
            self.app.pop_screen()
        except OSError as exc:
            status.update(f"[red]Error al guardar: {exc}[/red]")

    def _do_register(self) -> None:
        select: Select = self.query_one("#select-key", Select)
        alias_input: Input = self.query_one("#input-alias", Input)
        status = self.query_one("#register-status", Static)

        keyid = select.value
        alias = alias_input.value.strip()

        if not keyid or keyid is Select.BLANK:
            status.update("[red]Seleccioná una clave GPG.[/red]")
            return
        if not alias:
            status.update("[red]El alias es requerido.[/red]")
            return

        # Obtener el email del uid seleccionado
        uid_label = str(select._options[  # buscar label del valor seleccionado
            next(i for i, (_, v) in enumerate(select._options) if v == keyid)
        ][0]) if hasattr(select, "_options") else ""

        # Extraer email del uid (formato "Name <email@domain.com>")
        import re
        match = re.search(r"<(.+?)>", uid_label)
        email = match.group(1) if match else uid_label

        status.update("[yellow]Registrando...[/yellow]")
        self._run_register(keyid, alias, email)

    @work(thread=True)
    def _run_register(self, keyid: str, alias: str, email: str) -> None:
        from gpgshare.crypto import export_public_key
        from gpgshare.collaborators import add_collaborator, find_by_email, find_by_alias

        cfg = getattr(self.app, "_cfg", None)
        gpg_home = cfg.gpg_home if cfg else None

        if cfg:
            keys_dir = cfg.keys_dir
            collaborators_file = cfg.collaborators_file
        else:
            env = _read_env()
            keys_dir = Path(env.get("KEYS_DIR", str(_PROJECT_ROOT / "keys")))
            collaborators_file = Path(env.get("COLLABORATORS_FILE", str(_PROJECT_ROOT / "collaborators.yaml")))

        ok, result = export_public_key(keyid, gpg_home)
        if not ok:
            self.app.call_from_thread(self._set_register_status, f"[red]Error al exportar clave: {result}[/red]")
            return

        filename = _canonical_filename(email)
        key_path = keys_dir / filename
        try:
            keys_dir.mkdir(parents=True, exist_ok=True)
            key_path.write_text(result)
        except OSError as exc:
            self.app.call_from_thread(self._set_register_status, f"[red]Error al escribir {filename}: {exc}[/red]")
            return

        try:
            add_collaborator(collaborators_file, alias, email, filename)
        except ValueError as exc:
            self.app.call_from_thread(self._set_register_status, f"[red]{exc}[/red]")
            return

        self.app.call_from_thread(
            self._set_register_status,
            f"[green]Clave registrada como '{alias}' ({email}) → keys/{filename}[/green]",
        )

    def _set_register_status(self, msg: str) -> None:
        self.query_one("#register-status", Static).update(msg)
