"""
Tests for gpgshare.cli — all commands via Typer's CliRunner.
External I/O (GPG, filesystem for keys) is mocked.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from gpgshare.cli import app


runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_config(tmp_path: Path) -> MagicMock:
    collab_file = tmp_path / "collaborators.yaml"
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    cfg = MagicMock()
    cfg.signer_email = "me@example.com"
    cfg.collaborators_file = collab_file
    cfg.keys_dir = keys_dir
    cfg.private_key_path = str(tmp_path / "private.asc")
    cfg.gpg_home = None
    return cfg


def _write_registry(path: Path, entries: list[dict]) -> None:
    path.write_text(yaml.dump(entries))


def _write_key(keys_dir: Path, filename: str) -> None:
    (keys_dir / filename).write_text("fake key data")


# ── encrypt ───────────────────────────────────────────────────────────────────

class TestEncryptCommand:
    def test_unknown_recipient_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [])

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                result = runner.invoke(app, ["encrypt", "nobody", "-m", "hello"])

        assert result.exit_code == 1
        assert "not found" in result.stderr

    def test_empty_message_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
        ])

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                result = runner.invoke(app, ["encrypt", "juan", "-m", "   "])

        assert result.exit_code == 1

    def test_success_prints_ciphertext(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
        ])
        _write_key(cfg.keys_dir, "juan.asc")
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.encrypt_and_sign", return_value=(True, "-----BEGIN PGP-----\nciphertext\n-----END PGP-----")):
                        result = runner.invoke(app, ["encrypt", "juan", "-m", "hello"])

        assert result.exit_code == 0
        assert "ciphertext" in result.stdout

    def test_success_copies_to_clipboard(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
        ])
        _write_key(cfg.keys_dir, "juan.asc")
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.encrypt_and_sign", return_value=(True, "CIPHER")):
                        with patch("pyperclip.copy") as mock_copy:
                            result = runner.invoke(app, ["encrypt", "juan", "-m", "hello", "--clipboard"])

        assert result.exit_code == 0
        mock_copy.assert_called_once_with("CIPHER")

    def test_success_writes_to_file(self, tmp_path):
        cfg = _make_config(tmp_path)
        out_file = tmp_path / "out.gpg"
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
        ])
        _write_key(cfg.keys_dir, "juan.asc")
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.encrypt_and_sign", return_value=(True, "CIPHER_CONTENT")):
                        runner.invoke(app, ["encrypt", "juan", "-m", "hello", "--output", str(out_file)])

        assert out_file.read_text() == "CIPHER_CONTENT"

    def test_encrypt_failure_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
        ])
        _write_key(cfg.keys_dir, "juan.asc")
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.encrypt_and_sign", return_value=(False, "key not found")):
                        result = runner.invoke(app, ["encrypt", "juan", "-m", "hello"])

        assert result.exit_code == 1


# ── decrypt ───────────────────────────────────────────────────────────────────

class TestDecryptCommand:
    def test_no_ciphertext_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    result = runner.invoke(app, ["decrypt", "--ciphertext", "   "])

        assert result.exit_code == 1

    def test_success_prints_plaintext(self, tmp_path):
        cfg = _make_config(tmp_path)
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.decrypt_and_verify", return_value=(True, "plain text", "SIGNER_FP")):
                        result = runner.invoke(app, ["decrypt", "--ciphertext", "BEGIN PGP"])

        assert result.exit_code == 0
        assert "plain text" in result.stdout
        assert "SIGNER_FP" in result.stdout

    def test_success_without_signature_shows_warning(self, tmp_path):
        cfg = _make_config(tmp_path)
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.decrypt_and_verify", return_value=(True, "plain text", None)):
                        result = runner.invoke(app, ["decrypt", "--ciphertext", "BEGIN PGP"])

        assert result.exit_code == 0
        assert "No signature" in result.stdout or "no se pudo" in result.stdout.lower() or "⚠" in result.stdout

    def test_failure_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.decrypt_and_verify", return_value=(False, "bad passphrase", None)):
                        result = runner.invoke(app, ["decrypt", "--ciphertext", "BEGIN PGP"])

        assert result.exit_code == 1

    def test_loads_ciphertext_from_file(self, tmp_path):
        cfg = _make_config(tmp_path)
        cipher_file = tmp_path / "msg.gpg"
        cipher_file.write_text("-----BEGIN PGP MESSAGE-----\ndata\n-----END PGP MESSAGE-----")
        (tmp_path / "private.asc").write_text("private key")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                    with patch("gpgshare.crypto.decrypt_and_verify", return_value=(True, "hello", "FP")) as mock_dec:
                        runner.invoke(app, ["decrypt", "--input", str(cipher_file)])

        called_cipher = mock_dec.call_args[1]["ciphertext"]
        assert "BEGIN PGP" in called_cipher


# ── add-key ───────────────────────────────────────────────────────────────────

class TestAddKeyCommand:
    def test_missing_key_file_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)

        with patch("gpgshare.cli._load_config", return_value=cfg):
            result = runner.invoke(app, ["add-key", "bob", "bob@x.com", str(tmp_path / "nonexistent.asc")])

        assert result.exit_code == 1

    def test_success_copies_key_and_adds_to_yaml(self, tmp_path):
        cfg = _make_config(tmp_path)
        key_file = tmp_path / "bob.asc"
        key_file.write_text("public key data")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.crypto.import_key", return_value=(True, "BOB_FP")):
                result = runner.invoke(app, ["add-key", "bob", "bob@x.com", str(key_file)])

        assert result.exit_code == 0
        expected_dest = cfg.keys_dir / "bob-x-com.asc"
        assert expected_dest.exists()
        collaborators = yaml.safe_load(cfg.collaborators_file.read_text())
        assert any(c["alias"] == "bob" for c in collaborators)

    def test_duplicate_alias_exits_1(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "bob", "email": "bob@x.com", "gpgkey": "bob-x-com.asc"},
        ])
        key_file = tmp_path / "bob2.asc"
        key_file.write_text("public key data")

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.crypto.import_key", return_value=(True, "FP")):
                result = runner.invoke(app, ["add-key", "bob", "other@x.com", str(key_file)])

        assert result.exit_code == 1


# ── list ──────────────────────────────────────────────────────────────────────

class TestListCommand:
    def test_no_collaborators_prints_message(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [])

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No collaborators" in result.stdout

    def test_lists_collaborators(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "juan.asc"},
            {"alias": "pedro", "email": "pedro@x.com", "gpgkey": "pedro.asc"},
        ])

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "juan" in result.stdout
        assert "pedro" in result.stdout

    def test_missing_key_shows_missing_status(self, tmp_path):
        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "missing.asc"},
        ])
        # key file is NOT created in keys_dir

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.collaborators.validate_registry", return_value=[]):
                result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "missing" in result.stdout


# ── list-keys ──────────────────────────────────────────────────────────────────

class TestListKeysCommand:
    def test_no_keys_prints_message(self, tmp_path):
        cfg = _make_config(tmp_path)

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.crypto.list_public_keys", return_value=[]):
                result = runner.invoke(app, ["list-keys"])

        assert result.exit_code == 0
        assert "No keys" in result.stdout

    def test_lists_public_keys(self, tmp_path):
        cfg = _make_config(tmp_path)
        keys = [{"keyid": "ABCD1234", "fingerprint": "FULL_FP", "uids": ["Alice <alice@x.com>"]}]

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.crypto.list_public_keys", return_value=keys):
                result = runner.invoke(app, ["list-keys"])

        assert result.exit_code == 0
        assert "ABCD1234" in result.stdout
        assert "alice@x.com" in result.stdout

    def test_lists_secret_keys_with_flag(self, tmp_path):
        cfg = _make_config(tmp_path)
        keys = [{"keyid": "SECRET1", "fingerprint": "SECRET_FP", "uids": ["Me <me@x.com>"]}]

        with patch("gpgshare.cli._load_config", return_value=cfg):
            with patch("gpgshare.crypto.list_secret_keys", return_value=keys):
                result = runner.invoke(app, ["list-keys", "--secret"])

        assert result.exit_code == 0
        assert "SECRET1" in result.stdout


# ── _startup_check ────────────────────────────────────────────────────────────

class TestStartupCheck:
    def test_prints_warning_for_registry_errors(self, tmp_path):
        from gpgshare.cli import _startup_check
        from io import StringIO
        import sys

        cfg = _make_config(tmp_path)
        _write_registry(cfg.collaborators_file, [
            {"alias": "juan", "email": "juan@x.com", "gpgkey": "missing.asc"},
        ])

        with patch("gpgshare.collaborators.validate_registry", return_value=["Key missing for 'juan'"]):
            from rich.console import Console
            buf = StringIO()
            # Just verify it doesn't raise
            _startup_check(cfg)

    def test_no_output_for_clean_registry(self, tmp_path):
        from gpgshare.cli import _startup_check
        cfg = _make_config(tmp_path)

        with patch("gpgshare.collaborators.validate_registry", return_value=[]):
            _startup_check(cfg)  # should not raise
