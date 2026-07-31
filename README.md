# NeuroPA

Fundación local-first de NeuroPA: modelo de dominio SQLite con WAL, API FastAPI loopback y núcleo PA Framework vendorado. Datos locales en `~/.local/share/neuropa/` (Linux) o `NEUROPA_DATA_DIR` para pruebas.

## Desarrollo

```bash
uv sync --extra dev
uv run pytest -q
uv run uvicorn neuropa.api.app:app --host 127.0.0.1 --port 8765
```

El token se genera en el primer arranque en `token` con permisos `0600`.
