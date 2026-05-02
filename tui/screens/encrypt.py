"""
EncryptScreen — cifrar un mensaje para un colaborador.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, TextArea, Button, Checkbox, Input, Label, LoadingIndicator, Static
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.worker import Worker, WorkerState
from textual import work

from gpgshare.tui.widgets.key_selector import KeySelector
from gpgshare.tui.widgets.cipher_output import CipherOutput
from gpgshare.i18n import t


class EncryptScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back", priority=True),
        ("ctrl+e", "encrypt", "Encrypt"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._selected_alias: str | None = None
        self._selected_email: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(classes="form-section"):
                yield Label(t("encrypt.label_message"), classes="form-label")
                yield TextArea("", id="message-input", language=None)

                yield KeySelector(id="key-selector")

                yield Checkbox(t("encrypt.chk_sign"), value=True, id="chk-sign")

                with Horizontal(id="passphrase-row"):
                    yield Label(t("encrypt.label_passphrase"))
                    yield Input(password=True, placeholder="", id="passphrase-input")

                with Horizontal(classes="form-actions"):
                    yield Button(t("encrypt.btn_encrypt"), id="btn-encrypt", variant="primary")
                    yield Button(t("encrypt.btn_back"), id="btn-back", variant="default")

                yield LoadingIndicator(id="loading")
                yield Static("", id="encrypt-error", classes="error-detail")
                yield CipherOutput(title=t("encrypt.cipher_output_title"), id="cipher-output")
        yield Footer()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.app.pop_screen()

    def on_mount(self) -> None:
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#encrypt-error", Static).display = False
        self.title = t("encrypt.title")
        cfg = getattr(self.app, "_cfg", None)
        if cfg:
            self.sub_title = t("encrypt.subtitle_signing", email=cfg.signer_email)

    def on_key_selector_collaborator_selected(self, event: KeySelector.CollaboratorSelected) -> None:
        self._selected_alias = event.alias
        self._selected_email = event.email

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-encrypt":
                self.action_encrypt()
            case "btn-back":
                self.app.pop_screen()

    def action_encrypt(self) -> None:
        if self._selected_email is None:
            self.app.notify(t("encrypt.notify.no_recipient"), severity="warning")
            return

        message = self.query_one("#message-input", TextArea).text.strip()
        if not message:
            self.app.notify(t("encrypt.notify.empty_message"), severity="warning")
            return

        cfg = getattr(self.app, "_cfg", None)
        if cfg is None:
            self.app.notify(t("encrypt.notify.no_config"), severity="error")
            return

        passphrase = self.query_one("#passphrase-input", Input).value or None
        sign = self.query_one("#chk-sign", Checkbox).value

        self._run_encrypt(
            message=message,
            recipient_email=self._selected_email,
            signer_email=cfg.signer_email if sign else None,
            passphrase=passphrase,
        )

    @work(thread=True)
    def _run_encrypt(
        self,
        message: str,
        recipient_email: str,
        signer_email: str | None,
        passphrase: str | None,
    ) -> None:
        from gpgshare import crypto
        from gpgshare.collaborators import find_by_alias

        self.app.call_from_thread(self._set_loading, True)
        try:
            cfg = self.app._cfg

            collab = find_by_alias(cfg.collaborators_file, self._selected_alias)
            if collab is None:
                self.app.call_from_thread(
                    self.app.notify, t("encrypt.notify.collaborator_not_found"), severity="error"
                )
                return

            key_path = cfg.keys_dir / collab.gpgkey
            ok, result = crypto.import_key(str(key_path), cfg.gpg_home)
            if not ok:
                self.app.call_from_thread(
                    self.app.notify, t("encrypt.notify.error_import_key", result=result), severity="error"
                )
                return

            if cfg.keyring_disabled:
                ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
                if not ok:
                    self.app.call_from_thread(
                        self.app.notify, t("encrypt.notify.error_import_private", result=result), severity="error"
                    )
                    return

            ok, ciphertext = crypto.encrypt_and_sign(
                content=message,
                recipient_email=recipient_email,
                signer_key_id=signer_email or cfg.signer_email,
                passphrase=passphrase,
                gpg_home=cfg.gpg_home,
            )

            if ok:
                self.app.call_from_thread(self._show_result, ciphertext)
            else:
                self.app.call_from_thread(self._show_error, ciphertext)
        finally:
            self.app.call_from_thread(self._set_loading, False)

    def _set_loading(self, visible: bool) -> None:
        self.query_one("#loading", LoadingIndicator).display = visible
        self.query_one("#btn-encrypt", Button).disabled = visible

    def _show_error(self, error: str) -> None:
        widget = self.query_one("#encrypt-error", Static)
        widget.update(t("encrypt.notify.error_encrypt", error=error))
        widget.display = True

    def _show_result(self, ciphertext: str) -> None:
        self.query_one("#encrypt-error", Static).display = False
        self.query_one("#cipher-output", CipherOutput).set_content(ciphertext)
        self.app.notify(t("encrypt.notify.success"), severity="information")
