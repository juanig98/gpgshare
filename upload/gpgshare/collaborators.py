"""
Collaborators registry.
Reads and writes collaborators.yaml — the shared directory of public keys.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Collaborator:
    alias: str
    email: str
    gpgkey: str          # filename inside keys/ dir (e.g. "juan-correo-com.asc")


def _load_raw(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r") as f:
        data = yaml.safe_load(f) or []
    return data


def _save_raw(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_all(collaborators_file: Path) -> list[Collaborator]:
    """Load all collaborators from the YAML registry."""
    raw = _load_raw(collaborators_file)
    return [Collaborator(**entry) for entry in raw]


def find_by_alias(collaborators_file: Path, alias: str) -> Optional[Collaborator]:
    """Find a collaborator by alias (case-insensitive)."""
    for c in load_all(collaborators_file):
        if c.alias.lower() == alias.lower():
            return c
    return None


def find_by_email(collaborators_file: Path, email: str) -> Optional[Collaborator]:
    """Find a collaborator by email."""
    for c in load_all(collaborators_file):
        if c.email.lower() == email.lower():
            return c
    return None


def add_collaborator(
    collaborators_file: Path,
    alias: str,
    email: str,
    gpgkey_filename: str,
) -> None:
    """
    Add a new collaborator to the YAML registry.
    Raises ValueError if alias or email already exists.
    """
    raw = _load_raw(collaborators_file)

    for entry in raw:
        if entry.get("alias", "").lower() == alias.lower():
            raise ValueError(f"Alias '{alias}' already exists in the registry.")
        if entry.get("email", "").lower() == email.lower():
            raise ValueError(f"Email '{email}' already exists in the registry.")

    raw.append({"alias": alias, "email": email, "gpgkey": gpgkey_filename})
    _save_raw(collaborators_file, raw)


def validate_registry(collaborators_file: Path, keys_dir: Path) -> list[str]:
    """
    Integrity check: verify every gpgkey file referenced in the YAML exists.
    Returns a list of error strings (empty = all good).
    """
    errors = []
    if not collaborators_file.exists():
        errors.append(f"Collaborators file not found: {collaborators_file}")
        return errors

    for c in load_all(collaborators_file):
        key_path = keys_dir / c.gpgkey
        if not key_path.exists():
            errors.append(
                f"Key file missing for '{c.alias}' ({c.email}): {key_path}"
            )
    return errors