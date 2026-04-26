"""
CLI entrypoint — built with Typer + Rich.
Designed to grow into a TUI (Textual) without restructuring the core logic.
"""

import sys
import shutil
import getpass
from pathlib import Path
from typing import Optional

import typer
import pyperclip
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from gpgshare.config import Config
from gpgshare.collaborators import (
    load_all, find_by_alias, add_collaborator, validate_registry
)
from gpgshare import crypto

app = typer.Typer(
    name="gpgshare",
    help="Encrypt and decrypt messages using GPG keys among collaborators.",
    add_completion=True,
)
console = Console()
err_console = Console(stderr=True, style="bold red")


# ---------------------------------------------------------------------------
# Startup integrity check (runs on every command)
# ---------------------------------------------------------------------------

def _startup_check(cfg: Config) -> None:
    """Validate config and key registry on startup. Abort on critical errors."""
    errors = validate_registry(cfg.collaborators_file, cfg.keys_dir)
    if errors:
        err_console.print("[bold red]⚠ Registry integrity errors:[/bold red]")
        for e in errors:
            err_console.print(f"  [red]• {e}[/red]")
        console.print(
            "[yellow]Some collaborator keys are missing from disk. "
            "Run [bold]gpgshare list[/bold] to review.[/yellow]\n"
        )


def _load_config() -> Config:
    try:
        return Config.load()
    except EnvironmentError as e:
        err_console.print(str(e))
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def encrypt(
    recipient: str = typer.Argument(..., help="Alias of the recipient collaborator."),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Text to encrypt. If omitted, reads from stdin."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write ciphertext to this file instead of stdout."
    ),
    clipboard: bool = typer.Option(
        False, "--clipboard", "-c", help="Copy ciphertext to clipboard."
    ),
    passphrase: bool = typer.Option(
        False, "--passphrase", "-p",
        help="Prompt for private key passphrase (if not using gpg-agent)."
    ),
):
    """Encrypt and sign a message for a collaborator."""
    cfg = _load_config()
    _startup_check(cfg)

    # Resolve recipient
    collaborator = find_by_alias(cfg.collaborators_file, recipient)
    if not collaborator:
        err_console.print(f"Collaborator '[bold]{recipient}[/bold]' not found in registry.")
        raise typer.Exit(1)

    # Get message
    if message is None:
        if sys.stdin.isatty():
            console.print("[dim]Enter message (Ctrl+D to finish):[/dim]")
        message = sys.stdin.read()

    if not message.strip():
        err_console.print("Empty message. Nothing to encrypt.")
        raise typer.Exit(1)

    # Ensure recipient's public key is imported
    key_path = cfg.keys_dir / collaborator.gpgkey
    ok, result = crypto.import_key(str(key_path), cfg.gpg_home)
    if not ok:
        err_console.print(f"Could not import recipient key: {result}")
        raise typer.Exit(1)

    # Ensure own private key is imported
    ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
    if not ok:
        err_console.print(f"Could not import private key: {result}")
        raise typer.Exit(1)

    pw = getpass.getpass("Private key passphrase (leave empty for gpg-agent): ") if passphrase else None

    console.print(
        f"[dim]Encrypting for [bold]{collaborator.alias}[/bold] "
        f"<{collaborator.email}> and signing as [bold]{cfg.signer_email}[/bold]…[/dim]"
    )

    ok, ciphertext = crypto.encrypt_and_sign(
        content=message,
        recipient_email=collaborator.email,
        signer_key_id=cfg.signer_email,
        passphrase=pw,
        gpg_home=cfg.gpg_home,
    )

    if not ok:
        err_console.print(ciphertext)  # ciphertext contains the error here
        raise typer.Exit(1)

    # Output
    if output:
        output.write_text(ciphertext)
        console.print(f"[green]✓ Ciphertext written to [bold]{output}[/bold][/green]")
    else:
        console.print(Panel(ciphertext, title="[bold green]Encrypted message[/bold green]", box=box.ROUNDED))

    if clipboard:
        pyperclip.copy(ciphertext)
        console.print("[green]✓ Copied to clipboard.[/green]")


