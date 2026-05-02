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
from gpgshare.i18n import t


class DecryptScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back", priority=True),
        ("ctrl+d", "decrypt", "Decrypt"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(classes="form-section"):
                yield Label(t("decrypt.label_ciphertext"), classes="form-label")
                yield TextArea("", id="cipher-input", language=None)

                with Horizontal(classes="form-actions"):
                    yield Button(t("decrypt.btn_load_toggle"), id="btn-load-toggle")

                with Horizontal(id="load-path-row"):
                    yield Input(placeholder=t("decrypt.placeholder_file_path"), id="load-path-input")
                    yield Button(t("decrypt.btn_load_confirm"), id="btn-load-confirm", variant="default")

                with Horizontal(id="passphrase-row"):
                    yield Label(t("decrypt.label_passphrase"))
                    yield Input(password=True, placeholder="", id="passphrase-input")

                with Horizontal(classes="form-actions"):
                    yield Button(t("decrypt.btn_decrypt"), id="btn-decrypt", variant="primary")
                    yield Button(t("decrypt.btn_back"), id="btn-back", variant="default")

                yield LoadingIndicator(id="loading")
                yield Static("", id="decrypt-error", classes="error-detail")
                yield Static("", id="sig-badge")
                yield CipherOutput(title=t("decrypt.cipher_output_title"), id="plain-output")
        yield Footer()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()

    def on_mount(self) -> None:
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#load-path-row").display = False
        self.query_one("#decrypt-error", Static).display = False
        self.title = t("decrypt.title")
        cfg = getattr(self.app, "_cfg", None)
        if cfg:
            self.sub_title = t("decrypt.subtitle_signing", email=cfg.signer_email)

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
            self.app.notify(t("decrypt.notify.no_path"), severity="warning")
            return
        try:
            content = Path(path_str).read_text()
            self.query_one("#cipher-input", TextArea).load_text(content)
            self.app.notify(t("decrypt.notify.file_loaded"), severity="information")
        except Exception as exc:
            self.app.notify(t("decrypt.notify.error_file", exc=exc), severity="error")

    def action_decrypt(self) -> None:
        ciphertext = self.query_one("#cipher-input", TextArea).text.strip()
        if not ciphertext:
            self.app.notify(t("decrypt.notify.no_ciphertext"), severity="warning")
            return

        cfg = getattr(self.app, "_cfg", None)
        if cfg is None:
            self.app.notify(t("decrypt.notify.no_config"), severity="error")
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
                        t("decrypt.notify.error_import_private", result=result),
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
                self.app.call_from_thread(self._show_error, plaintext)
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _set_loading(self, visible: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = visible
        self.query_one("#btn-decrypt", Button).disabled = visible

    def _show_error(self, error: str) -> None:
        widget = self.query_one("#decrypt-error", Static)
        widget.update(t("decrypt.notify.error_decrypt", error=error))
        widget.display = True

    def _show_result(self, plaintext: str, signer_fp: str | None) -> None:
        self.query_one("#decrypt-error", Static).display = False
        self.query_one("#plain-output", CipherOutput).set_content(plaintext)

        badge = self.query_one("#sig-badge", Static)
        if signer_fp:
            badge.update(t("decrypt.badge_valid_sig", signer_fp=signer_fp))
            badge.remove_class("unknown")
            badge.add_class("valid")
        else:
            badge.update(t("decrypt.badge_no_sig"))
            badge.remove_class("valid")
            badge.add_class("unknown")

        self.app.notify(t("decrypt.notify.success"), severity="information")
