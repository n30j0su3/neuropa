# NeuroPA — Plan P2 Fixes 2026-08-05

**Origin:** N30 mensajes `1534586744215834805` / `1534586925225087139`  
**Checkpoint previo:** `docs/plans/2026-08-05-checkpoint-p2-pre-fix.md`  
**HEAD:** `81c6929c39f318742fb2fc4fe9818b4f3e573e82`

## Matriz de fixes

| # | Fix | Categoría | Prioridad | Esfuerzo | Origen file:line |
|---|-----|-----------|-----------|----------|-------------------|
| F1 | Aside fijo, no afectado por scroll de section | CSS layout | P0 | S | `index.html` L10 `.shell{display:grid}`, L141 `shell()` |
| F2 | Composer descentrado en Desktop vs transcript | CSS layout | P0 | S | `index.html` L53 `.composer{max-width:920px}`, L149 `composer()` |
| F3 | Provider control no permite elegir OpenRouter | Backend+Frontend | P1 | M | `router.py:157` `byok.available=bool(self.byok_key)`, `index.html:161` `renderProviderOptions` |
| F4 | Artifacts de sesión no se ven/descargan | Backend+Frontend | P1 | L | `harness.py:278` `create_artifact`, `index.html:207` `messageNode` |
| F5 | Memoria: editar claim + Wiki auto-populada | Backend+Frontend | P2 | L | `app.py:635` supersede, `app.py:564` wiki, `memory/wiki.py` |
| F6 | Título "Guardados" → "Guardados / Artifacts" | Frontend | P0 | XS | `index.html:124` navItems, L237 `renderArtifacts` |
| F7 | Reordenar Ajustes | Frontend | P0 | XS | `index.html:240` `renderSettings()` |

## Detalle por fix

### F1 — Aside fijo (P0, CSS)

**Problema:** `.shell` es `display:grid` con `grid-template-columns:248px minmax(0,1fr)`. El aside (`.primary-rail`) está en el flujo normal del grid; cuando el `.stage` scrollea, el aside se desplaza con la página porque no tiene `position:fixed`/`sticky`.

**Fix:** En desktop (>1100px), hacer `.primary-rail` `position:sticky` con `height:100vh` y `overflow-y:auto`. En móvil (≤700px) ya es `position:fixed` bottom bar — sin cambio.

**Cambio:**
```css
/* L10 - añadir a .primary-rail existente o nueva regla */
.primary-rail{position:sticky;top:0;height:100vh;overflow-y:auto}
```

### F2 — Composer descentrado en Desktop (P0, CSS)

**Problema:** `.transcript` tiene `max-width:920px;margin:0 auto` y `.composer` tiene `max-width:920px;margin:0 auto`, pero `.composer-wrap` tiene `padding:10px clamp(16px,4vw,60px)`. El padding del wrapper más el max-width del composer crean una asimetría con el transcript cuando el viewport >920px+padding. El form dentro del composer no hereda el centrado del max-width.

**Fix:** Asegurar que `.composer-wrap > .composer` herede el mismo centro que `.transcript` alineando ambos al mismo `max-width` + `margin:0 auto` o usando un contenedor compartido.

**Cambio:**
```css
.composer{max-width:920px;margin:0 auto}
/* En L147 renderWorkspace - el form del composer está dentro de .composer-wrap */
/* Verificar que .composer-wrap no añade padding asimétrico */
```

### F3 — OpenRouter no seleccionable (P1, Backend+Frontend)

**Problema:** `byok.available = bool(self.byok_key)` (router.py:157). Si `NEUROPA_BYOK_KEY` no está en el entorno, BYOK aparece como no disponible y el provider-control lo filtra con `providerEntries().filter(([,v]) => v.available !== false)` (index.html:160). OpenRouter debería ser seleccionable incluso sin API key (modo free-first con `openrouter/free`).

**Fix:**
- **Backend:** `byok.available = True` cuando el provider es OpenRouter (siempre que el endpoint sea `openrouter.ai`). El catálogo free no requiere key.
- **Frontend:** Mostrar BYOK/OpenRouter como opción seleccionable aunque no tenga key configurada, con etiqueta "GRATIS" si usa `openrouter/free`.

