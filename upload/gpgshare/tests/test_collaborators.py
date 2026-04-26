"""
Tests for gpgshare.collaborators — registry CRUD and validation.
"""

import pytest
import yaml
from pathlib import Path

from gpgshare.collaborators import (
    load_all,
    find_by_alias,
    find_by_email,
    add_collaborator,
    validate_registry,
    Collaborator,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def registry(tmp_path) -> Path:
    """Write a minimal collaborators.yaml and return its path."""
    data = [
        {"alias": "juan", "email": "juan@empresa.com", "gpgkey": "juan-empresa-com.asc"},
        {"alias": "gabriel", "email": "gabriel@empresa.com", "gpgkey": "gabriel-empresa-com.asc"},
    ]
    f = tmp_path / "collaborators.yaml"
    f.write_text(yaml.dump(data))
    return f


@pytest.fixture
def keys_dir(tmp_path, registry) -> Path:
    """Create a keys/ dir with one present and one missing key."""
    d = tmp_path / "keys"
    d.mkdir()
    (d / "juan-empresa-com.asc").write_text("fake key")
    # gabriel's key intentionally absent
    return d


# ── load_all ─────────────────────────────────────────────────────────────────

class TestLoadAll:
    def test_returns_collaborators(self, registry):
        result = load_all(registry)
        assert len(result) == 2
        assert all(isinstance(c, Collaborator) for c in result)

    def test_returns_empty_for_missing_file(self, tmp_path):
        result = load_all(tmp_path / "nonexistent.yaml")
        assert result == []

    def test_returns_empty_for_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert load_all(f) == []

    def test_fields_are_correct(self, registry):
        collaborators = load_all(registry)
        juan = next(c for c in collaborators if c.alias == "juan")
        assert juan.email == "juan@empresa.com"
        assert juan.gpgkey == "juan-empresa-com.asc"


# ── find_by_alias ─────────────────────────────────────────────────────────────

class TestFindByAlias:
    def test_finds_existing(self, registry):
        c = find_by_alias(registry, "juan")
        assert c is not None
        assert c.email == "juan@empresa.com"

    def test_returns_none_for_unknown(self, registry):
        assert find_by_alias(registry, "nobody") is None

    def test_case_insensitive(self, registry):
        assert find_by_alias(registry, "JUAN") is not None
        assert find_by_alias(registry, "Juan") is not None


# ── find_by_email ─────────────────────────────────────────────────────────────

class TestFindByEmail:
    def test_finds_existing(self, registry):
        c = find_by_email(registry, "juan@empresa.com")
        assert c is not None
        assert c.alias == "juan"

    def test_returns_none_for_unknown(self, registry):
        assert find_by_email(registry, "unknown@empresa.com") is None

    def test_case_insensitive(self, registry):
        assert find_by_email(registry, "JUAN@EMPRESA.COM") is not None


# ── add_collaborator ──────────────────────────────────────────────────────────

class TestAddCollaborator:
    def test_adds_new_collaborator(self, tmp_path):
        f = tmp_path / "collaborators.yaml"
        add_collaborator(f, "pepe", "pepe@example.com", "pepe-example-com.asc")
        result = load_all(f)
        assert len(result) == 1
        assert result[0].alias == "pepe"
        assert result[0].email == "pepe@example.com"
        assert result[0].gpgkey == "pepe-example-com.asc"

    def test_creates_file_if_missing(self, tmp_path):
        f = tmp_path / "new.yaml"
        assert not f.exists()
        add_collaborator(f, "alice", "alice@x.com", "alice.asc")
        assert f.exists()

    def test_appends_to_existing(self, registry):
        add_collaborator(registry, "pepe", "pepe@example.com", "pepe.asc")
        assert len(load_all(registry)) == 3

    def test_duplicate_alias_raises(self, registry):
        with pytest.raises(ValueError, match="(?i)alias.*already exists"):
            add_collaborator(registry, "juan", "other@example.com", "other.asc")

    def test_duplicate_email_raises(self, registry):
        with pytest.raises(ValueError, match="[Ee]mail.*already exists"):
            add_collaborator(registry, "otheralias", "juan@empresa.com", "other.asc")

    def test_duplicate_alias_case_insensitive(self, registry):
        with pytest.raises(ValueError):
            add_collaborator(registry, "JUAN", "other@example.com", "other.asc")


# ── validate_registry ─────────────────────────────────────────────────────────

class TestValidateRegistry:
    def test_no_errors_when_all_keys_present(self, tmp_path):
        f = tmp_path / "collaborators.yaml"
        keys = tmp_path / "keys"
        keys.mkdir()
        (keys / "juan.asc").write_text("key")
        add_collaborator(f, "juan", "juan@x.com", "juan.asc")

        errors = validate_registry(f, keys)
        assert errors == []

    def test_error_for_missing_key_file(self, registry, tmp_path):
        keys = tmp_path / "keys"
        keys.mkdir()
        # No key files created — both are missing
        errors = validate_registry(registry, keys)
        assert len(errors) == 2

    def test_partial_missing(self, registry, keys_dir):
        # keys_dir has juan's key but not gabriel's
        errors = validate_registry(registry, keys_dir)
        assert len(errors) == 1
        assert "gabriel" in errors[0]

    def test_error_for_missing_collaborators_file(self, tmp_path):
        errors = validate_registry(tmp_path / "none.yaml", tmp_path / "keys")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_no_errors_for_empty_registry(self, tmp_path):
        f = tmp_path / "collaborators.yaml"
        f.write_text("")
        errors = validate_registry(f, tmp_path / "keys")
        assert errors == []
