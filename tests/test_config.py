"""
Tests for gpgshare.config — Config.load()
"""

import pytest
from pathlib import Path
from unittest.mock import patch


def _load_with_env(**overrides):
    """Helper: load Config patching os.environ.

    Pass a key with value None to remove it from the environment.
    Other keys are set to the given string value.
    """
    import os
    import importlib
    import gpgshare.config as cfg_module

    base = {
        "GPG_PRIVATE_KEY_PATH": "/home/user/private.asc",
        "GPG_SIGNER_EMAIL": "user@example.com",
        "GPG_HOME": "",
    }
    base.update(overrides)

    # Build the patched env: remove keys set to None, set the rest
    keys_to_remove = [k for k, v in base.items() if v is None]
    keys_to_set = {k: v for k, v in base.items() if v is not None}

    env_copy = {k: v for k, v in os.environ.items() if k not in keys_to_remove}
    env_copy.update(keys_to_set)

    with patch.dict("os.environ", env_copy, clear=True):
        importlib.reload(cfg_module)
        return cfg_module.Config.load()


class TestConfigLoad:
    def test_loads_required_fields(self):
        cfg = _load_with_env()
        assert cfg.private_key_path == "/home/user/private.asc"
        assert cfg.signer_email == "user@example.com"

    def test_missing_private_key_path_raises(self):
        with pytest.raises(EnvironmentError, match="GPG_PRIVATE_KEY_PATH"):
            _load_with_env(GPG_PRIVATE_KEY_PATH="")

    def test_missing_signer_email_raises(self):
        with pytest.raises(EnvironmentError, match="GPG_SIGNER_EMAIL"):
            _load_with_env(GPG_SIGNER_EMAIL="")

    def test_missing_both_raises_with_both_messages(self):
        with pytest.raises(EnvironmentError) as exc_info:
            _load_with_env(GPG_PRIVATE_KEY_PATH="", GPG_SIGNER_EMAIL="")
        msg = str(exc_info.value)
        assert "GPG_PRIVATE_KEY_PATH" in msg
        assert "GPG_SIGNER_EMAIL" in msg

    def test_gpg_home_empty_string_becomes_none(self):
        cfg = _load_with_env(GPG_HOME="")
        assert cfg.gpg_home is None

    def test_gpg_home_set(self):
        cfg = _load_with_env(GPG_HOME="/custom/gnupg")
        assert cfg.gpg_home == "/custom/gnupg"

    def test_default_keys_dir_is_inside_project(self):
        # Remove KEYS_DIR so the code falls back to the built-in default
        cfg = _load_with_env(KEYS_DIR=None)
        assert cfg.keys_dir.name == "keys"

    def test_custom_keys_dir(self, tmp_path):
        cfg = _load_with_env(KEYS_DIR=str(tmp_path / "mykeys"))
        assert cfg.keys_dir == tmp_path / "mykeys"

    def test_default_collaborators_file(self):
        # Remove COLLABORATORS_FILE so the code falls back to the built-in default
        cfg = _load_with_env(COLLABORATORS_FILE=None)
        assert cfg.collaborators_file.name == "collaborators.yaml"

    def test_custom_collaborators_file(self, tmp_path):
        f = tmp_path / "team.yaml"
        cfg = _load_with_env(COLLABORATORS_FILE=str(f))
        assert cfg.collaborators_file == f
