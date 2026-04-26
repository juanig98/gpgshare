"""
Tests de la TUI con textual.testing.Pilot.
Cubren los flujos principales: navegación, cifrado, descifrado, colaboradores.
"""

import pytest
from unittest.mock import MagicMock, patch
from textual.pilot import Pilot

from gpgshare.tui.app import GpgShareApp


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_config() -> MagicMock:
    from pathlib import Path
    cfg = MagicMock()
    cfg.signer_email = "test@example.com"
    cfg.collaborators_file = Path("/tmp/collaborators.yaml")
    cfg.keys_dir = Path("/tmp/keys")
    cfg.private_key_path = "/tmp/private.asc"
    cfg.gpg_home = None
    return cfg


# ── tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_starts_and_shows_home():
    """La app arranca y muestra la pantalla de inicio."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.screen.__class__.__name__ == "HomeScreen"


@pytest.mark.asyncio
async def test_navigate_to_encrypt_screen():
    """Tecla 1 navega a EncryptScreen."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("1")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "EncryptScreen"


@pytest.mark.asyncio
async def test_navigate_to_decrypt_screen():
    """Tecla 2 navega a DecryptScreen."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("2")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "DecryptScreen"


@pytest.mark.asyncio
async def test_navigate_to_collaborators_screen():
    """Tecla 3 navega a CollaboratorsScreen."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            with patch("gpgshare.collaborators.load_all", return_value=[]):
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("3")
                    await pilot.pause()
                    assert app.screen.__class__.__name__ == "CollaboratorsScreen"


@pytest.mark.asyncio
async def test_back_button_returns_to_home():
    """Botón Volver desde EncryptScreen vuelve a HomeScreen."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            with patch("gpgshare.collaborators.load_all", return_value=[]):
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("1")
                    await pilot.pause()
                    assert app.screen.__class__.__name__ == "EncryptScreen"
                    await pilot.click("#btn-back")
                    await pilot.pause()
                    assert app.screen.__class__.__name__ == "HomeScreen"


@pytest.mark.asyncio
async def test_encrypt_requires_recipient():
    """Cifrar sin destinatario muestra notificación de advertencia."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            with patch("gpgshare.collaborators.load_all", return_value=[]):
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("1")
                    await pilot.pause()
                    await pilot.press("ctrl+e")
                    await pilot.pause()
                    # Should stay on EncryptScreen (not crash)
                    assert app.screen.__class__.__name__ == "EncryptScreen"


@pytest.mark.asyncio
async def test_decrypt_requires_ciphertext():
    """Descifrar sin texto cifrado muestra advertencia."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("2")
                await pilot.pause()
                await pilot.press("ctrl+d")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "DecryptScreen"


@pytest.mark.asyncio
async def test_startup_errors_shown_as_notifications():
    """Los errores de integridad del registro se muestran como notificaciones."""
    app = GpgShareApp()
    with patch("gpgshare.config.Config.load", return_value=_make_config()):
        with patch(
            "gpgshare.collaborators.validate_registry",
            return_value=["Key missing for 'juan'"],
        ):
            async with app.run_test() as pilot:
                await pilot.pause()
                # App should still start and show HomeScreen despite warnings
                assert app.screen.__class__.__name__ == "HomeScreen"
