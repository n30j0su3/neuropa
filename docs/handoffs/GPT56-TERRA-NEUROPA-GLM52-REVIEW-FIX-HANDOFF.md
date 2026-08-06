---
title: NeuroPA — revisión zero-trust de GLM-5.2 y paquete de corrección
date: 2026-08-04T17:21:52-05:00
reviewer: gpt-5.6-terra via OpenAI Codex
fix_executor: glm-5.2 via Z.AI
final_reviewer: gpt-5.6-sol via OpenAI Codex
status: PASS_FOR_N30_HUMAN_GATE
---

# Veredicto

`PASS_FOR_N30_HUMAN_GATE` tras remediación y revisión zero-trust final. Los hallazgos
originales quedan preservados abajo como historial; la sección **Cierre de ejecución**
documenta los fixes y las verificaciones frescas que levantaron el bloqueo.

## Evidencia independiente

- `python3 -m compileall -q neuropa tests` — exit 0.
- `uv run pytest -q --tb=short` — `108 passed`, 1 warning deprecado de Starlette.
- `git diff --check` — exit 0.
- Repro de exportación: al guardar `{"api_key":"LEAK-ME"}` en `workspace.settings`,
  `POST /api/export/selected` devuelve ese valor en claro (`HTTP 200`).
- Repro de profile: actualizar `default_provider` a `profile-provider`, crear sesión y
  enviar sin provider explícito hace que el router reciba `mode=None`.
- `grep` de `neuropa/frontend/index.html`: cero llamadas a `/api/profile`,
  `/api/export/selected`, `/api/wiki`, `/api/skills` y `/api/mcp-servers`.

## Bloqueantes

### B1 — Export selectivo filtra secretos

**Dónde:** `neuropa/api/app.py`, `export_selected()`.

El scanner ocurre después de serializar y devolver `entities`; sólo añade un warning.
No redacta ni bloquea los valores. La propia declaración `omitted_secret_declaration`
es falsa para claves dentro de `workspace.settings` y campos anidados equivalentes.

**Fix mínimo:** implementar una copia recursiva que omita claves case-insensitive que
contengan `token`, `api_key`, `secret`, `password`, `credential`, `authorization`,
`oauth` o `pairing_code`, antes de hashear y devolver datos. Si se descubre un secreto
en una cadena no asociada a clave, omitir sólo esa cadena o rechazar el export con 422;
no retornar el secreto con un warning.

**Tests requeridos:**

1. workspace settings con `api_key`, `nested.token` y texto normal;
2. respuesta sin secretos, con campo de declaración `redacted_keys`;
3. hashes calculados sobre la versión redactada;
4. no regresión: se conservan campos no secretos.

### B2 — AgentProfile no gobierna provider/mode realmente

**Dónde:** `neuropa/services/harness.py`, `create_session()` y `send_message()`.

Sólo se concatena `system_prompt`. `default_provider` y `default_mode_id` no se usan
como fallback para crear una sesión ni para llamar al router. El dato se persiste pero
no controla el comportamiento prometido.

**Fix mínimo:**

- En `create_session`, si no se pasa `provider_id` o `mode_id`, usar el profile primary.
- En `send_message`, resolver `provider = provider or profile.default_provider` y el
  modo profile cuando no exista una selección explícita de sesión/call.
- Mantener precedencia explícita: argumento de la llamada > sesión > AgentProfile >
  default heredado actual.

**Tests requeridos:** provider y mode de profile se consumen cuando faltan argumentos;
argumento y sesión tienen precedencia; profile update persiste tras reiniciar Database.

### B3 — UI no conecta ninguna superficie nueva

**Dónde:** `neuropa/frontend/index.html`, especialmente `renderSettings()` y
`renderMemory()`.

Los endpoints de profile, export selectivo, Wiki, Skills y MCP existen sólo en backend.
Ajustes sigue mostrando el export anterior (`exportData`) y Memoria no muestra Wiki.
Por tanto B1/B5/C1 no son funcionales para la persona usuaria.

**Fix mínimo:**

- Ajustes: card de Perfil (nombre visible, prompt, provider/mode, guardar), inventario
  read-only de Skills/MCP y selección explícita de secciones para exportar.
- Memoria: pestaña Wiki con índice, lectura de página, búsqueda y lint visible.
- No añadir framework ni rutas nuevas: usar el mismo SPA single-file y `api()` existente.

**Browser tests requeridos:** save/reload de profile; export selectivo descarga JSON
redactado; Wiki create/search/read; desktop 1600, tablet 768 y móvil 480 sin overflow,
con console/page errors a cero.

## Mejoras obligatorias antes de C1/C2/C3/C4

### H1 — La Wiki no implementa backlinks ni relaciones verificables

`related_concepts` se serializa, pero no hay backlinks ni estructura de relación
consumible por el grafo. Es incompatible con el patrón Understory acordado.

**Fix:** crear un índice de backlinks al guardar, o derivarlo determinísticamente al
leer/lint; validar referencias de cualquier tipo (`concept`, `entity`, `query`, etc.),
no sólo `concepts/` y no según el orden de `glob()`.

