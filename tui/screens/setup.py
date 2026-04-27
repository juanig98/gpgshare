"""
SetupScreen — formulario para configurar .env desde la TUI.
Closes #1, #2, #3
"""

import os
import re
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Input, Label, Static, Select
from textual.containers import Vertical, ScrollableContainer
from textual import work
from gpgshare.i18n import t
from gpgshare.tui.widgets.cipher_output import CipherOutput


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _PROJECT_ROOT / ".env"

# (env_key, translation_key, optional)
_FIELDS = [
    ("GPG_SIGNER_EMAIL",      "setup.label_signer_email",       False),
    ("GPG_PRIVATE_KEY_PATH",  "setup.label_private_key_path",   False),
    ("GPG_HOME",              "setup.label_gpg_home",           True),
    ("KEYS_DIR",              "setup.label_keys_dir",           True),
    ("COLLABORATORS_FILE",    "setup.label_collaborators_file", True),
]


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return values
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip()
    return values


def _write_env(values: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in values.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n")


def _canonical_filename(email: str) -> str:
    return email.lower().replace("@", "-").replace(".", "-") + ".asc"


class SetupScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("ctrl+s", "save", "Save config"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer():
            with Vertical(id="setup-container"):
                # ── Sección 1: .env ──────────────────────────────────────
                yield Static(t("setup.title"), id="setup-title")
                yield Static(t("setup.subtitle"), id="setup-subtitle")
                current = _read_env()
                for key, label_key, _ in _FIELDS:
                    yield Label(t(label_key), classes="form-label")
                    yield Input(value=current.get(key, ""), placeholder=key, id=f"input-{key}")

                yield Label(t("setup.label_language"), classes="form-label")
                _lang_opts = [("English", "en"), ("Español", "es")]
                _lang_val = current.get("LANGUAGE", "en")
                if _lang_val not in {v for _, v in _lang_opts}:
                    _lang_val = "en"
                yield Select(
                    options=_lang_opts,
                    id="input-LANGUAGE",
                    value=_lang_val,
                    allow_blank=False,
                )

                with Vertical(classes="form-actions"):
                    yield Button(t("setup.btn_save"), id="btn-save", variant="success")
                    yield Button(t("setup.btn_cancel"), id="btn-cancel")
                yield Static("", id="setup-status")

                # ── Sección 2: Registrar mi clave pública ────────────────
                yield Static(t("setup.register.title"), id="register-title")
                yield Static(t("setup.register.subtitle"), id="register-subtitle")
                yield Label(t("setup.register.label_select_key"), classes="form-label")
                yield Select(
                    options=[],
                    prompt=t("setup.register.prompt_loading"),
                    id="select-key",
                    allow_blank=True,
                )
                yield Label(t("setup.register.label_alias"), classes="form-label")
                yield Input(placeholder=t("setup.register.placeholder_alias"), id="input-alias")
                with Vertical(classes="form-actions"):
                    yield Button(t("setup.register.btn"), id="btn-register", variant="primary")
                yield Static("", id="register-status")

                # ── Sección 3: Exportar mi clave pública ─────────────────
                yield Static(t("setup.export.title"), id="export-title")
                yield Static(t("setup.export.subtitle"), id="export-subtitle")
                yield Label(t("setup.export.label_select_key"), classes="form-label")
                yield Select(
                    options=[],
                    prompt=t("setup.register.prompt_loading"),
                    id="select-key-export",
                    allow_blank=True,
                )
                with Vertical(classes="form-actions"):
                    yield Button(t("setup.export.btn"), id="btn-export", variant="primary")
                yield CipherOutput(title=t("setup.export.cipher_output_title"), id="export-output")

        yield Footer()

    def on_mount(self) -> None:
        self._load_keys()

    @work(thread=True)
    def _load_keys(self) -> None:
        from gpgshare.crypto import list_secret_keys
        cfg = getattr(self.app, "_cfg", None)
        gpg_home = cfg.gpg_home if cfg else None
        keys = list_secret_keys(gpg_home)
        self.app.call_from_thread(self._populate_select, keys)

    def _populate_select(self, keys: list[dict]) -> None:
        cfg = getattr(self.app, "_cfg", None)
        signer_email = cfg.signer_email if cfg else _read_env().get("GPG_SIGNER_EMAIL", "")

        options = []
        preselect = None
        for k in keys:
            label = k["uids"][0] if k["uids"] else k["keyid"]
            options.append((label, k["keyid"]))
            if signer_email and any(signer_email.lower() in uid.lower() for uid in k["uids"]):
                preselect = k["keyid"]

        empty_opts = [(t("setup.select.no_keys"), "")]

        for sel_id in ("#select-key", "#select-key-export"):
            select: Select = self.query_one(sel_id, Select)
            if not options:
                select.set_options(empty_opts)
            else:
                select.set_options(options)
                if preselect:
                    select.value = preselect

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        self._do_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-save":
                self._do_save()
            case "btn-cancel":
                self.action_go_back()
            case "btn-register":
                self._do_register()
            case "btn-export":
                self._do_export()

    def _do_save(self) -> None:
        values: dict[str, str] = {}
        missing = []
        current = _read_env()

        for key, _, optional in _FIELDS:
            widget: Input = self.query_one(f"#input-{key}", Input)
            val = widget.value.strip()
            if val:
                values[key] = val
            elif not optional:
                missing.append(key)

        lang_select: Select = self.query_one("#input-LANGUAGE", Select)
        if lang_select.value and lang_select.value is not Select.BLANK:
            values["LANGUAGE"] = str(lang_select.value)

        status = self.query_one("#setup-status", Static)

        if missing:
            status.update(t("setup.status.missing_fields", fields=", ".join(missing)))
            return

        try:
            _write_env(values)
            for key, val in values.items():
                os.environ[key] = val

            lang_changed = values.get("LANGUAGE") != current.get("LANGUAGE", "en")
            self.notify(t("setup.notify.saved"), severity="information", title="Setup")
            if lang_changed:
                self.notify(t("setup.notify.language_restart"), severity="warning", title="Setup")
            self.app.pop_screen()
        except OSError as exc:
            status.update(t("setup.status.save_error", exc=exc))

    def _do_register(self) -> None:
        select: Select = self.query_one("#select-key", Select)
        alias_input: Input = self.query_one("#input-alias", Input)
        status = self.query_one("#register-status", Static)

        keyid = select.value
        alias = alias_input.value.strip()

        if not keyid or keyid is Select.BLANK:
            status.update(t("setup.status.no_key_selected"))
            return
        if not alias:
            status.update(t("setup.status.alias_required"))
            return

        # Extraer email del uid (formato "Name <email@domain.com>")
        uid_label = str(select._options[
            next(i for i, (_, v) in enumerate(select._options) if v == keyid)
        ][0]) if hasattr(select, "_options") else ""

        match = re.search(r"<(.+?)>", uid_label)
        email = match.group(1) if match else uid_label

        status.update(t("setup.status.registering"))
        self._run_register(keyid, alias, email)

    @work(thread=True)
    def _run_register(self, keyid: str, alias: str, email: str) -> None:
        from gpgshare.crypto import export_public_key
        from gpgshare.collaborators import add_collaborator

        cfg = getattr(self.app, "_cfg", None)
        gpg_home = cfg.gpg_home if cfg else None

        if cfg:
            keys_dir = cfg.keys_dir
            collaborators_file = cfg.collaborators_file
        else:
            env = _read_env()
            keys_dir = Path(env.get("KEYS_DIR", str(_PROJECT_ROOT / "keys")))
            collaborators_file = Path(env.get("COLLABORATORS_FILE", str(_PROJECT_ROOT / "collaborators.yaml")))

        ok, result = export_public_key(keyid, gpg_home)
        if not ok:
            self.app.call_from_thread(
                self._set_register_status, t("setup.status.export_error", result=result)
            )
            return

        filename = _canonical_filename(email)
        key_path = keys_dir / filename
        try:
            keys_dir.mkdir(parents=True, exist_ok=True)
            key_path.write_text(result)
        except OSError as exc:
            self.app.call_from_thread(
                self._set_register_status, t("setup.status.save_error", exc=exc)
            )
            return

        try:
            add_collaborator(collaborators_file, alias, email, filename)
        except ValueError as exc:
            self.app.call_from_thread(self._set_register_status, str(exc))
            return

        self.app.call_from_thread(
            self._set_register_status,
            t("setup.status.registered", alias=alias, email=email, filename=filename),
        )

    def _set_register_status(self, msg: str) -> None:
        self.query_one("#register-status", Static).update(msg)

    def _do_export(self) -> None:
        select: Select = self.query_one("#select-key-export", Select)
        keyid = select.value
        if not keyid or keyid is Select.BLANK:
            self.notify(t("setup.status.no_key_selected"), severity="warning")
            return
        self._run_export(keyid)

    @work(thread=True)
    def _run_export(self, keyid: str) -> None:
        from gpgshare.crypto import export_public_key
        cfg = getattr(self.app, "_cfg", None)
        gpg_home = cfg.gpg_home if cfg else None
        ok, result = export_public_key(keyid, gpg_home)
        if not ok:
            self.app.call_from_thread(
                self.notify, t("setup.status.export_error", result=result), severity="error"
            )
            return
        self.app.call_from_thread(self._show_export, result)

    def _show_export(self, armored: str) -> None:
        self.query_one("#export-output", CipherOutput).set_content(armored)
