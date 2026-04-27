# Configuration

gpgshare reads its settings from a `.env` file in the project root.
Copy `.env.example` to `.env` and fill in your values — or use **Setup** in the TUI.

---

## Required fields

| Variable | Description | Example |
|---|---|---|
| `GPG_PRIVATE_KEY_PATH` | Path to your exported private key file | `~/.gnupg/my-key.asc` |
| `GPG_SIGNER_EMAIL` | Email associated with your private key | `you@yourcompany.com` |

The app will refuse to start if either of these is missing.

---

## Optional fields

| Variable | Default | Description |
|---|---|---|
| `GPG_HOME` | `~/.gnupg` | Custom GPG home directory |
| `KEYS_DIR` | `./keys` | Directory where public key files are stored |
| `COLLABORATORS_FILE` | `./collaborators.yaml` | Path to the collaborators registry |
| `KEYRING_DISABLED` | `false` | If `true`, only uses `GPG_PRIVATE_KEY_PATH` and ignores the system keyring |
| `LANGUAGE` | `en` | Interface language: `en` (English) or `es` (Spanish) |

---

## Changing settings from the TUI

Open the TUI and press **S** (Setup). The form pre-fills with your current values.
After saving, the app returns to the home screen with the new settings active.

> **Language change**: requires a restart to take effect. The TUI will remind you.

---

## Security

- `.env` is listed in `.gitignore`. **Never commit it.**
- Your private key file should also never be committed.
- Only the files in `keys/` (public keys) and `collaborators.yaml` belong in version control.