@app.command()
def decrypt(
    ciphertext: Optional[str] = typer.Option(
        None, "--ciphertext", "-t", help="Armored ciphertext string. If omitted, reads from stdin."
    ),
    input_file: Optional[Path] = typer.Option(
        None, "--input", "-i", help="Read ciphertext from this file."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write plaintext to this file instead of stdout."
    ),
    clipboard: bool = typer.Option(
        False, "--clipboard", "-c", help="Copy plaintext to clipboard."
    ),
    passphrase: bool = typer.Option(
        False, "--passphrase", "-p",
        help="Prompt for private key passphrase (if not using gpg-agent)."
    ),
):
    """Decrypt a message using your private key."""
    cfg = _load_config()
    _startup_check(cfg)

    # Ensure own private key is imported
    ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
    if not ok:
        err_console.print(f"Could not import private key: {result}")
        raise typer.Exit(1)

    # Get ciphertext
    if input_file:
        ciphertext = input_file.read_text()
    elif ciphertext is None:
        if sys.stdin.isatty():
            console.print("[dim]Paste ciphertext (Ctrl+D to finish):[/dim]")
        ciphertext = sys.stdin.read()

    if not ciphertext or not ciphertext.strip():
        err_console.print("No ciphertext provided.")
        raise typer.Exit(1)

    pw = getpass.getpass("Private key passphrase (leave empty for gpg-agent): ") if passphrase else None

    ok, plaintext, signer_fp = crypto.decrypt_and_verify(
        ciphertext=ciphertext,
        passphrase=pw,
        gpg_home=cfg.gpg_home,
    )

    if not ok:
        err_console.print(plaintext)  # contains the error
        raise typer.Exit(1)

    # Show signer info
    if signer_fp:
        console.print(f"[green]✓ Signature verified — signed by fingerprint: [bold]{signer_fp}[/bold][/green]")
    else:
        console.print("[yellow]⚠ No signature found or could not verify signature.[/yellow]")

    # Output
    if output:
        output.write_text(plaintext)
        console.print(f"[green]✓ Plaintext written to [bold]{output}[/bold][/green]")
    else:
        console.print(Panel(plaintext, title="[bold green]Decrypted message[/bold green]", box=box.ROUNDED))

    if clipboard:
        pyperclip.copy(plaintext)
        console.print("[green]✓ Copied to clipboard.[/green]")


@app.command("add-key")
def add_key(
    alias: str = typer.Argument(..., help="Short alias for the collaborator (e.g. 'juan')."),
    email: str = typer.Argument(..., help="Collaborator's email address."),
    key_file: Path = typer.Argument(..., help="Path to the collaborator's public GPG key file."),
):
    """
    Register a new collaborator: copies their public key into the keys/ directory
    and adds them to collaborators.yaml.

    The updated YAML should be committed and submitted via Pull Request.
    """
    cfg = _load_config()

    if not key_file.exists():
        err_console.print(f"Key file not found: {key_file}")
        raise typer.Exit(1)

    # Derive a canonical filename from the email
    canonical_name = email.lower().replace("@", "-").replace(".", "-") + ".asc"
    dest = cfg.keys_dir / canonical_name

    cfg.keys_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        overwrite = typer.confirm(f"Key file '{canonical_name}' already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    shutil.copy2(key_file, dest)
    console.print(f"[green]✓ Key copied to [bold]{dest}[/bold][/green]")

    # Import into keyring
    ok, fingerprint = crypto.import_key(str(dest), cfg.gpg_home)
    if ok:
        console.print(f"[green]✓ Key imported into GPG keyring. Fingerprint: {fingerprint}[/green]")
    else:
        console.print(f"[yellow]⚠ Key file copied but GPG import failed: {fingerprint}[/yellow]")

    # Add to YAML
    try:
        add_collaborator(cfg.collaborators_file, alias, email, canonical_name)
        console.print(
            f"[green]✓ Collaborator [bold]{alias}[/bold] added to "
            f"[bold]{cfg.collaborators_file.name}[/bold][/green]"
        )
    except ValueError as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    console.print(
        "\n[bold yellow]Next step:[/bold yellow] commit [bold]collaborators.yaml[/bold] "
        "and the new key file, then open a Pull Request."
    )


@app.command()
def list():
    """List all registered collaborators."""
    cfg = _load_config()
    _startup_check(cfg)

    collaborators = load_all(cfg.collaborators_file)

    if not collaborators:
        console.print("[yellow]No collaborators registered yet.[/yellow]")
        raise typer.Exit()

    table = Table(title="Collaborators", box=box.ROUNDED, show_lines=True)
    table.add_column("Alias", style="bold cyan")
    table.add_column("Email", style="white")
    table.add_column("Key file", style="dim")
    table.add_column("Key present", justify="center")

    for c in collaborators:
        key_path = cfg.keys_dir / c.gpgkey
        present = "[green]✓[/green]" if key_path.exists() else "[red]✗ missing[/red]"
        table.add_row(c.alias, c.email, c.gpgkey, present)

    console.print(table)


@app.command("list-keys")
def list_keys(
    secret: bool = typer.Option(False, "--secret", "-s", help="List private keys instead.")
):
    """List GPG keys available in the system keyring."""
    cfg = _load_config()
    keys = crypto.list_secret_keys(cfg.gpg_home) if secret else crypto.list_public_keys(cfg.gpg_home)

    if not keys:
        console.print("[yellow]No keys found in keyring.[/yellow]")
        raise typer.Exit()

    label = "Private" if secret else "Public"
    table = Table(title=f"{label} keys in GPG keyring", box=box.ROUNDED, show_lines=True)
    table.add_column("Key ID", style="bold cyan")
    table.add_column("Fingerprint", style="dim")
    table.add_column("UIDs")

    for k in keys:
        table.add_row(k["keyid"], k["fingerprint"], "\n".join(k["uids"]))

    console.print(table)


# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------

@app.command()
def tui():
    """Lanzar la interfaz de usuario de terminal (TUI)."""
    from gpgshare.tui.app import GpgShareApp
    GpgShareApp().run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app()