"""
DecryptScreen — descifrar un mensaje y verificar su firma.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, TextArea, Button, Input, Label, LoadingIndicator, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual import work

from gpgshare.tui.widgets.cipher_output import CipherOutput


class DecryptScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Volver", priority=True),
        ("ctrl+d", "decrypt", "Descifrar"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(classes="form-section"):
                yield Label("Texto cifrado (ASCII armor)", classes="form-label")
                yield TextArea("", id="cipher-input", language=None)

                with Horizontal(classes="form-actions"):
                    yield Button("Cargar desde archivo…", id="btn-load-toggle")

                with Horizontal(id="load-path-row"):
                    yield Input(placeholder="/ruta/al/archivo.gpg", id="load-path-input")
                    yield Button("Cargar", id="btn-load-confirm", variant="default")

                with Horizontal(id="passphrase-row"):
                    yield Label("Passphrase (vacío = gpg-agent):")
                    yield Input(password=True, placeholder="", id="passphrase-input")

                with Horizontal(classes="form-actions"):
                    yield Button("Descifrar", id="btn-decrypt", variant="primary")
                    yield Button("Volver", id="btn-back", variant="default")

                yield LoadingIndicator(id="loading")
                yield Static("", id="sig-badge")
                yield CipherOutput(title="Mensaje descifrado", id="plain-output")
        yield Footer()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()

    def on_mount(self) -> None:
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#load-path-row").display = False
        self.title = "GPGShare — Descifrar"
        cfg = getattr(self.app, "_cfg", None)
        if cfg:
            self.sub_title = f"Firmando como: {cfg.signer_email}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-load-toggle":
                self.query_one("#load-path-row").toggle_class("visible")
                self.query_one("#load-path-row").display = not (
                    self.query_one("#load-path-row").display
                )
            case "btn-load-confirm":
                self._load_from_file()
            case "btn-decrypt":
                self.action_decrypt()
            case "btn-back":
                self.app.pop_screen()

    def _load_from_file(self) -> None:
        path_str = self.query_one("#load-path-input", Input).value.strip()
        if not path_str:
            self.app.notify("Ingresá una ruta de archivo.", severity="warning")
            return
        try:
            content = Path(path_str).read_text()
            self.query_one("#cipher-input", TextArea).load_text(content)
            self.app.notify("Archivo cargado.", severity="information")
        except Exception as exc:
            self.app.notify(f"Error al leer archivo: {exc}", severity="error")

    def action_decrypt(self) -> None:
        ciphertext = self.query_one("#cipher-input", TextArea).text.strip()
        if not ciphertext:
            self.app.notify("Pegá el texto cifrado primero.", severity="warning")
            return

        cfg = getattr(self.app, "_cfg", None)
        if cfg is None:
            self.app.notify("Configuración no disponible.", severity="error")
            return

        passphrase = self.query_one("#passphrase-input", Input).value or None
        self._run_decrypt(ciphertext=ciphertext, passphrase=passphrase)

    @work(thread=True)
    def _run_decrypt(self, ciphertext: str, passphrase: str | None) -> None:
        from gpgshare import crypto

        self.app.call_from_thread(self._set_loading, True)
        try:
            cfg = self.app._cfg

            if cfg.keyring_disabled:
                ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
                if not ok:
                    self.app.call_from_thread(
                        self.app.notify,
                        f"No se pudo importar clave privada: {result}",
                        severity="error",
                    )
                    return

            ok, plaintext, signer_fp = crypto.decrypt_and_verify(
                ciphertext=ciphertext,
                passphrase=passphrase,
                gpg_home=cfg.gpg_home,
            )

            if ok:
                self.app.call_from_thread(self._show_result, plaintext, signer_fp)
            else:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Error al descifrar: {plaintext}",
                    severity="error",
                )
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _set_loading(self, visible: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = visible
        self.query_one("#btn-decrypt", Button).disabled = visible

    def _show_result(self, plaintext: str, signer_fp: str | None) -> None:
        self.query_one("#plain-output", CipherOutput).set_content(plaintext)

        badge = self.query_one("#sig-badge", Static)
        if signer_fp:
            badge.update(f"✓ Firma válida — fingerprint: {signer_fp}")
            badge.remove_class("unknown")
            badge.add_class("valid")
        else:
            badge.update("⚠ Sin firma o no se pudo verificar")
            badge.remove_class("valid")
            badge.add_class("unknown")

        self.app.notify("Mensaje descifrado correctamente.", severity="information")
