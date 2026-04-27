# GPG Setup

## Do I need a GPG key?

Yes. gpgshare uses GPG to encrypt and sign messages. You need at least one private key.

---

## Generate a new GPG key

```bash
gpg --full-generate-key
```

Follow the prompts:

1. **Key type** → choose `ECC (sign and encrypt)` or `RSA and RSA`
2. **Key size / curve** → the default is fine
3. **Expiration** → your choice (`0` = no expiration)
4. **Name and email** → use your real name and work email

Verify it was created:

```bash
gpg --list-secret-keys
```

---

## Export your private key (required for `.env`)

```bash
gpg --armor --export-secret-keys you@yourcompany.com > ~/my-private-key.asc
```

Set the path in `.env`:

```env
GPG_PRIVATE_KEY_PATH=~/my-private-key.asc
GPG_SIGNER_EMAIL=you@yourcompany.com
```

---

## Export your public key (to share with teammates)

```bash
gpg --armor --export you@yourcompany.com > /tmp/your-key.asc
```

Send this file to your teammate. They register it with:

```bash
gpgshare add-key yourAlias you@yourcompany.com /tmp/your-key.asc
```

---

## Multiple identities on the same machine

You can have several GPG keys in the same keyring — useful for testing or multiple accounts.

```bash
# Generate a second key
gpg --full-generate-key

# Export its private key
gpg --armor --export-secret-keys other@company.com > ~/.gnupg/other-private-key.asc

# Export its public key and register it as a collaborator
gpg --armor --export other@company.com > /tmp/other.asc
gpgshare add-key other other@company.com /tmp/other.asc
```

To use gpgshare with that identity, update `.env`:

```env
GPG_PRIVATE_KEY_PATH=~/.gnupg/other-private-key.asc
GPG_SIGNER_EMAIL=other@company.com
```

---

## Using gpg-agent (recommended)

If you use **GPG Suite** (macOS) or have `gpg-agent` running, gpgshare will automatically use it.
You won't need to enter your passphrase every time.

To check if the agent is running:

```bash
gpg-agent --daemon   # start it if needed
```
