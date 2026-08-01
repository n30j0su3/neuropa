# Changelog

Todos los cambios relevantes de NeuroPA se documentan aquí.

## F2 — Frontend premium

- Añadida la SPA frontend funcional servida por la API local.
- Incorporados flujos visibles para Today, captura, memoria y foco.
- Añadida una experiencia de interfaz orientada a reducir fricción y recuperar contexto.

## F1 — Flujos de producto

- Expuestos endpoints de inbox, Today, memoria y sesiones de foco.
- Añadida exportación e importación JSON de entidades.
- Añadida selección de proveedores con fallback y controles de privacidad.
- Añadidas pruebas de integración para memoria, Today y WebSocket de foco.

## F0 — Fundación local-first

- Creado el modelo de dominio con entidades para inbox, tareas, proyectos, recordatorios, memoria y más.
- Añadida persistencia SQLite con migración inicial, índices y modo WAL.
- Añadida API FastAPI limitada a loopback con token local de permisos restringidos.
- Añadida base de proyecto Python gestionada con `uv`.
