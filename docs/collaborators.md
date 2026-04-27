# Managing Collaborators

Collaborators are teammates who can receive encrypted messages from you (or send them to you).
The registry lives in `collaborators.yaml` and their public keys in `keys/` — both are committed to the repository.

---

## Typical flow

```
1. Juan generates a GPG key and exports his public key.
2. Juan registers himself in the project (CLI or TUI Setup).
3. Juan commits collaborators.yaml + keys/juan-company-com.asc and opens a Pull Request.
4. After the PR is merged, everyone on the team can encrypt messages for Juan.
```

---

## Register yourself (recommended: TUI)

```bash
gpgshare tui
# Press S → "Register my public key"
# Select your key from the list and enter an alias
```

The TUI exports your public key, writes it to `keys/`, and adds you to `collaborators.yaml` automatically.

---

## Register yourself (CLI)

```bash
# Export your public key
gpg --armor --export you@yourcompany.com > /tmp/your-key.asc

# Register it
gpgshare add-key yourAlias you@yourcompany.com /tmp/your-key.asc
```

---

## Register a teammate

Ask them to export their public key:

```bash
gpg --armor --export them@company.com > their-key.asc
```

Then register it:

```bash
gpgshare add-key theirAlias them@company.com their-key.asc
```

---

## Commit and open a Pull Request

After adding a collaborator, commit the changes:

```bash
git add collaborators.yaml keys/
git commit -m "chore: add collaborator <alias>"
git push
# Open a Pull Request
```

Once merged, everyone who pulls the repo can encrypt messages for the new collaborator.

---

## Key file naming

Key files are named automatically using the email address:

```
you@yourcompany.com  →  keys/you-yourcompany-com.asc
```

---

## Verify registry integrity

```bash
gpgshare list
```

A `✗ missing` status means the `.asc` file referenced in `collaborators.yaml` is not present in `keys/`.
This usually means someone added an entry to the YAML without committing the key file.
