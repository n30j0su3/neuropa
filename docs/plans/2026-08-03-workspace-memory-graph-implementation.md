# NeuroPA Workspace Control Dock + Memory Graph Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Entregar selectores premium y funcionales de provider/model/mode/context, más un Memory Graph local-first con provenance y supersession confirmada.

**Architecture:** Extender los contratos actuales de `ProviderRouter`, `HarnessService` y `MemoryClaimService`, proyectar el grafo desde entidades existentes y montar UI SVG/JS nativa dentro de la SPA sin build. Mantener persistencia SQLite actual, pairing LAN y separación de credenciales.

**Tech Stack:** Python 3.13, FastAPI, dataclasses, SQLite JSON entity payloads, pytest, HTML/CSS/JavaScript sin build, SVG nativo, Playwright.

---

## Preflight obligatorio

- Worktree: `/home/freakingjson/.config/superpowers/worktrees/neuropa/p1-workspace-memory-graph`
- Branch: `feat/p1-workspace-memory-graph`
- Baseline: `6502a9a886741a8967b48eb09f55a7abd9c6533c`
- No modificar el `main` que sirve la instancia LAN aprobada.
- No publicar ni mergear sin review de Hermes + QA humana N30.

### Task 1: Congelar contratos de provider/model catalog

**Files:**
- Modify: `tests/test_opencode_p0.py`
- Modify: `tests/test_harness_p0.py`
- Modify: `neuropa/providers/opencode_cli.py`
- Modify: `neuropa/providers/router.py`

**Step 1: Write failing tests**

Agregar tests que exijan:

- `OpenCodeCLI.list_models()` conserva múltiples modelos free.
- `ProviderRouter.status()` entrega `models`, `recommended_model`, `privacy` y `cost` por provider.
- Provider no disponible entrega lista vacía y no un modelo ficticio.

**Step 2: Run tests to verify RED**

Run: `uv run pytest tests/test_opencode_p0.py tests/test_harness_p0.py -q`
Expected: FAIL por campos de catálogo ausentes.

**Step 3: Implement minimal catalog contract**

- Normalizar la estructura en `ProviderRouter.status()`.
- Usar `OpenCodeCLI.list_models()` para `opencode_free`.
- No consultar modelos más de una vez por TTL.
- Definir recommended model sólo si aparece en `models`.

**Step 4: Run tests to verify GREEN**

Run: `uv run pytest tests/test_opencode_p0.py tests/test_harness_p0.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_opencode_p0.py tests/test_harness_p0.py neuropa/providers/opencode_cli.py neuropa/providers/router.py
git commit -m "feat: expose provider model catalogs"
```

### Task 2: Añadir context scope persistente y validación de modelo

**Files:**
- Modify: `tests/test_security_remediation.py`
- Modify: `neuropa/domain/models.py`
- Modify: `neuropa/api/app.py`
- Modify: `neuropa/services/harness.py`

**Step 1: Write failing tests**

Cubrir:

- `ChatSession.context_scope` y `context_claim_ids` tienen defaults compatibles.
- API acepta sólo `none`, `session`, `session_memory`.
- `none` no envía historial anterior.
- `session` envía historial reciente.
- `session_memory` añade sólo claims activos seleccionados.
- Claims superseded/inexistentes producen 400.
- `process_summary.sources` guarda IDs realmente usados.
- Modelo ajeno al provider enumerable produce 400 sin llamar al provider.

**Step 2: Run RED**

Run: `uv run pytest tests/test_security_remediation.py -q`
Expected: FAIL por campos/request/context ausentes.

**Step 3: Implement**

- Añadir defaults a `ChatSession`.
- Extender `MessageCreate`/request Pydantic con `context_scope` y `memory_claim_ids`.
- Crear helpers privados en `HarnessService` para validar modelo y construir contexto.
- Delimitar claims como evidencia no-instruccional.
- Persistir selección al completar envío.

**Step 4: Run GREEN**

Run: `uv run pytest tests/test_security_remediation.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_security_remediation.py neuropa/domain/models.py neuropa/api/app.py neuropa/services/harness.py
git commit -m "feat: persist explicit conversation context"
```

