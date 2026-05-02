# gpgshare

Cifrá mensajes para tus compañeros de equipo en un solo paso. Pegá el resultado en Slack, email o donde quieras — solo el destinatario puede leerlo.

---

## Empezar

```bash
git clone https://github.com/juanig98/gpgshare.git
cd gpgshare
bash run.sh
```

Eso es todo. El script se encarga de instalar dependencias y configurar tu clave GPG si todavía no tenés una.

---

## Uso diario

Para abrir la app:

```bash
bash run.sh
```

Desde la interfaz podés:

- **Cifrar** un mensaje para un compañero
- **Descifrar** un mensaje que te enviaron
- **Agregar colaboradores** para poder enviarles mensajes
- **Configurar** tu clave y perfil desde la pantalla de Setup

---

## Agregar un compañero

Para poder enviarle mensajes cifrados a alguien, necesitás su clave pública.

1. Pedile que corra `bash run.sh` en su máquina — eso genera y registra su clave automáticamente
2. Una vez que abra un Pull Request con su clave, hacé `git pull`
3. Listo — su nombre aparece en el selector de destinatarios

---

## Seguridad

- Los mensajes se cifran **y** se firman. El destinatario puede verificar que vinieron de vos.
- Tu clave privada nunca sale de tu máquina.
- Solo las claves públicas se guardan en el repositorio.
