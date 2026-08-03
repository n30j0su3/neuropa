# NeuroPA Workspace Control Dock + Memory Graph — Design

**Fecha:** 2026-08-03  
**Estado:** APPROVED por N30  
**Baseline:** `main@6502a9a886741a8967b48eb09f55a7abd9c6533c`

## Problema

La sesión y el modelo funcionan, pero la selección de provider/model/mode/context no tiene aún la calidad ni la semántica de un producto premium. Provider y modelo aparecen acoplados; Mode y Context dependen de `window.prompt()`; Context sólo alterna entre session/none. La vista Wiki/Memory permite guardar y buscar claims, pero no entender relaciones, provenance ni versiones.

## Decisión

Implementar un slice P1 incremental y domain-backed, manteniendo la SPA sin build y la arquitectura local-first:

1. Control Dock con provider, model, mode y context separados.
2. Catálogo de modelos filtrado por provider.
3. Context scope real con claims explícitos.
4. Graph API como proyección de entidades existentes.
5. Memory Graph SVG nativo con inspector y supersession confirmada.

No se integra el servidor/UI de Understory ni se crea una segunda base de conocimiento.

## Arquitectura UX

### Composer Control Dock

Cuatro botones tipo combobox, siempre visibles debajo del composer:

- **Provider**: disponibilidad, privacidad, coste y egress.
- **Model**: búsqueda y catálogo filtrado por provider.
- **Mode**: cards compactas con nombre, descripción e intención.
- **Context**: scope y claims seleccionados, con presupuesto visible.

Desktop/tablet usan popover anclado; mobile usa bottom sheet. Escape cierra, flechas recorren opciones, Enter selecciona y el foco vuelve al trigger.

### Modelo de estado

```text
selectedProvider
selectedModel
selectedMode
contextScope: none | session | session_memory
selectedMemoryClaimIds[]
```

Al cambiar provider, se preserva el modelo sólo si pertenece al nuevo catálogo. Si no, se elige el modelo recomendado del provider y se informa el cambio.

### Context behavior

- `none`: system mode + mensaje actual.
- `session`: system mode + hasta 12 mensajes recientes.
- `session_memory`: session + bloque de claims seleccionados, sanitizado y delimitado como evidencia no-instruccional.

Claims inválidos, eliminados o superseded se rechazan. Los IDs realmente usados se guardan en `process_summary.sources`.

## Arquitectura de datos

### Session persistence

`ChatSession` añade defaults compatibles:

```python
context_scope: str = "session"
context_claim_ids: list[str] = field(default_factory=list)
```

La base actual serializa entidades como JSON, por lo que no requiere nueva columna SQL.

### Provider catalog

`ProviderRouter.status()` entrega por provider:

```json
{
  "available": true,
  "description": "…",
  "privacy": "local|network|configured",
  "cost": "free|provider|unknown",
  "models": ["…"],
  "recommended_model": "…"
}
```

`HarnessService` valida que el modelo solicitado pertenezca al catálogo cuando éste sea enumerable.

### Memory Graph projection

Nodos:

- `claim:<uuid>`
- `source:<type>:<normalized-ref>`
- `session:<uuid>` cuando una sesión usó claims
- `artifact:<uuid>` cuando exista relación verificable

Edges:

- `sourced_from`
- `supersedes`
- `used_in_session`
- `derived_from` sólo cuando los datos lo declaren

No se fabrican relaciones por similitud textual.

## Memory Graph UI

La vista se divide en canvas + evidence inspector:

- Pan, zoom, reset y drag.
- Hover resalta primer vecindario.
- Filtros por source, status, confidence y texto.
- Tipo por color; tamaño por grado/confidence.
- Claims superseded y orphans tienen estados visuales distintos.
- Click abre claim, fuente, fecha, confidence y relaciones.
- “Usar como contexto” sincroniza el Control Dock.
- “Corregir memoria” crea un claim nuevo y supersede el anterior tras confirmación.

En móvil, canvas e inspector son tabs/estados de pantalla completa; no una grilla comprimida.

## Seguridad y provenance

- Claims se presentan al modelo como datos citables, nunca como instrucciones.
- Sólo se aceptan IDs presentes y activos en la DB.
- La corrección preserva el claim original y crea una cadena auditable.
- No se exponen tokens, raw provider credentials ni paths fuera del data root.
- El frontend continúa sin `innerHTML` y con `textContent` para contenido no confiable.

## Impeccable gate

- Preservar `#0f1117` + `#40E0D0`.
- Transcript sigue siendo el foco.
- Popovers con jerarquía por spacing, no exceso de cards.
- Targets >=44 px.
- Reduced motion.
- Focus visible y keyboard flow completo.
- QA a 1600/768/480.
- Máximo dos rondas de polish después de la primera implementación funcional.

## Roadmap

1. **P1.1 Workspace Control Dock** — este slice.
2. **P1.2 Memory Graph Foundation** — este slice.
3. **P1.3 Search + SourceRef** — FTS5/BM25 y relaciones projects/artifacts.
4. **P1.4 Event Ledger** — eventos de sesión y replay de rutas.
5. Streaming, desktop packaging, tools execution y SaaS continúan después de cerrar esta base UX/data.

## Criterios de aceptación

- Cero `window.prompt()` para provider/model/mode/context.
- Provider/model son controles separados y modelos se filtran correctamente.
- Mode/context persisten al recargar una sesión.
- Los tres context scopes cambian el request real al provider.
- Memory Graph carga datos reales, filtra y abre inspector.
- Supersession conserva provenance y requiere confirmación.
- Regresión completa y QA browser en tres viewports pasan.
