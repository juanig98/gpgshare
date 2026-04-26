"""
KeySelector — widget que carga colaboradores y expone un Select.
Emite CollaboratorSelected cuando cambia la selección.
"""

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Select, Label


class KeySelector(Widget):
    DEFAULT_CSS = """
    KeySelector {
        height: auto;
    }
    """

    class CollaboratorSelected(Message):
        """Emitido cuando el usuario elige un colaborador."""

        def __init__(self, alias: str, email: str) -> None:
            super().__init__()
            self.alias = alias
            self.email = email

    def compose(self) -> ComposeResult:
        yield Label("Destinatario", classes="form-label")
        yield Select(options=self._load_options(), id="key-select", prompt="Elegir colaborador…")

    def _load_options(self) -> list[tuple[str, str]]:
        try:
            from gpgshare.collaborators import load_all
            cfg = getattr(self.app, "_cfg", None)
            if cfg is None:
                return []
            collaborators = load_all(cfg.collaborators_file)
            return [(f"{c.alias}  <{c.email}>", c.alias) for c in collaborators]
        except Exception:
            return []

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.BLANK:
            return
        alias = str(event.value)
        try:
            from gpgshare.collaborators import find_by_alias
            cfg = getattr(self.app, "_cfg", None)
            if cfg is None:
                return
            collab = find_by_alias(cfg.collaborators_file, alias)
            if collab:
                self.post_message(self.CollaboratorSelected(collab.alias, collab.email))
        except Exception:
            pass