### H2 — `lint()` silencia corrupción y produce falsos resultados

`list_pages()` atrapa `Exception` y descarta páginas; `lint()` sólo atrapa `ValueError`.
Un YAML válido con forma no-mapping puede disparar `TypeError` en read/lint. La revisión
no debe ocultar páginas inválidas.

**Fix:** validar que frontmatter sea `dict`; en `lint`, devolver siempre un issue
estructurado (`invalid_frontmatter`, `unreadable_page`) en vez de descartar.

### H3 — Contrato Wiki incompleto en tipo/filtros

`list_pages(wiki_type="invalido")` devuelve `[]` en vez de 400; el `type` de la página
puede diferir del directorio. Validar tipo antes de listar y al leer comprobar que
frontmatter `type` coincide con la ruta solicitada.

## Restricciones de ejecución

- No tocar `:8474`, `:7865`, LAN/pairing/token/auth ni providers productivos.
- No reset/restore/commit; trabajar sólo encima del worktree actual.
- Conservar `#0f1117` + `#40E0E0`, sin CDN/frameworks, `prefers-reduced-motion` y
  controles ≥44px.
- B2/B3/B4 de OpenCode quedan fuera: requieren aprobación específica por su stop
  condition interactiva/global.

## Baseline de custodia

| Archivo | SHA256 |
|---|---|
| `neuropa/api/app.py` | `c546fe9cae1cd16d2e309d196f86a46f453899d3a3070e723b3da140b2300df5` |
| `neuropa/services/harness.py` | `077e636fec387541054a83dd9f2d9b63a2ef74a1d5d1f6e1de07fc57ca80721a` |
| `neuropa/domain/models.py` | `69611cdfa266f2f3955aa04715757c2937d362627520c69350ac504efc07e64c` |
| `neuropa/memory/wiki.py` | `5f7c34e10dae4f3e8ab9d2dd27033de964d28877b831771a26463edbd1b22532` |
| `neuropa/frontend/index.html` | `a0fed0aaaf14802cc57b17b3b5f83a136c3ac25ebab4b62140392503c4b11ce4` |

## Handoff acceptance gate

1. Focused red/green tests for B1–B3 and H1–H3.
2. `python3 -m compileall -q neuropa tests`.
3. `uv run pytest -q --tb=short`.
4. `git diff --check`.
5. Browser journey against an isolated temporary data dir at 1600/768/480.
6. Reviewer reruns the secret-leak and profile-fallback repros; both must fail safely.

## Cierre de ejecución — gpt-5.6-sol

Fecha: `2026-08-04T18:36:25-05:00`.

La revisión final encontró y cerró cuatro gaps adicionales que la primera ejecución de
GLM-5.2 no cubría:

1. `_all_page_refs()` y `lint()` todavía pluralizaban `entity/query` como
   `entitys/querys`; `notes/` tampoco formaba parte del bundle global.
2. `lint()` llamaba a `backlinks()` antes de completar el análisis, por lo que un YAML
   malformado podía hacer fallar el propio lint.
3. `_validate_model()` recibía el provider explícito original, no el
   `resolved_provider` heredado del AgentProfile.
4. La Wiki se renderizaba dentro de un inspector oculto en móvil y no tenía control
   visible de apertura en desktop/tablet. El profile UI tampoco exponía provider/mode.

Correcciones aplicadas:

- mapeo canónico type↔directory para todos los tipos, incluyendo `notes/`;
- backlinks sobre páginas válidas de cualquier tipo y lint tolerante a corrupción;
- errores API `400` para tipos Wiki y secciones de export desconocidas;
- validación de catálogo sobre `resolved_provider`;
- Profile UI con provider/mode persistentes para sesiones nuevas;
- control Wiki visible en desktop/tablet y activación real de `inspector-open` en móvil.

Evidencia fresca:

- `compileall` — PASS;
- `node --check` del script SPA — PASS;
- `pytest -q --tb=short` — **123 passed**, 1 warning deprecado de Starlette;
- `git diff --check` — PASS;
- Browser journeys 1600/768/480 — profile save/readback, export download y Wiki
  create/index/read; 0 console errors, 0 failed requests, 0 respuestas HTTP ≥400,
  0 overflow y 0 targets visibles menores de 44px;
- runtime humano `:8474` — HTTP 200 y no modificado;
- runtime efímero `:8589` — destruido tras QA.

Receipt: `docs/evidence/ux-audit-2026-08-04/glm52-final-zero-trust-receipt.json`.

## Cierre del gate visual LAN — N30

Fecha: `2026-08-04T19:51:29-05:00`.

La restricción histórica de no tocar `:8474` quedó supersedida únicamente para este
cierre por el reporte directo de N30 sobre la URL LAN. Se reprodujeron y corrigieron:

1. **Aside colapsado:** `.stage` caía en la columna grid de ancho cero. El shell
   colapsado ahora usa una columna y `.stage` ocupa explícitamente esa columna.