### Task 3: Crear proyección y endpoints del Memory Graph

**Files:**
- Create: `tests/test_memory_graph.py`
- Create: `neuropa/memory/graph.py`
- Modify: `neuropa/memory/__init__.py`
- Modify: `neuropa/api/app.py`

**Step 1: Write failing tests**

Exigir:

- Nodos claim y source reales.
- Edges `sourced_from` y `supersedes` sin inferencia ficticia.
- `used_in_session` sólo cuando `process_summary.sources` lo demuestra.
- Filtros de query/source/status/confidence.
- IDs virtuales de source deterministas y sin raw secrets.
- Endpoint de supersede crea claim nuevo, enlaza anterior y preserva ambos.
- No se puede superseder dos veces un claim ya superseded.

**Step 2: Run RED**

Run: `uv run pytest tests/test_memory_graph.py -q`
Expected: FAIL porque módulo/endpoints no existen.

**Step 3: Implement graph projector**

Crear funciones puras:

- `build_memory_graph(db, filters)`
- `normalize_source_node(source_type, source_ref)`
- `claim_status(claim)`

Añadir endpoints:

- `GET /api/memory/graph`
- `POST /api/memory/claims/{claim_id}/supersede`

**Step 4: Run GREEN**

Run: `uv run pytest tests/test_memory_graph.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_memory_graph.py neuropa/memory/graph.py neuropa/memory/__init__.py neuropa/api/app.py
git commit -m "feat: add provenance-first memory graph API"
```

### Task 4: Implementar Control Dock accesible

**Files:**
- Modify: `tests/test_frontend_harness_contract.py`
- Create: `tests/test_workspace_control_dock.py`
- Modify: `neuropa/frontend/index.html`

**Step 1: Write failing static/browser contract tests**

Exigir:

- IDs separados `provider-control`, `model-control`, `mode-control`, `context-control`.
- No `window.prompt(`.
- Roles combobox/listbox/dialog y `aria-expanded`.
- Catálogo filtrado por provider.
- Payload envía provider/model/context_scope/memory_claim_ids.
- Cambio de provider revalida modelo.

**Step 2: Run RED**

Run: `uv run pytest tests/test_frontend_harness_contract.py tests/test_workspace_control_dock.py -q`
Expected: FAIL.

**Step 3: Implement base funcional**

- Crear primitive `selectionPopover()` reutilizable.
- Provider y model como estados independientes.
- Mode con descripción.
- Context con scope y contador de claims.
- Desktop popover, mobile bottom sheet.
- Focus return, Escape y navegación teclado.

**Step 4: Run GREEN**

Run: `uv run pytest tests/test_frontend_harness_contract.py tests/test_workspace_control_dock.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_frontend_harness_contract.py tests/test_workspace_control_dock.py neuropa/frontend/index.html
git commit -m "feat: add premium workspace control dock"
```

### Task 5: Implementar Memory Graph SVG + inspector

**Files:**
- Create: `tests/test_memory_graph_frontend.py`
- Modify: `neuropa/frontend/index.html`

**Step 1: Write failing contracts**

Exigir:

- `/api/memory/graph` consumido.
- Canvas SVG con labels/accessibility fallback.
- Pan/zoom/reset, node drag y neighbor highlighting.
- Filtros query/source/status/confidence.
- Inspector muestra source, confidence, created_at y status.
- Acción “Usar como contexto”.
- Supersede requiere confirmación modal.
- No `innerHTML`.

**Step 2: Run RED**

Run: `uv run pytest tests/test_memory_graph_frontend.py -q`
Expected: FAIL.

**Step 3: Implement graph base**

- Layout inicial determinista.
- Simulación force liviana con `requestAnimationFrame` y límite de ticks.
- SVG edges/nodes/labels.
- Transform de cámara y pointer events.
- Inspector lateral; mobile alterna graph/inspector.
- Lista accesible paralela/fallback para teclado y reduced motion.

**Step 4: Implement management flow**

- Seleccionar/deseleccionar claim para context.
- Modal de corrección con claim nuevo, source y confidence.
- Refetch de graph después de supersede.

