# Contribuir a NeuroPA

Gracias por querer mejorar una herramienta que reduce fricción para personas con TDAH.

## Flujo

1. Abre una issue o describe claramente el cambio en el pull request.
2. Crea una rama desde la base actual: `git switch -c feat/nombre-corto`.
3. Mantén el cambio pequeño, local-first y compatible con la privacidad.
4. Añade pruebas para cualquier comportamiento nuevo o corregido.
5. Ejecuta `uv run pytest -q` antes de abrir el PR.

## Estilo de commits

Usa commits atómicos con Conventional Commits, por ejemplo:

- `feat: add keyboard capture shortcut`
- `fix: preserve inbox text during update`
- `docs: clarify local data paths`
- `test: cover export roundtrip`

Un commit debe representar una sola intención y no debe incluir secretos, bases de datos ni archivos generados.

## Pull requests

Incluye qué cambió, cómo se verificó y cualquier decisión de privacidad relevante. Las nuevas dependencias necesitan una justificación clara. Para cambios de interfaz, añade una captura o describe el flujo afectado.
