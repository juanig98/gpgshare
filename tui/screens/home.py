"""
HomeScreen — pantalla principal con el menú de navegación.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Center, Middle, Vertical
from gpgshare.i18n import t


class HomeScreen(Screen):
    BINDINGS = [
        ("1", "go_encrypt", "Encrypt"),
        ("2", "go_decrypt", "Decrypt"),
        ("3", "go_collaborators", "Collaborators"),
        ("s", "go_setup", "Setup"),
        ("d", "toggle_dark", "Dark/Light"),
        ("q", "quit_app", "Quit"),
        ("up", "move_focus_up", "Previous"),
        ("down", "move_focus_down", "Next"),
        ("enter", "press_focused", "Select"),
    ]

    BUTTON_IDS = ["btn-encrypt", "btn-decrypt", "btn-collaborators", "btn-setup", "btn-quit"]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Middle():
                with Vertical(id="menu-container"):
                    yield Static(t("home.title"), id="home-title")
                    yield Static(t("home.subtitle"), id="home-subtitle")
                    yield Button(t("home.btn_encrypt"), id="btn-encrypt", variant="primary")
                    yield Button(t("home.btn_decrypt"), id="btn-decrypt")
                    yield Button(t("home.btn_collaborators"), id="btn-collaborators")
                    yield Button(t("home.btn_setup"), id="btn-setup", variant="warning")
                    yield Button(t("home.btn_quit"), id="btn-quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        cfg = getattr(self.app, "_cfg", None)
        if cfg:
            self.sub_title = t("home.subtitle_signing", email=cfg.signer_email)
        self.query_one("#btn-encrypt", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-encrypt":
                self.action_go_encrypt()
            case "btn-decrypt":
                self.action_go_decrypt()
            case "btn-collaborators":
                self.action_go_collaborators()
            case "btn-setup":
                self.action_go_setup()
            case "btn-quit":
                self.action_quit_app()

    def action_go_encrypt(self) -> None:
        from gpgshare.tui.screens.encrypt import EncryptScreen
        self.app.push_screen(EncryptScreen())

    def action_go_decrypt(self) -> None:
        from gpgshare.tui.screens.decrypt import DecryptScreen
        self.app.push_screen(DecryptScreen())

    def action_go_collaborators(self) -> None:
        from gpgshare.tui.screens.collaborators import CollaboratorsScreen
        self.app.push_screen(CollaboratorsScreen())

    def action_go_setup(self) -> None:
        from gpgshare.tui.screens.setup import SetupScreen
        self.app.push_screen(SetupScreen())

    def action_toggle_dark(self) -> None:
        self.app.action_toggle_dark()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_move_focus_up(self) -> None:
        current = self.screen.focused
        if current and current.id in self.BUTTON_IDS:
            idx = self.BUTTON_IDS.index(current.id)
            if idx > 0:
                self.query_one(f"#{self.BUTTON_IDS[idx - 1]}", Button).focus()
            else:
                self.query_one(f"#{self.BUTTON_IDS[-1]}", Button).focus()
        else:
            self.query_one("#btn-encrypt", Button).focus()

    def action_move_focus_down(self) -> None:
        current = self.screen.focused
        if current and current.id in self.BUTTON_IDS:
            idx = self.BUTTON_IDS.index(current.id)
            if idx < len(self.BUTTON_IDS) - 1:
                self.query_one(f"#{self.BUTTON_IDS[idx + 1]}", Button).focus()
            else:
                self.query_one(f"#{self.BUTTON_IDS[0]}", Button).focus()
        else:
            self.query_one("#btn-encrypt", Button).focus()

    def action_press_focused(self) -> None:
        focused = self.screen.focused
        if focused and hasattr(focused, "pressed"):
            focused.simulate_press()