### F4 — Artifacts de sesión invisibles e indescargables (P1, Backend+Frontend)

**Problema:** Cuando un agente produce código HTML/SPA en una respuesta (ej: "reporte-ia-local.html"), el mensaje se guarda como texto plano en `ChatMessage.content`. El sistema de artifacts actual (`harness.py:278`) crea un `.md` a partir del mensaje completo — no parsea bloques de código ni archivos individuales. El frontend (`messageNode`, L207) muestra `body.textContent = message.content` — no renderiza HTML ni detecta bloques de código. No hay botón de descarga por artifact inline.

**Fix (YAGNI — 3 sub-fixes):**
1. **Detección automática:** `harness.py` parsea bloques ```` ```html ````/```` ```python ```` en respuestas del assistant y los extrae como artifacts individuales con tipo detectado (html, python, js, etc.).
2. **Renderizado en mensaje:** `messageNode` detecta artifacts en el mensaje y renderiza: preview colapsable para HTML, syntax highlight básico para código, y botón "Descargar" por cada artifact.
3. **Canvas de artifact:** `openArtifact` ya existe (L302) pero actualmente carga contenido desde `/api/artifacts/{id}` — extender para servir el contenido real del archivo y permitir descarga directa.

### F5 — Memoria: editar claim + Wiki auto-poblada (P2, Backend+Frontend)

**Problema A:** "Corregir memoria" (supersede, L230 `openSupersedeModal`) sólo permite introducir texto nuevo + fuente manualmente. No permite editar el claim existente in-place.

**Fix A:** Cambiar `openSupersedeModal` para precargar el texto del claim existente en el textarea, permitiendo editarlo en lugar de empezar de cero. El backend ya soporta supersede con texto arbitrario.

**Problema B:** La Wiki (`/api/wiki/pages`) está vacía. Las páginas se crean manualmente vía API. Deberían poblarse automáticamente cuando se almacenan/editan claims de memoria, siguiendo el patrón Karpathy LLM-Wiki que ya usamos en Hermes (scripts/flows sin LLM permanente).

**Fix B (YAGNI — script determinista):**
- Un hook en `memory.store_claim()` y `memory.supersede_claim()` que escriba automáticamente una página Wiki en `data_dir/wiki/` usando un template determinista (slug del claim → archivo `.md` con frontmatter + claim + fuente + fecha).
- El agente/modelo que interactúa con NeuroPA puede enriquecer estas páginas, pero la creación/persistencia base es determinista.
- No depende de un LLM permanente para el mantenimiento base.

### F6 — Título "Guardados" → "Guardados / Artifacts" (P0, XS)

**Fix:** `index.html:124` navItems cambiar `'Guardados'` → `'Guardados / Artifacts'`. L237 `renderModule('Guardados',…)` → `renderModule('Guardados / Artifacts',…)`.

### F7 — Reordenar Ajustes (P0, XS)

**Orden actual (L240):** Perfil → Capas permanentes → Modos → Configuración inicial → Provider → Privacy

**Orden solicitado:** Provider → Configuración inicial (wizard) → Perfil → Capas permanentes → Modos → Skills/MCP → resto

**Fix:** Reordenar los `make('section',…)` en `renderSettings()`.

## Orden de ejecución propuesto

1. **F6 + F7** (XS, 5 min) — quick wins de UI
2. **F1** (CSS, 10 min) — aside sticky
3. **F2** (CSS, 10 min) — composer alignment
4. **F3** (Backend+Frontend, 30 min) — OpenRouter seleccionable sin key
5. **F4** (Backend+Frontend, 60 min) — artifacts parse + view + download
6. **F5** (Backend+Frontend, 90 min) — memory edit + wiki auto-populate

## Gates

- `compileall + pytest -q --tb=short` después de cada fix de backend
- `node --check` del JS inline extraído después de cada fix de frontend
- Browser QA 3 breakpoints (480/768/1600) después de F1+F2
- Smoke runtime `:8474` después de F3+F4
- N30 human QA final
