# NeuroPA

> **AI Workspace / local-first harness** para pensar, crear y trabajar con memoria persistente. Las funciones de executive function son un módulo del workspace, no la identidad completa del producto.

[![Licencia: AGPL-3.0](https://img.shields.io/badge/licencia-AGPL--3.0-blue.svg)](LICENSE)

## Qué es

NeuroPA es **el espacio preconfigurado** para usar IA gratis, fácil y sin parte técnica. Open source (AGPL-3.0), local-first: tus sesiones, tu memoria y tus guardados viven en tu dispositivo. Elige entre IA gratuita (OpenCode), local (Ollama) o tu propia clave (OpenRouter) — sin cuenta, sin suscripción obligatoria y sin telemetría.

No hace claims clínicos, no diagnostica y no sustituye atención profesional. La experiencia pública OSS está diseñada para funcionar completa localmente, sin cuenta ni SaaS obligatorio.

## Quick start sin conocimientos técnicos

```bash
git clone https://github.com/n30j0su3/neuropa.git
cd neuropa
scripts/install.sh
scripts/run-neuropa.sh
```

Después abre `http://127.0.0.1:8474`. Para revisar sin cambiar nada: `scripts/install.sh --check`. Para automatización explícita: `scripts/install.sh --yes`.

Guía bilingüe: [docs/SETUP.md](docs/SETUP.md). Manual de uso: [docs/MANUAL-DE-USO.md](docs/MANUAL-DE-USO.md). Prompts iniciales: [docs/PROMPTS-INICIALES.md](docs/PROMPTS-INICIALES.md).

## Uso diario

```bash
# Local-only (por defecto)
scripts/run-neuropa.sh

# LAN temporal en una red de confianza
scripts/run-neuropa.sh --lan --port 8474

# Opcional: exigir emparejamiento de un solo uso
scripts/run-neuropa.sh --lan --pairing --port 8474

# Estado y exportación
uv run neuropa --status
uv run neuropa --export backup.json

# Versión
uv run neuropa --version
```

Detén el proceso con `Ctrl+C`. Tus datos permanecen en tu equipo.

## Arquitectura pública / privada

- **Público OSS:** `neuropa/`, CLI, API local, frontend, almacenamiento local, harness y módulos de workspace. Es el camino completo local-first.
- **Privado/separado:** cualquier SaaS gestionado, sincronización, colaboración o servicios operados por terceros. No es necesario para instalar ni usar el OSS público y sus políticas de datos son distintas.

Por defecto la base de datos y el token viven en `~/.local/share/neuropa/` (o la ruta equivalente del sistema). `NEUROPA_DATA_DIR` permite elegir otra ubicación. No se requiere telemetría oculta. Al conectar proveedores externos u OpenCode, revisa qué prompts/archivos pueden salir del equipo.

## OpenCode y Ollama

OpenCode es un CLI gratuito opcional para trabajo de código/agentes. El instalador lo detecta y puede ofrecer `npm install -g opencode-ai` sólo con confirmación. Ollama no se instala automáticamente; si deseas usarlo, instálalo y configúralo por separado.

## Features

- AI Workspace/harness local-first con memoria persistente.
- Captura rápida tipo inbox, sin clasificación obligatoria.
- Módulo executive-function: Today, siguiente acción, parking lot y Focus.
- Memoria con evidencia y fuentes.
- API local protegida por token loopback.
- Exportación JSON para copias y portabilidad.
- Router preparado para proveedores locales, BYOK o gestionados.
- SQLite local con migraciones y modo WAL.

## Para developers

```bash
uv sync --extra dev
uv run pytest -q
```

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo de contribución.

## Créditos y licencias

NeuroPA se distribuye bajo [GNU Affero General Public License v3.0](LICENSE). El mapa de licencias, atribuciones upstream y el límite del SDK están documentados en [LICENSES.md](LICENSES.md); el SDK futuro conserva [Apache-2.0](LICENSE.sdk-Apache-2.0). Las contribuciones siguen [CONTRIBUTING.md](CONTRIBUTING.md).
