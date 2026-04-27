# gpgshare

Encrypt and sign messages for your teammates using GPG — in one step.
Paste the result anywhere: Slack, email, GitHub comments.

Available as a **CLI** and a **terminal UI (TUI)**.

---

## Getting Started

### 1. Install

```bash
git clone https://github.com/juanig98/gpgshare.git
cd gpgshare
bash install.sh
```

The installer checks your Python version, sets up a virtual environment, installs dependencies, and copies the configuration template.

### 2. Configure

Open the `.env` file that was just created and fill in two required fields:

```env
GPG_PRIVATE_KEY_PATH=~/.gnupg/my-private-key.asc
GPG_SIGNER_EMAIL=you@yourcompany.com
```

> **Don't have a GPG key yet?** See [GPG Setup →](docs/gpg-setup.md)

### 3. Register yourself as a collaborator

Before anyone can send you an encrypted message, they need your public key.
Run this once to export it and register it in the project:

```bash
source .venv/bin/activate
gpgshare tui   # then go to Setup → Register my public key
```

Or via CLI:

```bash
gpg --armor --export you@yourcompany.com > /tmp/your-key.asc
gpgshare add-key yourAlias you@yourcompany.com /tmp/your-key.asc
```

Then commit `collaborators.yaml` and the new `.asc` file in `keys/` and open a Pull Request so your teammates can pull the update.

### 4. Send an encrypted message

```bash
# Encrypt a message for a teammate (replace "juan" with their alias)
gpgshare encrypt juan --message "Production token: abc123" --clipboard
```

Paste the output wherever you like. Only Juan can read it.

### 5. Decrypt a message

```bash
# Paste the ciphertext when prompted
gpgshare decrypt
```

---

## Terminal UI

```bash
gpgshare tui
```

The TUI provides the same features with a guided interface — no commands to remember.
Use **Setup** (key `S`) to configure your environment and manage your GPG keys.

---

## Language

gpgshare supports **English** (default) and **Spanish**.
Set the language in `.env`:

```env
LANGUAGE=es   # or: en
```

Or change it from the TUI Setup screen. A restart is required to apply the change.

---

## Documentation

| Topic | Link |
|---|---|
| CLI command reference | [docs/cli.md](docs/cli.md) |
| Configuration (.env) | [docs/configuration.md](docs/configuration.md) |
| Adding collaborators | [docs/collaborators.md](docs/collaborators.md) |
| GPG key setup | [docs/gpg-setup.md](docs/gpg-setup.md) |
| Architecture & code | [docs/architecture.md](docs/architecture.md) |

---

## Security notes

- Messages are **encrypted and signed** in one step. Recipients can verify who sent them.
- Never commit your `.env` or private key — both are in `.gitignore`.
- Only public keys live in the repository (`keys/`). Private keys never leave your machine.
