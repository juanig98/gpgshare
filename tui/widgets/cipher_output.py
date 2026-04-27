"""
CipherOutput — panel con el texto cifrado/descifrado y botones Copiar/Guardar.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import TextArea, Button, Input, Label
from textual.containers import Vertical, Horizontal
from gpgshare.i18n import t


class CipherOutput(Widget):
    """Muestra un bloque de texto (ciphertext o plaintext) con acciones."""

    DEFAULT_CSS = """
    CipherOutput {
        height: auto;
        display: none;
    }
    CipherOutput.visible {
        display: block;
    }
    #save-path-row {
        layout: horizontal;
        height: auto;
        display: none;
    }
    #save-path-row.visible {
        display: block;
    }
    #save-path-input {
        width: 1fr;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._content = ""

    def compose(self) -> ComposeResult:
        title = self._title or t("cipher_output.label_default_title")
        yield Label(title, classes="form-label")
        yield TextArea("", id="output-text", read_only=True)
        with Horizontal(id="cipher-output-actions"):
            yield Button(t("cipher_output.btn_copy"), id="btn-copy", variant="success")
            yield Button(t("cipher_output.btn_save_toggle"), id="btn-save-toggle")
        with Horizontal(id="save-path-row"):
            yield Input(placeholder=t("cipher_output.placeholder_save_path"), id="save-path-input")
            yield Button(t("cipher_output.btn_save_confirm"), id="btn-save-confirm", variant="primary")

    def set_content(self, text: str) -> None:
        self._content = text
        self.query_one("#output-text", TextArea).load_text(text)
        self.add_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        match event.button.id:
            case "btn-copy":
                self._copy()
            case "btn-save-toggle":
                self._toggle_save_row()
            case "btn-save-confirm":
                self._save_file()

    def _copy(self) -> None:
        if not self._content:
            return
        self.app.copy_to_clipboard(self._content)
        self.app.notify(t("cipher_output.notify.copied"), severity="information")

    def _toggle_save_row(self) -> None:
        row = self.query_one("#save-path-row")
        row.toggle_class("visible")

    def _save_file(self) -> None:
        path_str = self.query_one("#save-path-input", Input).value.strip()
        if not path_str:
            self.app.notify(t("cipher_output.notify.no_path"), severity="warning")
            return
        try:
            Path(path_str).write_text(self._content)
            self.app.notify(t("cipher_output.notify.saved", path_str=path_str), severity="information")
            self.query_one("#save-path-row").remove_class("visible")
        except Exception as exc:
            self.app.notify(t("cipher_output.notify.save_error", exc=exc), severity="error")
