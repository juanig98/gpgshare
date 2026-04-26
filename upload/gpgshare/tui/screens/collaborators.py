"""
CollaboratorsScreen — listado y registro de colaboradores.
"""

import shutil
from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, DataTable, Button, Input, Label, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import work


class AddCollaboratorModal(ModalScreen):
    """Modal para agregar un nuevo colaborador."""

    BINDINGS = [Binding("escape", "dismiss", "Cancelar", priority=True)]

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Static("Agregar colaborador", id="modal-title")
            yield Label("Alias (ej: juan)", classes="form-label")
            yield Input(placeholder="juan", id="input-alias")
            yield Label("Email", classes="form-label")
            yield Input(placeholder="juan@empresa.com", id="input-email")
            yield Label("Ruta al archivo .asc", classes="form-label")
            yield Input(placeholder="/ruta/a/juan.asc", id="input-keypath")
            with Horizontal(id="modal-actions"):
                yield Button("Agregar", id="btn-confirm", variant="primary")
                yield Button("Cancelar", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-confirm":
            self._submit()

    def _submit(self) -> None:
        alias = self.query_one("#input-alias", Input).value.strip()
        email = self.query_one("#input-email", Input).value.strip()
        key_path = self.query_one("#input-keypath", Input).value.strip()

        errors = []
        if not alias:
            errors.append("El alias no puede estar vacío.")
        if not email or "@" not in email:
            errors.append("El email no es válido.")
        if not key_path:
            errors.append("La ruta al archivo .asc no puede estar vacía.")
        elif not Path(key_path).exists():
            errors.append(f"Archivo no encontrado: {key_path}")

        if errors:
            for e in errors:
                self.app.notify(e, severity="warning")
            return

        self.dismiss({"alias": alias, "email": email, "key_path": key_path})


class CollaboratorsScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Volver", priority=True),
        ("r", "reload", "Recargar"),
        ("a", "add", "Agregar"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(classes="form-section"):
                yield Label("Colaboradores registrados", classes="form-label")
                with Horizontal(id="collab-actions"):
                    yield Button("A  Agregar colaborador", id="btn-add", variant="primary")
                    yield Button("R  Recargar", id="btn-reload")
                    yield Button("Volver", id="btn-back")
                yield DataTable(id="collab-table")
        yield Footer()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()

    def on_mount(self) -> None:
        self.title = "GPGShare — Colaboradores"
        table = self.query_one("#collab-table", DataTable)
        table.add_columns("Alias", "Email", "Archivo de clave", "Estado")
        self._load_table()

    def _load_table(self) -> None:
        from gpgshare.collaborators import load_all
        table = self.query_one("#collab-table", DataTable)
        table.clear()
        cfg = getattr(self.app, "_cfg", None)
        if cfg is None:
            return
        try:
            collaborators = load_all(cfg.collaborators_file)
            for c in collaborators:
                key_path = cfg.keys_dir / c.gpgkey
                status = "✓ presente" if key_path.exists() else "✗ faltante"
                table.add_row(c.alias, c.email, c.gpgkey, status)
        except Exception as exc:
            self.app.notify(f"Error al cargar colaboradores: {exc}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-add":
                self.action_add()
            case "btn-reload":
                self.action_reload()
            case "btn-back":
                self.app.pop_screen()

    def action_reload(self) -> None:
        self._load_table()
        self.app.notify("Lista recargada.", severity="information")

    def action_add(self) -> None:
        self.app.push_screen(AddCollaboratorModal(), callback=self._on_modal_result)

    def _on_modal_result(self, result: dict | None) -> None:
        if result is None:
            return
        self._register_collaborator(
            alias=result["alias"],
            email=result["email"],
            key_path=result["key_path"],
        )

    @work(thread=True)
    def _register_collaborator(self, alias: str, email: str, key_path: str) -> None:
        from gpgshare import crypto
        from gpgshare.collaborators import add_collaborator

        cfg = self.app._cfg
        canonical_name = email.lower().replace("@", "-").replace(".", "-") + ".asc"
        dest = cfg.keys_dir / canonical_name

        try:
            cfg.keys_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(key_path, dest)

            ok, fingerprint = crypto.import_key(str(dest), cfg.gpg_home)
            if not ok:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Clave copiada pero no importada: {fingerprint}",
                    severity="warning",
                )

            add_collaborator(cfg.collaborators_file, alias, email, canonical_name)

            self.app.call_from_thread(self._load_table)
            self.app.call_from_thread(
                self.app.notify,
                f"Colaborador '{alias}' agregado. "
                "Commiteá collaborators.yaml y abrí un Pull Request.",
                severity="information",
            )
        except ValueError as exc:
            self.app.call_from_thread(self.app.notify, str(exc), severity="error")
        except Exception as exc:
            self.app.call_from_thread(
                self.app.notify,
                f"Error al registrar colaborador: {exc}",
                severity="error",
            )
