"""
GPG cryptographic operations.
Wraps python-gnupg delegating all crypto to the system GPG binary.
"""

import gnupg
import platform
import subprocess
from pathlib import Path
from typing import Optional

_IS_MACOS = platform.system() == "Darwin"

# GPG stderr keywords that indicate a passphrase/agent problem.
_PASSPHRASE_KEYWORDS = (
    "bad passphrase",
    "no passphrase",
    "passphrase missing",
    "no pinentry",
    "pinentry",
    "inappropriate ioctl",
    "gpg-agent",
    "operation cancelled",
    "need_passphrase"
)


def _passphrase_hint(stderr: str, status: str) -> str:
    """Return a user-facing hint when a GPG error looks passphrase-related."""
    combined = f"{stderr} {status}".lower()
    if not any(kw in combined for kw in _PASSPHRASE_KEYWORDS):
        return ""
    try:
        from gpgshare.i18n import t
        key = "crypto.hint.passphrase_macos" if _IS_MACOS else "crypto.hint.passphrase_linux"
        return f"\n{t(key)}"
    except Exception:
        return ""


def _gpg(gpg_home: Optional[str] = None) -> gnupg.GPG:
    """Return a GPG instance, optionally with a custom keyring home."""
    kwargs = {"use_agent": True}
    if gpg_home:
        kwargs["gnupghome"] = gpg_home
    return gnupg.GPG(**kwargs)


def import_key(key_path: str, gpg_home: Optional[str] = None) -> tuple[bool, str]:
    """
    Import a public (or private) key from a file into the GPG keyring.
    Returns (success, fingerprint_or_error).
    """
    path = Path(key_path).expanduser().resolve()
    if not path.exists():
        return False, f"Key file not found: {path}"

    cmd = ["gpg", "--batch", "--import", str(path)]
    if gpg_home:
        cmd = ["gpg", "--homedir", str(Path(gpg_home).expanduser()), "--batch", "--import", str(path)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, proc.stderr.strip() or "Import failed with no output."

    # Extract fingerprint from stderr (gpg prints import info there)
    for line in proc.stderr.splitlines():
        if "key" in line.lower() and ":" in line:
            parts = line.split(":")
            for part in parts:
                stripped = part.strip().split()[-1] if part.strip() else ""
                if len(stripped) >= 16 and all(c in "0123456789ABCDEFabcdef" for c in stripped):
                    return True, stripped

    return True, "imported"


def encrypt_and_sign(
    content: str,
    recipient_emails: list[str],
    signer_key_id: str,
    passphrase: Optional[str] = None,
    gpg_home: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Encrypt `content` for `recipient_emails` and sign with `signer_key_id`.
    Returns (success, ascii_armored_ciphertext_or_error).
    """
    gpg = _gpg(gpg_home)

    # Use loopback when a passphrase is provided, or on macOS where gpg-agent
    # cannot open a pinentry dialog without pinentry-mac installed.
    use_loopback = passphrase is not None or _IS_MACOS
    extra: list[str] = ["--pinentry-mode", "loopback"] if use_loopback else []
    result = gpg.encrypt(
        content,
        recipients=recipient_emails,
        sign=signer_key_id,
        passphrase=passphrase,
        armor=True,
        always_trust=True,
        extra_args=extra,
    )

    if not result.ok:
        stderr = result.stderr.strip() if result.stderr else ""
        status = result.status or ""
        hint = _passphrase_hint(stderr, status)
        return False, f"Encryption failed: {stderr or status}{hint}"

    return True, str(result)


def decrypt_and_verify(
    ciphertext: str,
    passphrase: Optional[str] = None,
    gpg_home: Optional[str] = None,
) -> tuple[bool, str, Optional[str]]:
    """
    Decrypt `ciphertext` using the available private key.
    Returns (success, plaintext_or_error, signer_fingerprint_or_None).
    """
    gpg = _gpg(gpg_home)

    use_loopback = passphrase is not None or _IS_MACOS
    extra = ["--pinentry-mode", "loopback"] if use_loopback else []
    result = gpg.decrypt(
        ciphertext,
        passphrase=passphrase,
        always_trust=True,
        extra_args=extra,
    )

    if not result.ok:
        stderr = result.stderr.strip() if result.stderr else ""
        status = result.status or ""
        hint = _passphrase_hint(stderr, status)
        return False, f"Decryption failed: {stderr or status}{hint}", None

    signer = result.fingerprint if result.fingerprint else None
    return True, str(result), signer


def list_secret_keys(gpg_home: Optional[str] = None) -> list[dict]:
    """Return a list of available private keys in the keyring."""
    gpg = _gpg(gpg_home)
    keys = gpg.list_keys(secret=True)
    return [
        {
            "fingerprint": k["fingerprint"],
            "uids": k["uids"],
            "keyid": k["keyid"],
        }
        for k in keys
    ]


def export_public_key(keyid: str, gpg_home: Optional[str] = None) -> tuple[bool, str]:
    """
    Export the ASCII-armored public key for `keyid`.
    Returns (success, armored_key_or_error).
    """
    gpg = _gpg(gpg_home)
    armored = gpg.export_keys(keyid)
    if not armored:
        return False, f"No public key found for keyid: {keyid}"
    return True, armored


def list_public_keys(gpg_home: Optional[str] = None) -> list[dict]:
    """Return a list of available public keys in the keyring."""
    gpg = _gpg(gpg_home)
    keys = gpg.list_keys()
    return [
        {
            "fingerprint": k["fingerprint"],
            "uids": k["uids"],
            "keyid": k["keyid"],
        }
        for k in keys
    ]