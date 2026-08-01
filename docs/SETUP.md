# NeuroPA setup / Configuración de NeuroPA

This is the **no-tech path** for the public, local-first NeuroPA AI Workspace. / Esta es la ruta **sin conocimientos técnicos** para el AI Workspace público y local-first de NeuroPA.

## Quick start / Inicio rápido

Requirements / Requisitos: Linux or macOS, an internet connection only for the first dependency download, and a terminal.

```bash
git clone https://github.com/FreakingJSON/neuropa.git
cd neuropa
scripts/install.sh
scripts/run-neuropa.sh
```

Open `http://127.0.0.1:8474`. Your data stays on this computer by default. / Abre esa dirección. Tus datos permanecen en este equipo por defecto.

For automation, use `scripts/install.sh --yes`. `--check` only inspects prerequisites and makes no changes. / Para automatización usa `--yes`; `--check` sólo revisa.

## Local-only and OpenCode / Sólo local y OpenCode

- NeuroPA is a local AI Workspace/harness first; executive-function features are a module, not a clinical product. / NeuroPA es primero un Workspace/harness local; las funciones ejecutivas son un módulo, no un producto clínico.
- OpenCode is an optional free CLI path for coding/agent work. Install it only when you want it: `npm install -g opencode-ai`. The installer detects it and never installs Ollama automatically. / OpenCode es opcional y gratuito; el instalador nunca instala Ollama automáticamente.
- The public OSS repository is complete for local-first use. Any private SaaS is a separate product and is not required for this setup. / El OSS público está completo para uso local-first. Cualquier SaaS privado es separado y no es necesario.

## Temporary LAN access / Acceso LAN temporal

Only on a trusted network:

```bash
scripts/run-neuropa.sh --lan --port 8474
```

LAN mode is temporary and binds the server for network access. Stop it with `Ctrl+C`; return to local-only mode by omitting `--lan`. Do not expose it to the internet or an untrusted Wi-Fi network. / El modo LAN es temporal: deténlo con `Ctrl+C` y no lo expongas a Internet.

## Privacy, egress, and data / Privacidad, salida y datos

Default storage is `~/.local/share/neuropa/` (or the platform equivalent). `NEUROPA_DATA_DIR` can choose another directory. No hidden telemetry is required. If you connect an external provider or OpenCode, prompts and files may leave the machine according to that provider's configuration and policy; local-only operation is the safe default. / Si conectas un proveedor externo, los datos pueden salir según su configuración y política.

## Backup and export / Copia y exportación

```bash
uv run neuropa --status
uv run neuropa --export backup.json
```

Keep `backup.json` private. Back up the data directory too when you need a full local recovery. / Mantén privado el JSON y copia también el directorio de datos para una recuperación completa.

## Troubleshooting / Resolución de problemas

- **`uv` missing / falta `uv`:** rerun `scripts/install.sh`; it asks before downloading the official installer. Without `curl`, follow the visible instructions at [uv installation](https://docs.astral.sh/uv/getting-started/installation/).
- **OpenCode missing / falta OpenCode:** install Node.js/npm, then run `npm install -g opencode-ai`. It is optional.
- **Port busy / puerto ocupado:** use another one, for example `scripts/run-neuropa.sh --port 9000`.
- **Browser did not open / no se abrió el navegador:** open `http://127.0.0.1:8474` manually.
- **Stop / detener:** press `Ctrl+C`. User data is not deleted by stopping or by the default uninstall.
- **Clean repo environment / limpiar entorno:** `scripts/uninstall.sh --dry-run`, then `scripts/uninstall.sh`. It removes only `.venv` and known repo caches. `--purge-data` requires typing exactly `PURGE NEUROPA DATA`.

## For contributors / Para contribuidores

```bash
uv sync --extra dev
uv run pytest -q
```

See [CONTRIBUTING.md](../CONTRIBUTING.md), [LICENSES.md](../LICENSES.md), and [LICENSE](../LICENSE) for contribution, attribution, and licensing details.
