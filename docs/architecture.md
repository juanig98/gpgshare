# Architecture

## Stack

| Layer | Library |
|---|---|
| CLI | Typer + Rich |
| TUI | Textual |
| GPG wrapper | python-gnupg + subprocess |
| Collaborator registry | PyYAML |
| Configuration | python-dotenv |
| Clipboard | pyperclip |

Python 3.11+ required. Entry point: `gpgshare` → `gpgshare.cli:main`.

## Supported platforms

| Platform | Status |
|---|---|
| macOS (12+) | Supported — GPG via Homebrew or GPG Suite |
| Linux (Debian/Ubuntu, Fedora, Arch) | Supported — GPG via system package manager |

`scripts/install.sh` auto-detects the OS and installs GPG if missing. Windows is not supported.

---

## Project structure

```
gpgshare/
├── config.py           # Loads .env, exposes Config dataclass
├── crypto.py           # GPG operations (import, encrypt, decrypt, list, export)
├── collaborators.py    # CRUD on collaborators.yaml
├── cli.py              # CLI commands (Typer)
├── i18n.py             # Internationalization — t(key, **kwargs) with EN fallback
├── translations/
│   ├── en.json         # English strings (default/fallback)
│   └── es.json         # Spanish strings
├── collaborators.yaml  # Shared collaborator registry (versioned)
├── keys/               # Public key files (.asc) — versioned
├── .env                # Local config — never commit
├── .env.example        # Config template
├── run.sh              # Entry point — installs, checks key, launches TUI
├── scripts/
│   ├── install.sh      # Virtual environment and dependency setup
│   └── generate-key.sh # Interactive GPG key generation
└── tui/
    ├── app.py                    # GpgShareApp (Textual root)
    ├── screens/
    │   ├── home.py               # Main menu
    │   ├── encrypt.py            # Encrypt screen
    │   ├── decrypt.py            # Decrypt screen
    │   ├── collaborators.py      # Collaborators table + add modal
    │   └── setup.py              # Setup screen (.env, key registration, key export)
    └── widgets/
        ├── key_selector.py       # Collaborator Select widget
        └── cipher_output.py      # Read-only output panel with copy/save actions
```

---

## Core modules

### `config.py` — `Config`

Dataclass loaded from `.env`. Fields: `private_key_path`, `signer_email`, `gpg_home`, `keys_dir` (Path), `collaborators_file` (Path), `keyring_disabled` (bool), `language` (str).

Raises `EnvironmentError` if required fields are missing. Always call via `Config.load()`.

### `crypto.py`

All functions accept `gpg_home: Optional[str]` (None = use system keyring).

- `import_key(key_path, gpg_home)` → `(bool, fingerprint_or_error)` — uses `subprocess` for direct GPG control
- `export_public_key(keyid, gpg_home)` → `(bool, armored_or_error)`
- `encrypt_and_sign(content, recipient_email, signer_key_id, passphrase, gpg_home)` → `(bool, armored_or_error)`
- `decrypt_and_verify(ciphertext, passphrase, gpg_home)` → `(bool, plaintext_or_error, signer_fp_or_None)`
- `list_public_keys(gpg_home)` / `list_secret_keys(gpg_home)` → `list[dict]` with keys `fingerprint`, `uids`, `keyid`

GPG calls use `always_trust=True` and `use_agent=True`.

### `collaborators.py` — `Collaborator`

Dataclass: `alias`, `email`, `gpgkey` (filename inside `keys/`).

- `load_all(file)` → list of Collaborator
- `find_by_alias(file, alias)` — case-insensitive
- `find_by_email(file, email)`
- `add_collaborator(file, alias, email, gpgkey_filename)` — raises `ValueError` if alias or email already exists
- `validate_registry(file, keys_dir)` → `list[str]` of errors (empty = all good)

Canonical key filename: `email.lower().replace("@", "-").replace(".", "-") + ".asc"`

### `i18n.py`

- `setup_language(lang)` — call once at startup with the value from `Config.language`
- `t(key, **kwargs)` — returns the translation for `key` in the active language, falling back to English. If a key is missing in both languages, returns the key string itself (never crashes).

---

## TUI

`GpgShareApp` loads `Config` in `on_mount`, calls `setup_language()`, and stores the config in `self._cfg`. Screens access it via `getattr(self.app, "_cfg", None)`.

GPG operations run in **thread workers** (`@work(thread=True)`) to avoid blocking the event loop. Callbacks to the main thread use `self.app.call_from_thread(...)`.

### Navigation

| Screen | Key | Description |
|---|---|---|
| `HomeScreen` | `1` `2` `3` `S` `Q` | Main menu |
| `EncryptScreen` | `Ctrl+E` / `Escape` | Encrypt a message |
| `DecryptScreen` | `Ctrl+D` / `Escape` | Decrypt a message |
| `CollaboratorsScreen` | `A` `R` / `Escape` | List and add collaborators |
| `SetupScreen` | `Ctrl+S` / `Escape` | Configure .env, register and export keys |

### Widgets

- `KeySelector` — emits `KeySelector.CollaboratorSelected(alias, email)` on selection
- `CipherOutput` — hidden until `set_content(text)` is called; provides copy-to-clipboard and save-to-file actions

---

## Tests

```bash
pytest                          # all tests
pytest tests/test_crypto.py     # specific module
```

- `tests/` — unit tests for `crypto`, `collaborators`, `config`, `cli` (mocks for gnupg/subprocess and filesystem)
- `tui/tests/` — TUI tests with `pytest-asyncio`
