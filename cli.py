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
from gpgshare.i18n import t, setup_language

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
        err_console.print(f"[bold red]{t('cli.startup.registry_errors')}[/bold red]")
        for e in errors:
            err_console.print(f"  [red]• {e}[/red]")
        console.print(f"[yellow]{t('cli.startup.keys_missing')}[/yellow]\n")


def _load_config() -> Config:
    try:
        cfg = Config.load()
        setup_language(cfg.language)
        return cfg
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

    collaborator = find_by_alias(cfg.collaborators_file, recipient)
    if not collaborator:
        err_console.print(t("cli.encrypt.collaborator_not_found", recipient=recipient))
        raise typer.Exit(1)

    if message is None:
        if sys.stdin.isatty():
            console.print(f"[dim]{t('cli.encrypt.stdin_prompt')}[/dim]")
        message = sys.stdin.read()

    if not message.strip():
        err_console.print(t("cli.encrypt.empty_message"))
        raise typer.Exit(1)

    key_path = cfg.keys_dir / collaborator.gpgkey
    ok, result = crypto.import_key(str(key_path), cfg.gpg_home)
    if not ok:
        err_console.print(t("cli.encrypt.error_import_recipient", result=result))
        raise typer.Exit(1)

    ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
    if not ok:
        err_console.print(t("cli.encrypt.error_import_private", result=result))
        raise typer.Exit(1)

    pw = getpass.getpass("Private key passphrase (leave empty for gpg-agent): ") if passphrase else None

    console.print(
        f"[dim]{t('cli.encrypt.encrypting', alias=collaborator.alias, email=collaborator.email, signer=cfg.signer_email)}[/dim]"
    )

    ok, ciphertext = crypto.encrypt_and_sign(
        content=message,
        recipient_email=collaborator.email,
        signer_key_id=cfg.signer_email,
        passphrase=pw,
        gpg_home=cfg.gpg_home,
    )

    if not ok:
        err_console.print(ciphertext)
        raise typer.Exit(1)

    if output:
        output.write_text(ciphertext)
        console.print(f"[green]{t('cli.encrypt.written', output=output)}[/green]")
    else:
        console.print(Panel(ciphertext, title=f"[bold green]{t('cli.encrypt.panel_title')}[/bold green]", box=box.ROUNDED))

    if clipboard:
        pyperclip.copy(ciphertext)
        console.print(f"[green]{t('cli.encrypt.copied')}[/green]")


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

    ok, result = crypto.import_key(cfg.private_key_path, cfg.gpg_home)
    if not ok:
        err_console.print(t("cli.encrypt.error_import_private", result=result))
        raise typer.Exit(1)

    if input_file:
        ciphertext = input_file.read_text()
    elif ciphertext is None:
        if sys.stdin.isatty():
            console.print(f"[dim]{t('cli.decrypt.stdin_prompt')}[/dim]")
        ciphertext = sys.stdin.read()

    if not ciphertext or not ciphertext.strip():
        err_console.print(t("cli.decrypt.no_ciphertext"))
        raise typer.Exit(1)

    pw = getpass.getpass("Private key passphrase (leave empty for gpg-agent): ") if passphrase else None

    ok, plaintext, signer_fp = crypto.decrypt_and_verify(
        ciphertext=ciphertext,
        passphrase=pw,
        gpg_home=cfg.gpg_home,
    )

    if not ok:
        err_console.print(plaintext)
        raise typer.Exit(1)

    if signer_fp:
        console.print(f"[green]{t('cli.decrypt.sig_valid', signer_fp=signer_fp)}[/green]")
    else:
        console.print(f"[yellow]{t('cli.decrypt.sig_invalid')}[/yellow]")

    if output:
        output.write_text(plaintext)
        console.print(f"[green]{t('cli.decrypt.written', output=output)}[/green]")
    else:
        console.print(Panel(plaintext, title=f"[bold green]{t('cli.decrypt.panel_title')}[/bold green]", box=box.ROUNDED))

    if clipboard:
        pyperclip.copy(plaintext)
        console.print(f"[green]{t('cli.encrypt.copied')}[/green]")


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
        err_console.print(t("cli.add_key.file_not_found", key_file=key_file))
        raise typer.Exit(1)

    canonical_name = email.lower().replace("@", "-").replace(".", "-") + ".asc"
    dest = cfg.keys_dir / canonical_name

    cfg.keys_dir.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        overwrite = typer.confirm(t("cli.add_key.confirm_overwrite", canonical_name=canonical_name))
        if not overwrite:
            raise typer.Abort()

    shutil.copy2(key_file, dest)
    console.print(f"[green]{t('cli.add_key.key_copied', dest=dest)}[/green]")

    ok, fingerprint = crypto.import_key(str(dest), cfg.gpg_home)
    if ok:
        console.print(f"[green]{t('cli.add_key.key_imported', fingerprint=fingerprint)}[/green]")
    else:
        console.print(f"[yellow]{t('cli.add_key.import_warn', fingerprint=fingerprint)}[/yellow]")

    try:
        add_collaborator(cfg.collaborators_file, alias, email, canonical_name)
        console.print(
            f"[green]{t('cli.add_key.collaborator_added', alias=alias, filename=cfg.collaborators_file.name)}[/green]"
        )
    except ValueError as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    console.print(t("cli.add_key.next_step"))


@app.command()
def list():
    """List all registered collaborators."""
    cfg = _load_config()
    _startup_check(cfg)

    collaborators = load_all(cfg.collaborators_file)

    if not collaborators:
        console.print(f"[yellow]{t('cli.list.no_collaborators')}[/yellow]")
        raise typer.Exit()

    table = Table(title=t("cli.list.table_title"), box=box.ROUNDED, show_lines=True)
    table.add_column(t("cli.list.col_alias"), style="bold cyan")
    table.add_column(t("cli.list.col_email"), style="white")
    table.add_column(t("cli.list.col_keyfile"), style="dim")
    table.add_column(t("cli.list.col_present"), justify="center")

    for c in collaborators:
        key_path = cfg.keys_dir / c.gpgkey
        present = t("cli.list.present") if key_path.exists() else t("cli.list.missing")
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
        console.print(f"[yellow]{t('cli.list_keys.no_keys')}[/yellow]")
        raise typer.Exit()

    label = t("cli.list_keys.label_private") if secret else t("cli.list_keys.label_public")
    table = Table(title=t("cli.list_keys.table_title", label=label), box=box.ROUNDED, show_lines=True)
    table.add_column(t("cli.list_keys.col_keyid"), style="bold cyan")
    table.add_column(t("cli.list_keys.col_fingerprint"), style="dim")
    table.add_column(t("cli.list_keys.col_uids"))

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
