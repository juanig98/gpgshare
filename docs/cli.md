# CLI Reference

Activate your virtual environment first:

```bash
source .venv/bin/activate
```

---

## `gpgshare encrypt <alias>`

Encrypt and sign a message for a registered collaborator.

```bash
# Interactive — prompts for message input
gpgshare encrypt juan

# Inline message
gpgshare encrypt juan --message "Production token: abc123"

# From stdin
echo "secret message" | gpgshare encrypt juan

# Save to file
gpgshare encrypt juan -m "secret" --output message.asc

# Copy to clipboard
gpgshare encrypt juan -m "secret" --clipboard

# Prompt for passphrase (if not using gpg-agent)
gpgshare encrypt juan -m "secret" --passphrase
```

| Flag | Short | Description |
|---|---|---|
| `--message` | `-m` | Message text. Reads from stdin if omitted. |
| `--output` | `-o` | Write ciphertext to a file instead of stdout. |
| `--clipboard` | `-c` | Copy ciphertext to clipboard. |
| `--passphrase` | `-p` | Prompt for private key passphrase. |

---

## `gpgshare decrypt`

Decrypt a message using your private key.

```bash
# Paste ciphertext interactively (Ctrl+D to finish)
gpgshare decrypt

# From file
gpgshare decrypt --input message.asc

# Save plaintext to file
gpgshare decrypt --input message.asc --output result.txt

# Copy plaintext to clipboard
gpgshare decrypt --clipboard

# Prompt for passphrase
gpgshare decrypt --passphrase
```

| Flag | Short | Description |
|---|---|---|
| `--input` | `-i` | Read ciphertext from a file. |
| `--ciphertext` | `-t` | Pass ciphertext as a string argument. |
| `--output` | `-o` | Write plaintext to a file instead of stdout. |
| `--clipboard` | `-c` | Copy plaintext to clipboard. |
| `--passphrase` | `-p` | Prompt for private key passphrase. |

---

## `gpgshare add-key <alias> <email> <file.asc>`

Register a new collaborator by importing their public key.

```bash
gpgshare add-key juan juan@company.com /path/to/juan.asc
```

This copies the key to `keys/` and adds an entry to `collaborators.yaml`.
Commit both files and open a Pull Request so your team can pull the update.

---

## `gpgshare list`

List all registered collaborators and whether their key file is present.

```bash
gpgshare list
```

---

## `gpgshare list-keys`

List GPG keys available in the system keyring.

```bash
gpgshare list-keys            # public keys
gpgshare list-keys --secret   # private keys
```

---

## `gpgshare tui`

Launch the terminal user interface.

```bash
gpgshare tui
```