2. **Memory Map:** se sustituyó el layout fijo por force layout determinista con
   separación de colisiones, labels orientadas hacia afuera, fuentes como nodos
   técnicos sin ruido visual, drag de nodos, pan y zoom.
3. **Cambios no visibles:** el proceso vivo era anterior a las rutas nuevas y devolvía
   `404` para Profile, Wiki, Skills, MCP y export selectivo. `:8474` se reinició con
   la CLI canónica `neuropa --lan` y CIDR `192.168.1.0/24`. El pairing quedó luego
   desactivado por decisión de N30 y preservado como opt-in `--pairing`.

Gate fresco:

- `compileall` + `node --check` + `git diff --check` — PASS;
- `pytest -q --tb=short` — **123 passed**;
- Browser QA real en `1600×900`, `768×1024`, `480×900` — 0 solapamientos de
  labels, 0 labels técnicas visibles, 0 overflow, 0 controles <44px, 0 errores de
  consola/request/HTTP; artifact canvas y Profile/Export/Skills/MCP visibles;
- drag de nodo verificado por cambio real de transform SVG;
- runtime `:8474` — health 200 y `/api/profile` autenticado 200.

Receipt: `docs/evidence/ux-audit-2026-08-04/n30-live-8474-visual-fix-receipt.json`.

## Ajustes operables + composer móvil — N30

Fecha: `2026-08-04T20:46:19-05:00`.

- El wizard inicial se puede relanzar desde **Ajustes → Configuración inicial** sin
  borrar sesiones, memoria ni guardados.
- Skills y servidores MCP pasaron de lectura a registro CRUD mínimo: alta,
  edición, activación/desactivación y eliminación. Las altas quedan desactivadas
  por defecto; no existe descarga ni ejecución arbitraria de código.
- El composer móvil se redujo a `149.6px` de alto en `480×900`: textarea inicial
  de una línea, dock progresivo y fila única de estado + Enviar.
- Browser QA real en `1600×900`, `768×1024` y `480×900`: sin overflow,
  sin controles menores de `44px`, wizard reabierto y cero errores API/JS.
- Suite final: **128 passed**; `compileall`, `node --check`, `git diff --check` y
  health `:8474` — PASS.

Receipt: `docs/evidence/ux-audit-2026-08-04/n30-settings-integrations-mobile-receipt.json`.

## Corrección de turno y latencia — N30

Fecha: `2026-08-04T21:33:42-05:00`.

- Causa raíz confirmada en `HarnessService.send_message`: `context_scope=session`
  omitía el mensaje actual del usuario. En una sesión con historial el proveedor
  recibía como último turno la respuesta anterior; en una sesión nueva recibía
  únicamente el prompt de Claridad.
- El mensaje actual ahora se añade exactamente una vez y siempre queda como el
  último mensaje `user`. Los mensajes fallidos ya no vuelven al contexto.
- El contrato de respuesta establece que los modos sólo modifican enfoque/formato;
  nunca reemplazan la solicitud literal ni seleccionan un turno anterior.
- Benchmark real con el mismo prompt: Laguna S 2.1 respondió correctamente en
  `15.882s`; DeepSeek V4 Flash respondió correctamente en `25.189s`. Laguna pasa
  a ser el recomendado gratuito por defecto; una selección manual se respeta.
- Suite final: **132 passed**; runtime `:8474` reiniciado y saludable.

Receipt: `docs/evidence/ux-audit-2026-08-04/n30-chat-correctness-latency-receipt.json`.

## Mobile Composer B — aprobación e implementación N30

Fecha: `2026-08-04T23:22:50-05:00`.

- N30 aprobó el diseño B inspirado en Discord móvil y su ajuste final: textarea
  protagonista, envío visualmente pequeño, configuración mediante icono de sliders
  y chevron principal flotante sin fondo ni borde.
- Se implementaron exactamente dos estados globales: compacto y retraído. El
  retraído conserva textarea + envío y oculta configuración + estado de egress.
- El textarea crece desde 44 px, llega a 110 px con cuatro líneas y se limita a
  132 px en móvil antes de activar scroll interno.
- El envío conserva un hit target de 44×44 px con núcleo visual de 32 px, estado
  neutro cuando está vacío y turquesa cuando puede enviarse.
- La configuración móvil se expande por toque como lista plana de cuatro controles;
  no crea cards redundantes.
- TDD: 2 fallos esperados en RED, 2 pass en GREEN, 37 pass focalizados y **134 pass**
  en la suite completa; `compileall`, `node --check` y `git diff --check` pasan.
- QA real: 480×860, 768×900 y 1600×1000; cero errores de consola y cero overflow
  horizontal. Enter envía; Shift+Enter conserva salto de línea. El request de QA
  fue interceptado para no contaminar una sesión real.
- Runtime `:8474` reiniciado y saludable. Studio `:7865` no fue tocado.

Receipt: `docs/evidence/ux-audit-2026-08-04/n30-mobile-composer-b-receipt.json`.
