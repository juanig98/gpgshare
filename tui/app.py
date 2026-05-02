"""
GpgShareApp — root Textual application.
"""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer


class GpgShareApp(App):
    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "GPGShare"
    BINDINGS = [
        ("d", "toggle_dark", "Oscuro/Claro"),
    ]

    def on_mount(self) -> None:
        from gpgshare.config import Config
        from gpgshare.collaborators import validate_registry
        from gpgshare.tui.screens.home import HomeScreen

        self._cfg = None
        self._config_error = None

        try:
            self._cfg = Config.load()
            from gpgshare.i18n import setup_language, t
            from gpgshare.collaborators import find_by_email
            setup_language(self._cfg.language)
            errors = validate_registry(self._cfg.collaborators_file, self._cfg.keys_dir)
            if errors:
                for err in errors:
                    self.notify(err, severity="warning", title="Integridad del registro")
            if find_by_email(self._cfg.collaborators_file, self._cfg.signer_email) is None:
                self.notify(
                    t("app.warn.not_registered", email=self._cfg.signer_email),
                    severity="warning",
                    title=t("app.warn.not_registered_title"),
                    timeout=10,
                )
        except EnvironmentError as exc:
            self._config_error = str(exc)
            self.notify(str(exc), severity="error", title="Error de configuración")

        self.push_screen(HomeScreen())

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"
