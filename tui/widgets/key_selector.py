"""
KeySelector — widget que carga colaboradores y expone un SelectionList.
Permite selección múltiple de destinatarios.
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import SelectionList, Label
from gpgshare.i18n import t


class KeySelector(Widget):
    DEFAULT_CSS = """
    KeySelector {
        height: auto;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._loaded = False

    def compose(self) -> ComposeResult:
        yield Label(t("key_selector.label"), classes="form-label")
        yield SelectionList(id="key-selection")

    def on_mount(self) -> None:
        self.load_options()

    def load_options(self) -> None:
        if self._loaded:
            return
        try:
            from gpgshare.collaborators import load_all
            cfg = getattr(self.app, "_cfg", None)
            if cfg is None:
                return
            collaborators = load_all(cfg.collaborators_file)
            sl = self.query_one(SelectionList)
            options = [
                (f"{c.alias}  <{c.email}>", c.alias)
                for c in collaborators
                if c.email.lower() != cfg.signer_email.lower()
                and (cfg.keys_dir / c.gpgkey).exists()
            ]
            sl.add_options(options)
            self._loaded = True
        except Exception as e:
            import sys
            print(f"KeySelector load error: {e}", file=sys.stderr)

    def get_selected_aliases(self) -> list[str]:
        sl = self.query_one(SelectionList)
        return list(sl.selected)

    def select_all(self) -> None:
        sl = self.query_one(SelectionList)
        sl.select_all()

    def deselect_all(self) -> None:
        sl = self.query_one(SelectionList)
        sl.deselect_all()