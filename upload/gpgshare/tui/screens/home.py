"""
HomeScreen — pantalla principal con el menú de navegación.
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Center, Middle, Vertical


class HomeScreen(Screen):
    BINDINGS = [
        ("1", "go_encrypt", "Cifrar"),
        ("2", "go_decrypt", "Descifrar"),
        ("3", "go_collaborators", "Colaboradores"),
        ("d", "toggle_dark", "Oscuro/Claro"),
        ("q", "quit_app", "Salir"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Center():
            with Middle():
                with Vertical(id="menu-container"):
                    yield Static("GPGShare", id="home-title")
                    yield Static("Encriptación GPG entre colaboradores", id="home-subtitle")
                    yield Button("1  Cifrar mensaje", id="btn-encrypt", variant="primary")
                    yield Button("2  Descifrar mensaje", id="btn-decrypt")
                    yield Button("3  Colaboradores", id="btn-collaborators")
                    yield Button("Q  Salir", id="btn-quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        cfg = getattr(self.app, "_cfg", None)
        if cfg:
            self.sub_title = f"Firmando como: {cfg.signer_email}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-encrypt":
                self.action_go_encrypt()
            case "btn-decrypt":
                self.action_go_decrypt()
            case "btn-collaborators":
                self.action_go_collaborators()
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

    def action_toggle_dark(self) -> None:
        self.app.action_toggle_dark()

    def action_quit_app(self) -> None:
        self.app.exit()
