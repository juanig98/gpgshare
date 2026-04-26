"""
Tests for gpgshare.crypto — GPG operations.
All calls to gnupg.GPG are mocked so no real GPG binary or keyring is needed.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def _make_gpg_mock():
    """Return a fresh MagicMock shaped like gnupg.GPG."""
    return MagicMock()


# ── import_key ────────────────────────────────────────────────────────────────

class TestImportKey:
    def test_success_returns_fingerprint(self, tmp_path):
        key_file = tmp_path / "key.asc"
        key_file.write_text("-----BEGIN PGP PUBLIC KEY BLOCK-----\nfake\n-----END PGP PUBLIC KEY BLOCK-----\n")

        import_result = MagicMock()
        import_result.count = 1
        import_result.fingerprints = ["ABCDEF1234567890"]

        gpg_mock = _make_gpg_mock()
        gpg_mock.import_keys.return_value = import_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, fp = crypto.import_key(str(key_file))

        assert ok is True
        assert fp == "ABCDEF1234567890"

    def test_failure_when_no_keys_imported(self, tmp_path):
        key_file = tmp_path / "key.asc"
        key_file.write_text("not a valid key")

        import_result = MagicMock()
        import_result.count = 0
        import_result.fingerprints = []

        gpg_mock = _make_gpg_mock()
        gpg_mock.import_keys.return_value = import_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, msg = crypto.import_key(str(key_file))

        assert ok is False
        assert "No keys were imported" in msg

    def test_uses_unknown_fingerprint_when_list_empty(self, tmp_path):
        key_file = tmp_path / "key.asc"
        key_file.write_text("key data")

        import_result = MagicMock()
        import_result.count = 1
        import_result.fingerprints = []

        gpg_mock = _make_gpg_mock()
        gpg_mock.import_keys.return_value = import_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, fp = crypto.import_key(str(key_file))

        assert ok is True
        assert fp == "unknown"

    def test_passes_gpg_home_to_constructor(self, tmp_path):
        key_file = tmp_path / "key.asc"
        key_file.write_text("key data")

        import_result = MagicMock()
        import_result.count = 1
        import_result.fingerprints = ["FP"]

        gpg_mock = _make_gpg_mock()
        gpg_mock.import_keys.return_value = import_result

        with patch("gnupg.GPG", return_value=gpg_mock) as gpg_cls:
            from gpgshare import crypto
            crypto.import_key(str(key_file), gpg_home="/custom/home")
            call_kwargs = gpg_cls.call_args[1]
            assert call_kwargs.get("gnupghome") == "/custom/home"


# ── encrypt_and_sign ──────────────────────────────────────────────────────────

class TestEncryptAndSign:
    def test_success_returns_ciphertext(self):
        encrypt_result = MagicMock()
        encrypt_result.ok = True
        encrypt_result.__str__ = lambda self: "-----BEGIN PGP MESSAGE-----\ndata\n-----END PGP MESSAGE-----\n"

        gpg_mock = _make_gpg_mock()
        gpg_mock.encrypt.return_value = encrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, ciphertext = crypto.encrypt_and_sign(
                content="secret",
                recipient_email="recipient@example.com",
                signer_key_id="signer@example.com",
            )

        assert ok is True
        assert "BEGIN PGP MESSAGE" in ciphertext

    def test_failure_returns_error_message(self):
        encrypt_result = MagicMock()
        encrypt_result.ok = False
        encrypt_result.status = "invalid recipient"

        gpg_mock = _make_gpg_mock()
        gpg_mock.encrypt.return_value = encrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, msg = crypto.encrypt_and_sign(
                content="secret",
                recipient_email="nobody@example.com",
                signer_key_id="signer@example.com",
            )

        assert ok is False
        assert "invalid recipient" in msg

    def test_passes_correct_params_to_gpg(self):
        encrypt_result = MagicMock()
        encrypt_result.ok = True
        encrypt_result.__str__ = lambda self: "cipher"

        gpg_mock = _make_gpg_mock()
        gpg_mock.encrypt.return_value = encrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            crypto.encrypt_and_sign(
                content="msg",
                recipient_email="bob@example.com",
                signer_key_id="alice@example.com",
                passphrase="secret123",
            )

        call_kwargs = gpg_mock.encrypt.call_args
        assert call_kwargs[0][0] == "msg"
        assert "bob@example.com" in call_kwargs[1]["recipients"]
        assert call_kwargs[1]["sign"] == "alice@example.com"
        assert call_kwargs[1]["passphrase"] == "secret123"
        assert call_kwargs[1]["armor"] is True


# ── decrypt_and_verify ────────────────────────────────────────────────────────

class TestDecryptAndVerify:
    def test_success_with_signer_fingerprint(self):
        decrypt_result = MagicMock()
        decrypt_result.ok = True
        decrypt_result.fingerprint = "SIGNER_FP_ABCDEF"
        decrypt_result.__str__ = lambda self: "plain text"

        gpg_mock = _make_gpg_mock()
        gpg_mock.decrypt.return_value = decrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, plaintext, signer = crypto.decrypt_and_verify("cipher data")

        assert ok is True
        assert plaintext == "plain text"
        assert signer == "SIGNER_FP_ABCDEF"

    def test_success_without_signature(self):
        decrypt_result = MagicMock()
        decrypt_result.ok = True
        decrypt_result.fingerprint = None
        decrypt_result.__str__ = lambda self: "plain text"

        gpg_mock = _make_gpg_mock()
        gpg_mock.decrypt.return_value = decrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, plaintext, signer = crypto.decrypt_and_verify("cipher data")

        assert ok is True
        assert signer is None

    def test_failure_returns_error(self):
        decrypt_result = MagicMock()
        decrypt_result.ok = False
        decrypt_result.status = "bad passphrase"

        gpg_mock = _make_gpg_mock()
        gpg_mock.decrypt.return_value = decrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            ok, msg, signer = crypto.decrypt_and_verify("bad cipher")

        assert ok is False
        assert "bad passphrase" in msg
        assert signer is None

    def test_passes_passphrase_to_gpg(self):
        decrypt_result = MagicMock()
        decrypt_result.ok = True
        decrypt_result.fingerprint = None
        decrypt_result.__str__ = lambda self: "plain"

        gpg_mock = _make_gpg_mock()
        gpg_mock.decrypt.return_value = decrypt_result

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            crypto.decrypt_and_verify("cipher", passphrase="pw")

        call_kwargs = gpg_mock.decrypt.call_args[1]
        assert call_kwargs["passphrase"] == "pw"


# ── list_secret_keys / list_public_keys ───────────────────────────────────────

class TestListKeys:
    def _make_key_entry(self, keyid, fingerprint, uids):
        return {"keyid": keyid, "fingerprint": fingerprint, "uids": uids, "extra": "ignored"}

    def test_list_secret_keys_returns_expected_fields(self):
        gpg_mock = _make_gpg_mock()
        gpg_mock.list_keys.return_value = [
            self._make_key_entry("ABC123", "FULL_FP_1", ["Alice <alice@x.com>"]),
            self._make_key_entry("DEF456", "FULL_FP_2", ["Bob <bob@x.com>"]),
        ]

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            keys = crypto.list_secret_keys()

        gpg_mock.list_keys.assert_called_once_with(secret=True)
        assert len(keys) == 2
        assert keys[0] == {"keyid": "ABC123", "fingerprint": "FULL_FP_1", "uids": ["Alice <alice@x.com>"]}

    def test_list_public_keys_returns_expected_fields(self):
        gpg_mock = _make_gpg_mock()
        gpg_mock.list_keys.return_value = [
            self._make_key_entry("PUB1", "PUB_FP_1", ["Charlie <c@x.com>"]),
        ]

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            keys = crypto.list_public_keys()

        gpg_mock.list_keys.assert_called_once_with()
        assert len(keys) == 1
        assert set(keys[0].keys()) == {"keyid", "fingerprint", "uids"}

    def test_list_secret_keys_empty(self):
        gpg_mock = _make_gpg_mock()
        gpg_mock.list_keys.return_value = []

        with patch("gnupg.GPG", return_value=gpg_mock):
            from gpgshare import crypto
            assert crypto.list_secret_keys() == []
