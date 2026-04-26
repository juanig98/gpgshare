# gpgshare — CLAUDE.md

## Qué es este proyecto

CLI + TUI para cifrar y descifrar mensajes entre colaboradores usando GPG. El usuario cifra un mensaje para un destinatario (usando su clave pública) y lo firma con su propia clave privada. El receptor descifra y verifica la firma.

## Stack

- Python 3.11+
- **Typer + Rich** — CLI
- **Textual** — TUI
- **python-gnupg** — wrapper del binario GPG del sistema
- **PyYAML** — registro de colaboradores
- **python-dotenv** — configuración local
- **pyperclip** — portapapeles

Instalación: `pip install -e ".[dev]"`  
Entrypoint: `gpgshare` (definido en `pyproject.toml` → `gpgshare.cli:main`)

## Estructura de archivos

```
gpgshare/
├── config.py           # Carga .env, expone Config dataclass
├── crypto.py           # Operaciones GPG (import, encrypt, decrypt, list)
├── collaborators.py    # CRUD sobre collaborators.yaml
├── cli.py              # Comandos CLI (Typer)
├── collaborators.yaml  # Registro compartido (va a VCS)
├── keys/               # Archivos .asc de claves públicas (van a VCS)
├── .env                # Config local — NUNCA commitear
└── tui/
    ├── app.py                      # GpgShareApp (raíz Textual)
    ├── screens/
    │   ├── home.py                 # Menú principal
    │   ├── encrypt.py              # Pantalla de cifrado
    │   ├── decrypt.py              # Pantalla de descifrado
    │   └── collaborators.py        # Tabla + modal para agregar colaboradores
    └── widgets/
        ├── key_selector.py         # Select de colaboradores, emite CollaboratorSelected
        └── cipher_output.py        # Panel read-only con acciones copiar/guardar
```

## Configuración (.env)

```env
GPG_PRIVATE_KEY_PATH=~/.gnupg/my-private-key.asc   # requerido
GPG_SIGNER_EMAIL=you@yourcompany.com                 # requerido
GPG_HOME=                                            # opcional, default ~/.gnupg
KEYS_DIR=./keys                                      # opcional
COLLABORATORS_FILE=./collaborators.yaml              # opcional
```

Exportar clave privada: `gpg --armor --export-secret-keys you@email.com > ~/my-private-key.asc`

## Comandos CLI

```bash
gpgshare encrypt <alias>          # Cifra para un colaborador (lee stdin si no hay -m)
gpgshare decrypt                  # Descifra (lee stdin o -i archivo)
gpgshare add-key <alias> <email> <archivo.asc>  # Registra colaborador
gpgshare list                     # Lista colaboradores registrados
gpgshare list-keys [--secret]     # Lista claves en el keyring GPG
gpgshare tui                      # Lanza la TUI
```

Flags comunes: `-o <archivo>` (salida a archivo), `-c` (copiar al portapapeles), `-p` (pedir passphrase interactiva).

## Módulos core

### config.py — `Config`

Dataclass cargada desde `.env`. Campos: `private_key_path`, `signer_email`, `gpg_home`, `keys_dir` (Path), `collaborators_file` (Path). Lanza `EnvironmentError` si faltan los campos requeridos. Llamar siempre con `Config.load()`.

### crypto.py

Todas las funciones reciben `gpg_home: Optional[str]` (None = usar keyring del sistema).

- `import_key(key_path, gpg_home)` → `(bool, fingerprint_or_error)` — importa clave pública o privada
- `encrypt_and_sign(content, recipient_email, signer_key_id, passphrase, gpg_home)` → `(bool, armored_or_error)`
- `decrypt_and_verify(ciphertext, passphrase, gpg_home)` → `(bool, plaintext_or_error, signer_fp_or_None)`
- `list_public_keys(gpg_home)` / `list_secret_keys(gpg_home)` → `list[dict]` con keys `fingerprint`, `uids`, `keyid`

GPG siempre se llama con `always_trust=True` y `use_agent=True`.

### collaborators.py — `Collaborator`

Dataclass: `alias`, `email`, `gpgkey` (nombre del archivo `.asc` dentro de `keys/`).

- `load_all(file)` → lista de Collaborator
- `find_by_alias(file, alias)` — case-insensitive
- `find_by_email(file, email)`
- `add_collaborator(file, alias, email, gpgkey_filename)` — lanza `ValueError` si alias o email ya existe
- `validate_registry(file, keys_dir)` → `list[str]` de errores (vacío = todo OK)

Nombre canónico del archivo: `email.lower().replace("@", "-").replace(".", "-") + ".asc"`

### cli.py

Llama `_startup_check()` al inicio de cada comando: valida integridad del registro y muestra warnings si faltan archivos `.asc`. No aborta en warnings, solo en errores críticos de config.

## TUI (Textual)

`GpgShareApp` carga `Config` en `on_mount` y lo guarda en `self._cfg`. Las screens acceden a él con `getattr(self.app, "_cfg", None)`.

Las operaciones GPG (cifrado, descifrado, registro de colaboradores) se ejecutan en **workers de thread** (`@work(thread=True)`) para no bloquear el event loop. Las callbacks al hilo principal se hacen con `self.call_from_thread(...)`.

Navegación de la TUI:
- `HomeScreen`: teclas `1` cifrar, `2` descifrar, `3` colaboradores, `Q` salir
- `EncryptScreen`: `Ctrl+E` cifrar, `Escape` volver
- `DecryptScreen`: `Ctrl+D` descifrar, `Escape` volver, soporte para cargar desde archivo
- `CollaboratorsScreen`: `A` agregar, `R` recargar, `Escape` volver

`KeySelector` emite `KeySelector.CollaboratorSelected(alias, email)` al seleccionar un destinatario.  
`CipherOutput` se muestra oculto hasta que se llama `set_content(text)`, luego agrega la clase `visible`.

## Tests

```bash
pytest                  # corre tests/ y tui/tests/
pytest tests/test_crypto.py   # módulo específico
```

Tests en `tests/`: unit tests de `crypto`, `collaborators`, `config`, `cli` (con mocks de gnupg y filesystem).  
Tests en `tui/tests/`: tests de la TUI con `pytest-asyncio`.

## Flujo para agregar un colaborador

1. El colaborador exporta su clave: `gpg --armor --export their@email.com > their.asc`
2. Correr `gpgshare add-key <alias> <email> their.asc` (o usar la TUI)
3. Commitear `collaborators.yaml` y el archivo `.asc` en `keys/`
4. Abrir Pull Request — el YAML y las claves son el registro compartido del equipo
