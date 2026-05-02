# SDD 002 — Cifrado para múltiples destinatarios

## Contexto

Actualmente `encrypt_and_sign` acepta un único email y el CLI/TUI solo permiten seleccionar un destinatario. GPG soporta nativamente cifrar para múltiples destinatarios pasando una lista a `recipients=[...]`. Este cambio expone esa capacidad en toda la cadena: función crypto → CLI → TUI.

**Resultado esperado:**
- `gpgshare encrypt juan maria` cifra para ambos.
- `gpgshare encrypt --all` cifra para todos los colaboradores registrados.
- La TUI permite selección múltiple con checkbox list y un botón "Seleccionar todos".

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `crypto.py` | Cambio de firma: `recipient_email: str` → `recipient_emails: list[str]` |
| `gpgshare/cli.py` | Args variádicos + flag `--all` |
| `tui/widgets/key_selector.py` | `Select` → `SelectionList` (Textual ≥ 0.65) |
| `tui/screens/encrypt.py` | Multi-select + botón Select All |
| `translations/en.json` | Strings nuevos para multi-select |
| `translations/es.json` | Strings nuevos para multi-select |
| `tests/test_crypto.py` | Actualizar `recipient_email=` → `recipient_emails=[…]` |

---

## Diseño por módulo

### `crypto.py` — `encrypt_and_sign`

**Antes:**
```python
def encrypt_and_sign(
    content: str,
    recipient_email: str,
    signer_key_id: str,
    passphrase: Optional[str] = None,
    gpg_home: Optional[str] = None,
) -> tuple[bool, str]:
    ...
    result = gpg.encrypt(content, recipients=[recipient_email], ...)
```

**Después:**
```python
def encrypt_and_sign(
    content: str,
    recipient_emails: list[str],
    signer_key_id: str,
    passphrase: Optional[str] = None,
    gpg_home: Optional[str] = None,
) -> tuple[bool, str]:
    ...
    result = gpg.encrypt(content, recipients=recipient_emails, ...)
```

GPG ya soporta múltiples destinatarios internamente; el único cambio real es la firma de la función.

---

### `gpgshare/cli.py` — comando `encrypt`

**Antes:** un argumento posicional `recipient: str`.

**Después:**
```python
@app.command()
def encrypt(
    recipients: Optional[List[str]] = typer.Argument(
        None, help="Alias(es) of recipient collaborator(s). Omit if using --all."
    ),
    all_collaborators: bool = typer.Option(
        False, "--all", "-a", help="Encrypt for all registered collaborators."
    ),
    message: Optional[str] = typer.Option(None, "--message", "-m"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    clipboard: bool = typer.Option(False, "--clipboard", "-c"),
    passphrase: bool = typer.Option(False, "--passphrase", "-p"),
):
```

**Lógica:**
1. Si `--all` → cargar todos con `collaborators.load_all()`.
2. Si no hay `recipients` y no hay `--all` → error y salir.
3. Loop: por cada alias → `find_by_alias` → importar clave pública → acumular email.
4. Si algún alias no existe → error y salir.
5. Llamar `encrypt_and_sign(content, recipient_emails=[...], ...)`.

**Ejemplos de uso:**
```bash
gpgshare encrypt juan -m "hola"
gpgshare encrypt juan maria pedro -m "hola a todos"
gpgshare encrypt --all -m "broadcast"
```

---

### `tui/widgets/key_selector.py` — SelectionList

Reemplaza `Select` (selección única) por `SelectionList` (selección múltiple con espacio).

**API pública del widget:**
```python
class KeySelector(Widget):
    def get_selected_aliases(self) -> list[str]: ...
    def select_all(self) -> None: ...
    def deselect_all(self) -> None: ...
```

- Se elimina la clase de evento `CollaboratorSelected` (ya no se emite en cada cambio).
- La selección se lee bajo demanda al presionar Encrypt.
- `_load_options()` retorna `list[tuple[str, str]]` con `(display_text, alias)`.

---

### `tui/screens/encrypt.py`

**Cambios en estado:**
- Eliminar `_selected_alias: str | None` y `_selected_email: str | None`.
- Eliminar handler `on_key_selector_collaborator_selected()`.

**Cambios en compose():**
- Agregar fila horizontal con botones `btn-select-all` / `btn-deselect-all`.

**`action_encrypt()` actualizado:**
```python
aliases = self.query_one(KeySelector).get_selected_aliases()
if not aliases:
    self.notify(t("encrypt.notify.no_recipient"), severity="warning")
    return
# ... resto de validaciones
self._run_encrypt(message, aliases, signer_email, passphrase)
```

**`_run_encrypt` actualizado:**
```python
@work(thread=True)
def _run_encrypt(self, message, aliases, signer_email, passphrase):
    emails = []
    for alias in aliases:
        collab = find_by_alias(cfg.collaborators_file, alias)
        if not collab:
            # notificar error y retornar
            return
        key_path = cfg.keys_dir / collab.gpgkey
        ok, result = crypto.import_key(str(key_path), cfg.gpg_home)
        if not ok:
            # notificar error y retornar
            return
        emails.append(collab.email)

    ok, ciphertext = crypto.encrypt_and_sign(
        content=message,
        recipient_emails=emails,
        signer_key_id=signer_email,
        passphrase=passphrase,
        gpg_home=cfg.gpg_home,
    )
    ...
```

---

### Traducciones

Agregar en `en.json` y `es.json`:

```json
"encrypt.btn_select_all": "Select all",
"encrypt.btn_deselect_all": "Deselect all",
"encrypt.notify.no_recipient": "Select at least one recipient."
```

```json
"encrypt.btn_select_all": "Seleccionar todos",
"encrypt.btn_deselect_all": "Deseleccionar todos",
"encrypt.notify.no_recipient": "Seleccioná al menos un destinatario."
```

La clave `encrypt.notify.no_collaborator_selected` (si existe) se reemplaza por `encrypt.notify.no_recipient`.

---

### `tests/test_crypto.py`

Actualizar los 3 tests de `TestEncryptAndSign`: renombrar kwarg `recipient_email="..."` → `recipient_emails=["..."]`.

El assert existente `"bob@example.com" in call_kwargs[1]["recipients"]` sigue siendo válido con lista.

---

## Verificación

```bash
# Tests unitarios
pytest tests/test_crypto.py -v

# CLI: un destinatario
gpgshare encrypt juan -m "hola"

# CLI: varios destinatarios
gpgshare encrypt juan maria -m "hola a todos"

# CLI: todos los colaboradores
gpgshare encrypt --all -m "broadcast"

# TUI: selección múltiple
bash run.sh
# → En Encrypt: seleccionar varios con espacio, luego Ctrl+E
# → En Encrypt: usar botón "Seleccionar todos", luego Ctrl+E
```
