# NeuroPA setup / Configuración de NeuroPA

This is the **no-tech path** for the public, local-first NeuroPA AI Workspace. / Esta es la ruta **sin conocimientos técnicos** para el AI Workspace público y local-first de NeuroPA.

## Quick start / Inicio rápido

Requirements / Requisitos: Linux, macOS, Windows PowerShell, Docker, or Android / Termux; internet is only required for the first dependency download and remote AI providers.

```bash
git clone https://github.com/FreakingJSON/neuropa.git
cd neuropa
scripts/install.sh
scripts/run-neuropa.sh
```

Open `http://127.0.0.1:8474`. Your data stays on this computer by default. / Abre esa dirección. Tus datos permanecen en este equipo por defecto.

For automation, use `scripts/install.sh --yes`. `--check` only inspects prerequisites and makes no changes. / Para automatización usa `--yes`; `--check` sólo revisa.

## Platform paths / Rutas por plataforma

### Linux and macOS

Use the quick-start commands above. On macOS, install Git and `uv` first if they are not already available. Data uses the platform-native directory (`~/.local/share/neuropa` on Linux, `~/Library/Application Support/neuropa` on macOS).

### Windows PowerShell

```powershell
git clone https://github.com/FreakingJSON/neuropa.git
cd neuropa
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
powershell -ExecutionPolicy Bypass -File scripts\run-neuropa.ps1
```

The PowerShell installer fails closed when `uv` or Git is missing and asks before downloading dependencies. Use `-Check` for read-only prerequisite inspection or `-Yes` for explicit automation. LAN remains opt-in: `scripts\run-neuropa.ps1 -Lan -LanCidr 192.168.1.0/24`.

### Docker

```bash
docker compose up --build
```

Open `http://127.0.0.1:8474`. The compose file publishes NeuroPA on host loopback only and persists data in the named `neuropa-data` volume. Stop with `docker compose down`; add `-v` only when you intentionally want to delete that volume.

### Android / Termux

```bash
pkg update
pkg install python git
git clone https://github.com/FreakingJSON/neuropa.git
cd neuropa
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
neuropa --port 8474
```

Open `http://127.0.0.1:8474` in the Android browser. Android / Termux is a local web runtime, not a native APK. Keep Termux running while using NeuroPA.

## Local-only and OpenCode / Sólo local y OpenCode

- NeuroPA is a local AI Workspace/harness first; executive-function features are a module, not a clinical product. / NeuroPA es primero un Workspace/harness local; las funciones ejecutivas son un módulo, no un producto clínico.
- OpenCode is an optional free CLI path for coding/agent work. The reviewed installer version is pinned: `npm install -g opencode-ai@1.15.6`. The installer records the detected version and never installs Ollama automatically. / OpenCode es opcional y gratuito; la versión revisada está fijada y el instalador nunca instala Ollama automáticamente.
- The public OSS repository is complete for local-first use. Any private SaaS is a separate product and is not required for this setup. / El OSS público está completo para uso local-first. Cualquier SaaS privado es separado y no es necesario.

## Temporary LAN access / Acceso LAN temporal

Only on a trusted network:

```bash
scripts/run-neuropa.sh --lan --port 8474
```

LAN mode is explicit and temporary. It accepts only a private narrow network (IPv4 `/24` or narrower, IPv6 `/64` or narrower) and devices in that trusted network enter directly by default. Add `--pairing` only when you explicitly want the preserved one-time pairing gate; its code stays in the URL fragment and terminal. Stop with `Ctrl+C`; return to loopback-only mode by omitting `--lan`. Never expose LAN mode to the internet or untrusted Wi-Fi. / El modo LAN es explícito y temporal; en la red privada autorizada entra directamente por defecto. `--pairing` conserva el emparejamiento como opción.

## Privacy, egress, and data / Privacidad, salida y datos

Default storage is `~/.local/share/neuropa/` (or the platform equivalent). `NEUROPA_DATA_DIR` can choose another directory. No hidden telemetry is required. If you connect an external provider or OpenCode, prompts and files may leave the machine according to that provider's configuration and policy; local-only operation is the safe default. / Si conectas un proveedor externo, los datos pueden salir según su configuración y política.

### OpenRouter BYOK — free first

NeuroPA accepts an OpenRouter key through the process environment; the key is never written to the SQLite workspace or included in exports:

```bash
export NEUROPA_BYOK_KEY='...'
scripts/run-neuropa.sh
```

PowerShell: `$env:NEUROPA_BYOK_KEY='...'`. Docker: put `NEUROPA_BYOK_KEY=...` in a local `.env` file that is not committed. The default endpoint is `https://openrouter.ai/api/v1`; NeuroPA refreshes the eligible model catalog and places `openrouter/free` and zero-cost `:free` models first. Advanced overrides: `NEUROPA_BYOK_PROVIDER` for another OpenAI-compatible endpoint and comma-separated `NEUROPA_BYOK_MODELS` for explicit additional models. Remote prompts follow the selected provider's policy and limits.

## Backup and export / Copia y exportación

```bash
uv run neuropa --status
uv run neuropa --export backup.json
```

Keep `backup.json` private. Back up the data directory too when you need a full local recovery. / Mantén privado el JSON y copia también el directorio de datos para una recuperación completa.

From Workspace, **Exportar sesión** offers JSON, Markdown (`.md`), and a self-contained **SPA-HTML offline** transcript. The HTML needs no CDN or backend and includes local search plus author filtering. In Ajustes, **Importar backup JSON** validates the backup and requires explicit confirmation before atomically replacing the local workspace. Full backups also include the owner-editable `SOUL.md` and `AGENTS.md` identity layers; old backups without these fields remain compatible. Conversations remain sessions; this does not convert them into saved deliverables.

## Troubleshooting / Resolución de problemas

- **`uv` missing / falta `uv`:** the installer fails closed and never executes a remote shell. Install it manually from the [official uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/), then rerun `scripts/install.sh`.
- **OpenCode missing / falta OpenCode:** install Node.js/npm, then run `npm install -g opencode-ai@1.15.6`. It is optional and the installer asks for confirmation unless `--yes` was explicitly supplied.
- **Port busy / puerto ocupado:** use another one, for example `scripts/run-neuropa.sh --port 9000`.
- **Browser did not open / no se abrió el navegador:** open `http://127.0.0.1:8474` manually.
- **Stop / detener:** press `Ctrl+C`. User data is not deleted by stopping or by the default uninstall.
- **Clean repo environment / limpiar entorno:** `scripts/uninstall.sh --dry-run`, then `scripts/uninstall.sh`. It removes only `.venv` and known repo caches. `--purge-data` requires typing exactly `PURGE NEUROPA DATA`.

## For contributors / Para contribuidores

```bash
uv sync --extra dev
uv run pytest -q
```

### Reproducible frontend QA

Run these commands from the repository root and use the project environment (not an external `VIRTUAL_ENV`):

```bash
uv sync --dev
uv run playwright install chromium
uv run python tools/qa_frontend.py
```

The QA runner fails closed when Playwright or Chromium is unavailable. It regenerates `docs/evidence/qa-v2/` at desktop (1600×1000), tablet (768×900), and mobile (480×860), requiring 44px actionable targets at every viewport, zero JavaScript/console/HTTP errors, no horizontal overflow, and the expected mobile navigation.

See [CONTRIBUTING.md](../CONTRIBUTING.md), [LICENSES.md](../LICENSES.md), and [LICENSE](../LICENSE) for contribution, attribution, and licensing details.
