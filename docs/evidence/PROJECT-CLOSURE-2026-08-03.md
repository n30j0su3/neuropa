# NeuroPA — Cierre del proyecto

**Fecha:** 2026-08-03  
**Repositorio:** `https://github.com/n30j0su3/neuropa`  
**Rama:** `main`  
**Estado de cierre:** `READY_TO_PUBLISH`

## Resumen ejecutivo

NeuroPA queda cerrado como **P0 funcional y verificable**: un AI Workspace / harness local-first, sin cuenta obligatoria, sin telemetría oculta y con un camino real de uso mediante OpenCode gratuito. La implementación no se amplía a P1 en este cierre; FTS5/SourceRef, streaming, contexto seleccionable, provenance avanzada, keyring y empaquetado firmado quedan como roadmap condicionado a validar el pivote con beta users.

## Evidencia final

| Gate | Resultado |
|---|---:|
| `uv run pytest -q --disable-warnings` | **43 passed** |
| `python3 -m compileall -q neuropa tests tools` | **PASS** |
| `bash -n scripts/install.sh scripts/run-neuropa.sh scripts/uninstall.sh` | **PASS** |
| `git diff --check` | **PASS** |
| Browser QA 1600 / 768 / 480 | **PASS** |
| JavaScript, console y HTTP errors | **0 / 0 / 0** |
| Horizontal overflow | **0 en las 3 vistas** |
| Touch/action targets | **mínimo 44px en las 3 vistas** |
| Dozer QA | **PASS; sin blocker/HIGH** |
| Seraph security review | **PASS; sin blocker/HIGH** |
| OpenCode gratuito live | **`LAN_AI_OK`** |

## Alcance efectivamente cerrado

- API local FastAPI + SQLite/WAL + SPA sin build.
- Sesiones, mensajes, workspaces, memoria y artifacts Markdown con containment y SHA-256.
- Modos Creativity, Clarity, Detail y Memory.
- Persistencia de provider/model/mode y enforcement de `local_only`.
- Pairing LAN one-time con cookie HttpOnly, SameSite Strict y host binding.
- Protección de master token, import atómico, aislamiento de workspace OpenCode y prompt por stdin.
- Installer sin ejecución remota mutable y con OpenCode fijado a `1.15.6`.
- QA reproducible en desktop, tablet y mobile.

## Residual conocido

Queda una nota **MEDIUM no bloqueante**: un cliente WebSocket no-browser con cookie válida y sin header `Origin` puede ser aceptado. Los Origins cruzados se rechazan, el query-token LAN se rechaza y la cookie es host-bound. La corrección estricta queda como hardening futuro si el producto adopta un contrato browser-only.

## Decisión de producto

El siguiente trabajo **no se inicia automáticamente**. El plan canónico `docs/product/PLAN-2.0-HARNESS.md` exige validar el pivote con cinco beta users antes de invertir en Week 1 (FTS5 + SourceRef). Esto evita convertir el roadmap en trabajo especulativo.

## Publicación y superficies

- Repositorio público: publicar los commits locales pendientes después de este cierre.
- Wiki interna: registrar este cierre y sus gates.
- Memoria permanente: conservar únicamente el resultado y el puntero a esta evidencia.
- No se publican paths internos, credenciales, tokens ni configuración privada.
