# Plan de desarrollo — TUI con Textual

## Premisas de arquitectura

El core (`crypto.py`, `collaborators.py`, `config.py`) no se toca.
La TUI es una capa de presentación alternativa a la CLI. Ambas coexisten.
El entrypoint se separa:

```
gpgshare encrypt juan -m "..."   →  CLI (ya funciona)
gpgshare tui                     →  lanza la TUI
```

---

## Estructura final del proyecto

```
gpgshare/
├── cli.py
├── crypto.py
├── collaborators.py
├── config.py
└── tui/
    ├── __init__.py
    ├── app.py                    # GpgShareApp(App) — root, gestión de pantallas
    ├── screens/
    │   ├── __init__.py
    │   ├── home.py               # pantalla principal / menú
    │   ├── encrypt.py            # formulario de cifrado
    │   ├── decrypt.py            # formulario de descifrado
    │   └── collaborators.py      # listado + add-key
    ├── widgets/
    │   ├── __init__.py
    │   ├── key_selector.py       # selector de destinatario
    │   └── cipher_output.py      # panel de output con botones Copiar/Guardar
    └── styles/
        └── app.tcss              # estilos Textual CSS
```

---

## Fase 1 — Scaffolding y navegación

**Objetivo:** la app arranca, navega entre pantallas, lee config y muestra errores de inicio.

### Dependencias

Agregar a `pyproject.toml`:

```toml
"textual>=0.65",
```

### Tareas

- Crear `tui/app.py` con `GpgShareApp(App)` y el sistema de pantallas (`push_screen`, `pop_screen`).
- Implementar `HomeScreen` con el menú principal: **Cifrar / Descifrar / Colaboradores / Salir**.
- Integrar el `_startup_check` de la CLI como notificación visual (`Notification`) al iniciar.
- Agregar `gpgshare tui` como comando en `cli.py` que llama a `GpgShareApp().run()`.
- Crear `tui/styles/app.tcss` con layout base y variables de color.

### Resultado verificable

`gpgshare tui` abre la app, se navega entre pantallas vacías, los errores de config aparecen como banner en lugar de abortar.

---

## Fase 2 — Pantalla de cifrado

**Objetivo:** cifrar un mensaje con selección de destinatario desde la TUI.

### Tareas

- `EncryptScreen`:
  - `TextArea` para escribir el mensaje.
  - `Select` con los alias del YAML como opciones.
  - Checkbox "Firmar con mi clave" (siempre `True` por defecto, igual que en CLI).
  - Botón **Cifrar** que llama a `crypto.encrypt_and_sign()` dentro de un worker (`@work`) para no bloquear la UI.
- Widget `KeySelector`: encapsula la carga de colaboradores y expone un evento `CollaboratorSelected`.
- Widget `CipherOutput`: panel con el ciphertext resultante y dos botones: **Copiar al portapapeles** y **Guardar en archivo**.
- Manejo de passphrase: si `gpg-agent` no está disponible, mostrar un `Input(password=True)` inline antes de ejecutar.

### Resultado verificable

Se puede cifrar un mensaje para cualquier colaborador del YAML y copiar o guardar el resultado sin salir de la app.

---

## Fase 3 — Pantalla de descifrado

**Objetivo:** pegar o cargar un ciphertext y descifrarlo desde la TUI.

### Tareas

- `DecryptScreen`:
  - `TextArea` para pegar el bloque cifrado en ASCII armor.
  - Botón **Cargar desde archivo** con un `Input` de path o selector de archivo.
  - Botón **Descifrar** → worker que llama a `crypto.decrypt_and_verify()`.
- Panel de resultado con el texto plano.
- Badge de verificación de firma: verde ✓ si la firma es válida, amarillo ⚠ si no se puede verificar.
- Misma lógica de passphrase que en Fase 2.
- Botones **Copiar** y **Guardar**.

### Resultado verificable

Se puede descifrar cualquier mensaje cifrado con la clave pública propia y ver la verificación de firma inline.

---

## Fase 4 — Pantalla de colaboradores

**Objetivo:** gestionar el directorio de colaboradores sin salir de la TUI.

### Tareas

- `CollaboratorsScreen`:
  - `DataTable` con columnas: alias, email, key file, estado (✓ presente / ✗ faltante).
  - Botón **Agregar colaborador** que abre un formulario modal (`ModalScreen`) con campos: alias, email, path al archivo `.asc`.
  - El modal llama internamente a `add_collaborator()` y `crypto.import_key()`, igual que el comando `add-key` de la CLI.
  - Mensaje de confirmación post-registro: _"Commiteá collaborators.yaml y abrí un Pull Request."_
  - Botón **Recargar** para refrescar la tabla sin reiniciar la app.

### Resultado verificable

Se puede ver el listado completo, detectar claves faltantes y registrar un nuevo colaborador desde la TUI.

---

## Fase 5 — Polish y UX

**Objetivo:** la app se siente terminada y es cómoda de usar a diario.

### Tareas

- Navegación completa por teclado: atajos documentados en un footer persistente (`Footer` de Textual).
- Modo oscuro / claro con `App.dark` toggle.
- Indicador de identidad activa en el header: _"Firmando como: vos@empresa.com"_.
- Animación de loading en workers lentos (cifrado/descifrado con claves grandes).
- Pantalla de error dedicada para fallos de GPG con mensaje legible y opción de reintentar.
- Validación de campos en tiempo real (alias vacío, email sin `@`, path inexistente).
- Tests con `textual.testing.Pilot` para los flujos principales (cifrar, descifrar, add-key).

### Resultado verificable

La app pasa un recorrido completo de uso (cifrar → copiar → descifrar → verificar) sin tocar el mouse y sin mensajes de error confusos.

---

## Hoja de ruta resumida

| Fase | Foco | Entregable clave |
|------|------|-----------------|
| 1 | Scaffolding | `gpgshare tui` arranca y navega |
| 2 | Cifrado | Cifrar + copiar/guardar desde TUI |
| 3 | Descifrado | Descifrar + verificar firma desde TUI |
| 4 | Colaboradores | Listar y agregar desde TUI |
| 5 | Polish | UX completa, teclado, tests |

---

## Recursos

- [Textual — documentación oficial](https://textual.textualize.io/)
- [Textual — guía de workers](https://textual.textualize.io/guide/workers/)
- [Textual — testing con Pilot](https://textual.textualize.io/guide/testing/)
- [python-gnupg — docs](https://python-gnupg.readthedocs.io/)