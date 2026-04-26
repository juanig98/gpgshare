# gpgshare

CLI para cifrar y descifrar mensajes entre colaboradores usando claves GPG.
Firmado + cifrado en un solo paso. Output en ASCII armor, listo para pegar en cualquier canal.

---

## Requisitos

- Python 3.11+
- GPG instalado en el sistema (`brew install gnupg` en macOS)

---

## Instalación

```bash
git clone https://github.com/tu-org/gpgshare.git
cd gpgshare

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

---

## Configuración inicial

```bash
cp .env.example .env
```

Editá `.env` con tus valores:

```bash
GPG_PRIVATE_KEY_PATH=~/.gnupg/mi-clave-privada.asc
GPG_SIGNER_EMAIL=vos@tuempresa.com
```

> `.env` está en `.gitignore`. Nunca lo commitees.

---

## Generar una clave GPG (si no tenés una)

```bash
gpg --full-generate-key
```

Seguí el asistente:
1. Tipo de clave → **ECC (sign and encrypt)** o RSA 4096
2. Curva o tamaño → default está bien
3. Expiración → a tu criterio
4. Nombre y email → los datos que van a identificar tu clave

Para verificar que se creó:

```bash
gpg --list-secret-keys
```

---

## Exportar tu clave privada (para el .env)

```bash
gpg --armor --export-secret-keys vos@tuempresa.com > ~/mi-clave-privada.asc
```

---

## Registrarte como colaborador

```bash
# Exportar tu clave pública primero
gpg --armor --export vos@tuempresa.com > /tmp/vos-tuempresa-com.asc

# Registrarla en el proyecto
gpgshare add-key tuAlias vos@tuempresa.com /tmp/vos-tuempresa-com.asc
```

Luego commiteá `collaborators.yaml` y el archivo `.asc` en `keys/` y abrí un Pull Request.

---

## Comandos

### Cifrar un mensaje

```bash
# Interactivo (te pide el mensaje)
gpgshare encrypt juan

# Con el mensaje directo
gpgshare encrypt juan --message "Token de producción: abc123"

# Desde stdin
echo "mensaje secreto" | gpgshare encrypt juan

# Guardar en archivo
gpgshare encrypt juan -m "secreto" --output mensaje.asc

# Copiar al portapapeles
gpgshare encrypt juan -m "secreto" --clipboard

# Con passphrase (si no usás gpg-agent)
gpgshare encrypt juan -m "secreto" --passphrase
```

### Descifrar un mensaje

```bash
# Pegar ciphertext por stdin
gpgshare decrypt

# Desde archivo
gpgshare decrypt --input mensaje.asc

# Guardar resultado en archivo
gpgshare decrypt --input mensaje.asc --output resultado.txt

# Copiar resultado al portapapeles
gpgshare decrypt --clipboard

# Con passphrase
gpgshare decrypt --passphrase
```

### Listar colaboradores

```bash
gpgshare list
```

### Listar claves en el keyring GPG

```bash
gpgshare list-keys           # claves públicas
gpgshare list-keys --secret  # claves privadas
```

---

## Estructura del proyecto

```
gpgshare/
├── .env.example         # plantilla de configuración
├── .env                 # tu configuración local (NO commitear)
├── collaborators.yaml   # directorio de colaboradores (versionado)
├── keys/                # claves públicas (.asc) de colaboradores
├── gpgshare/
│   ├── cli.py           # comandos CLI (Typer + Rich)
│   ├── crypto.py        # operaciones GPG
│   ├── collaborators.py # lectura/escritura del YAML
│   └── config.py        # carga del .env
└── pyproject.toml
```

---

## Flujo típico entre colaboradores

```
Juan quiere mandar un secreto a Gabriel:

1. Juan corre:  gpgshare encrypt gabriel -m "pass: X9#kL2" --clipboard
2. Juan pega el bloque cifrado en Slack/mail/lo que sea
3. Gabriel corre: gpgshare decrypt --clipboard  (o pega por stdin)
4. Gabriel ve el mensaje descifrado + confirmación de firma de Juan
```

---

## Múltiples identidades en la misma máquina

Podés tener varias claves GPG conviviendo en el mismo keyring. Útil para probar el flujo o manejar múltiples cuentas.

```bash
# Generar una segunda clave con otro email
gpg --full-generate-key

# Exportar su clave privada
gpg --armor --export-secret-keys otro@correo.com > ~/.gnupg/otro-private-key.asc

# Exportar su clave pública para registrarla como colaborador
gpg --armor --export otro@correo.com > /tmp/otro.asc
gpgshare add-key otro otro@correo.com /tmp/otro.asc
```

Para usar gpgshare con esa identidad, cambiás `.env`:

```env
GPG_PRIVATE_KEY_PATH=~/.gnupg/otro-private-key.asc
GPG_SIGNER_EMAIL=otro@correo.com
```

---

## Notas de seguridad

- Los mensajes se cifran **y firman** en un solo paso. El destinatario puede verificar quién lo envió.
- Nunca commiteés tu `.env` ni tu clave privada.
- Las claves privadas nunca tocan el repositorio. Solo las públicas van en `keys/`.
- Si usás `gpg-agent` (recomendado en macOS con GPG Suite), no necesitás passphrase en cada comando.