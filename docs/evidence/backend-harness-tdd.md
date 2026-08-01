# Backend Harness P0 — evidencia TDD

Fecha: 2026-08-01

## RED

Se añadieron primero `tests/test_opencode_p0.py` y `tests/test_harness_p0.py` para cubrir parser JSONL, ejecutable temporal real, roundtrip de entidades, seed idempotente, persistencia, fallo de provider y artifact. La primera ejecución inicial de la suite detectó un fallo de compatibilidad en `ProviderRouter._call` (firma histórica de tres argumentos).

## GREEN

Se ajustó el router para conservar la firma compatible cuando no se necesita `cwd`. Verificación final ejecutada:

- `python -m compileall -q neuropa tests` — exit 0
- `uv run pytest -q` — 21 passed, 1 warning

Los tests del ejecutable temporal invocan un script real con `subprocess.run(shell=False)`; no se usa mock subprocess en runtime.
