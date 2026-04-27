"""
Configuration loader.
Reads .env and exposes typed settings for the rest of the app.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass
class Config:
    private_key_path: str
    signer_email: str
    gpg_home: str
    keys_dir: Path
    collaborators_file: Path
    keyring_disabled: bool
    language: str

    @classmethod
    def load(cls) -> "Config":
        private_key_path = os.getenv("GPG_PRIVATE_KEY_PATH", "")
        signer_email = os.getenv("GPG_SIGNER_EMAIL", "")
        gpg_home = os.getenv("GPG_HOME", "")
        keys_dir = Path(os.getenv("KEYS_DIR", str(_PROJECT_ROOT / "keys")))
        collaborators_file = Path(
            os.getenv("COLLABORATORS_FILE", str(_PROJECT_ROOT / "collaborators.yaml"))
        )
        keyring_disabled = os.getenv("KEYRING_DISABLED", "false").strip().lower() == "true"
        language = os.getenv("LANGUAGE", "en").strip().lower()

        errors = []
        if not private_key_path:
            errors.append("GPG_PRIVATE_KEY_PATH is not set in .env")
        if not signer_email:
            errors.append("GPG_SIGNER_EMAIL is not set in .env")
        if errors:
            raise EnvironmentError(
                "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        return cls(
            private_key_path=str(Path(private_key_path).expanduser()),
            signer_email=signer_email,
            gpg_home=str(Path(gpg_home).expanduser()) if gpg_home else None,
            keys_dir=keys_dir.expanduser(),
            collaborators_file=collaborators_file.expanduser(),
            keyring_disabled=keyring_disabled,
            language=language,
        )