**Step 5: Run GREEN**

Run: `uv run pytest tests/test_memory_graph_frontend.py tests/test_frontend_harness_contract.py -q`
Expected: PASS.

**Step 6: Commit**

```bash
git add tests/test_memory_graph_frontend.py neuropa/frontend/index.html
git commit -m "feat: visualize and manage grounded memory"
```

### Task 6: Impeccable polish y QA browser real

**Files:**
- Modify: `neuropa/frontend/index.html`
- Modify: `tools/qa_frontend.py`
- Create: `docs/evidence/p1-workspace-memory-graph/qa.json`
- Create: screenshots under `docs/evidence/p1-workspace-memory-graph/`

**Step 1: Run baseline browser QA against canary**

Levantar puerto aislado, no 8474:

```bash
NEUROPA_DATA_DIR=/tmp/neuropa-p1-canary uv run neuropa --host 127.0.0.1 --port 8475
```

Probar 1600×1000, 768×1024 y 480×900.

**Step 2: Validate real interactions**

- Abrir cada selector y cambiar opciones.
- Verificar filtrado de modelos.
- Crear sesión y recargar persistencia.
- Enviar en `none`, `session`, `session_memory` con router controlado o mock reproducible.
- Buscar claim, abrir graph, pan/zoom/drag/filter.
- Usar claim como context.
- Ejecutar supersede con confirmación.

**Step 3: Impeccable polish pass 1**

Corregir jerarquía, spacing, focus, empty/loading/error states y mobile sheet.

**Step 4: Re-run all viewports**

Criterios:

- 0 errores console/page/HTTP.
- 0 overflow horizontal.
- targets >=44 px.
- focus visible.
- selectors y graph operativos.

**Step 5: Commit**

```bash
git add neuropa/frontend/index.html tools/qa_frontend.py docs/evidence/p1-workspace-memory-graph
git commit -m "test: certify workspace controls and memory graph UX"
```

### Task 7: Regresión, seguridad y review zero-trust

**Files:**
- Review all changed files.

**Step 1: Full regression**

```bash
uv run pytest -q
uv run python -m compileall -q neuropa tests tools
bash -n scripts/install.sh scripts/run-neuropa.sh scripts/uninstall.sh
git diff --check main...HEAD
```

**Step 2: Security checks**

- LAN token endpoint sigue 403.
- Pairing one-time sigue PASS.
- Claims no entran como system instructions.
- No raw secret en graph/source IDs.
- No external CDN/assets.
- No `innerHTML`.

**Step 3: Dozer review**

Revisar función, accesibilidad, legibilidad y estados de error. Cero blocker/HIGH.

**Step 4: Seraph review**

Revisar context injection, IDOR, provenance mutation y LAN auth. Cero blocker/HIGH.

### Task 8: Actualizar roadmap y entregar canary LAN

**Files:**
- Modify: `docs/product/PLAN-2.0-HARNESS.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/evidence/p1-workspace-memory-graph/SUMMARY.md`

**Step 1: Update roadmap after verified implementation**

Marcar P1.1/P1.2 según resultados reales y reordenar P1.3/P1.4. No declarar completo antes de receipts.

**Step 2: Preserve evidence**

Incluir tests, browser matrix, source commit Understory audit, hashes, first-pass/repaired status y residuals.

**Step 3: Final commit**

```bash
git add docs/product/PLAN-2.0-HARNESS.md README.md CHANGELOG.md docs/evidence/p1-workspace-memory-graph/SUMMARY.md
git commit -m "docs: update NeuroPA roadmap after P1 UX slice"
```

**Step 4: Start isolated LAN canary**

Usar un puerto distinto de 8474 y un pairing code fresco. Verificar health, root, pairing y API protegida. Entregar a N30 sólo después de QA completa.

## Definition of Done

- Suite completa verde.
- Browser QA real verde en 1600/768/480.
- Provider/model/mode/context separados, persistentes y reales.
- Graph e inspector consumen datos reales.
- Supersession auditable.
- Seguridad LAN sin regresión.
- Roadmap actualizado con evidencia.
- Branch aislado; `main` y la instancia aprobada no se modifican.
