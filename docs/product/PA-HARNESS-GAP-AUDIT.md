# PA Framework → NeuroPA: auditoría de gap del AI harness

**Fecha:** 2026-08-01  
**Alcance:** auditoría estática, de solo lectura, del checkout original de PA y de `neuropa`.  
**Objetivo:** decidir qué capacidades debe heredar NeuroPA como *AI harness* local, no reconstruir PA completo ni convertir NeuroPA en una app de productividad con un chat añadido.

## Veredicto ejecutivo

NeuroPA ya tiene una base local sólida para el producto ADHD-first: SQLite/WAL, API loopback con token, captura inbox, Today/Focus, memoria con evidencia, export/import JSON y un router local/BYOK/managed. Sin embargo, eso todavía es un **núcleo de productividad con una integración AI puntual**, no un harness: no existe una superficie de chat/sesiones, ejecución de tools, agentes, skills, proyectos/workspaces, artifacts ni configuración de providers gestionable por el usuario.

**Orden recomendado YAGNI:**

1. **P0 — Harness mínimo usable:** chat persistente + sesiones, provider/model selection con local-first y free access, tool registry seguro, un agente principal con contexto y permisos, skills declarativas mínimas, workspace activo y artifacts básicos, configuración local explícita.
2. **P1 — Continuidad y recuperación:** memoria de sesiones searchable, importación del contexto PA/Markdown, proyectos, artifacts versionados, updater seguro, reminders/calendar local.
3. **Defer:** wiki/grafo completo, multi-agent complejo, marketplace de skills, dashboard analítico, cloud sync/colaboración, calendarios externos, MCP remoto y cualquier telemetría.

**Regla de producto:** productivity (Today, Focus, tareas y reminders) es un módulo del harness. El home principal debe ser el espacio de conversación/acción del agente, con captura ADHD como entrada rápida, no el dashboard Today.

---

## Evidencia y método

Se contrastaron estos checkouts reales:

- **PA original auditado:** `/home/freakingjson/Hermes-Stuff/projects/pa-framework/pa-framework-audit/` (commit `d8eabcc`).
- **NeuroPA:** `/home/freakingjson/Hermes-Stuff/projects/neuro-sass/neuropa/` (commit `cec7d93`).
- Suite actual de NeuroPA verificada: `uv run pytest -q` → **17 passed, 1 warning**.

La clasificación distingue entre: **implementado**, **parcial/esquema**, **gap**, y **defer**. La documentación del PA se trata como evidencia de intención; las rutas de código permiten confirmar capacidades reales.

---

## Mapa funcional priorizado

| Dominio | PA aporta | NeuroPA hoy | Decisión para NeuroPA |
|---|---|---|---|
| Chat/sessions | bootstrap, sesión diaria, captura de mensajes, búsqueda y continuidad multi-CLI | no hay chat ni modelo de `Session` expuesto en la API; solo FocusSession/productividad | **P0:** chat persistente y sesiones de conversación |
| Providers/free access | `MultiEngine`, Ollama, OpenAI-compatible, mock, fallback | router managed → BYOK → local; Ollama/OpenAI-compatible heredados | **P0:** local primero, Ollama/free access, BYOK explícito y health/status; corregir orden de privacidad |
| Agents | agente principal + ContextScout, SessionManager, DocWriter, FeatureArchitect y permisos | no hay agentes ni delegación | **P0:** un agente principal; **P1:** subagentes acotados |
| Tools | tools declaradas en agente; `ToolRegistry` y executor de skills | no registry/executor/API de tools | **P0:** registry de tools con allowlist, confirmación y trazabilidad |
| Skills | catálogo modular, discovery-first, manifests y executor TOML | entidad `Skill` sin loader/runtime/API | **P0:** skills locales declarativas mínimas |
| Artifacts | archivos Markdown, exports `.pa-export`, KB y workspaces | entidad `Artifact` sin endpoints ni blob/version lifecycle | **P0:** resultado/archivo como artifact básico; versionado/links en P1 |
| Projects/workspaces | `project_register.py`, registry SQLite/Wiki/JSON/Markdown, `workspaces/` por disciplina | entidad `Project` sin CRUD; `project_id` solo en `Task`; sin workspace | **P0:** un workspace activo + projects CRUD mínimo |
| Memory/wiki | 4 capas: sessions MD, Memory MD, SQLite, Wiki; pipeline, search BM25, extraction | `MemoryClaim` con evidencia y búsqueda literal; no sesiones conversacionales/wiki | **P0:** memoria de sesión y claims; **P1:** búsqueda; wiki defer |
| Installer/config/updater | `install.py`, launchers, providers JSON/YAML, `update.py` con backup/migraciones | `uv/pip` install, env vars, `--status`, export/import; no config UX/updater | **P0:** setup/config local sin claves hardcodeadas; **P1:** updater preservando datos |
| Calendar/reminders | PA no presenta un calendario operativo central | modelos `Reminder` y `CalendarEvent`, sin API/worker/UI | **P1:** recordatorios locales; calendar externo defer |

---

# 1. Chat y sessions — **P0**

### Qué heredar del PA

- Bootstrap de contexto antes de actuar: `core/scripts/session_start.py`, `core/scripts/context_loader.py`, `core/INIT-PROTOCOL.md`.
- Ciclo de vida de sesión: `core/scripts/session_start.py`, `core/scripts/session_end.py`, `core/scripts/session_saver.py` y `core/scripts/session_indexer.py`.
- Captura en tiempo real de user/assistant/tool/system mediante `core/scripts/message_hook.py` y `core/scripts/session_bridge.py`.
- Búsqueda histórica con filtros y ranking documentada en `docs/knowledge-management/README.md`, implementada alrededor de `core/scripts/session_search.py`.
- Continuidad y coordinación: `core/memory/session_memory.py`, `core/scripts/multi_cli_coordinator.py`, `core/scripts/file_lock.py`.

### Gap actual

`neuropa/api/app.py` solo expone inbox, clarify, memory, Today, Focus y export/import. No hay `/api/chat`, mensajes, conversaciones ni sesiones AI. `neuropa/domain/models.py` contiene `FocusSession`, pero no un modelo de conversación. Las 17 pruebas cubren productividad/memoria/provider fallback, no continuidad de chat.

### Mínimo P0

- `Conversation`/`Message` persistidos en SQLite, con roles `user`, `assistant`, `tool`, `system` y `provider/model` metadata.
- Crear, reabrir, listar y cerrar sesiones; recuperar las últimas N intervenciones al iniciar.
- Streaming opcional solo si el provider local lo permite; no construir un sistema de realtime distribuido.
- Botón/acción **Guardar en memoria** y captura automática configurable; nunca capturar contenido sin una opción clara del usuario.
- Context window pequeño y determinista; resumir solo cuando sea necesario.

**No heredar:** la obligación rígida de escribir cada intercambio en varios formatos. Una fuente primaria SQLite + export Markdown es suficiente para P0.

---

# 2. Providers y free access — **P0**

### Qué heredar

- Interface `EngineBase` (`list_models`, `generate`, `health`) y engines en `core/providers/multi_engine.py`.
- Ollama local, OpenAI-compatible y mock de emergencia del PA.
- Configuración de ejemplo en `core/providers/providers.example.json` y guía en `docs/SETUP-STANDALONE.md`.
- Fallback/circuit breaker/retry como patrón, no como motivo para soportar docenas de vendors.

### Estado actual NeuroPA

`neuropa/providers/router.py` ya tiene managed, BYOK y local, privacidad sensible forzada a local, retry/circuit breaker y `/api/providers/status`. `neuropa/core/providers/multi_engine.py` contiene `OllamaEngine`, `OpenAICompatEngine`, `MockEngine` y routing por modelo. `pyproject.toml` ya incluye `httpx` y `pyyaml`.

### Gap/riesgo

- El router declara cadena `managed → BYOK → local` (`neuropa/providers/router.py:70-72`), que contradice el objetivo 100% local por defecto. El harness debe preferir **local → free/managed opcional → BYOK**, con consentimiento explícito para egress.
- No hay UI ni endpoints para administrar providers, modelos, costes, privacidad, health o prioridad.
- `clarify()` exige JSON perfecto (`json.loads`), sin parser tolerante/fallback seguro.
- El estado `mock` aparece en `fallback_chain` pero no se usa en `generate`.

### Mínimo P0

- Ollama (o servidor OpenAI-compatible local) como camino de instalación gratuita/offline.
- Provider managed opcional y BYOK opcional, siempre visibles y opt-in.
- Perfil de provider: nombre, endpoint, modelo, credencial referenciada por entorno/secret local, `privacy_label`, `cost_label`, health.
- Selección por sesión/tarea: local por defecto; `privacy_sensitive=true` no puede salir a red.
- Registro de provider/modelo/latencia/tokens en cada respuesta, sin telemetría externa.

**Defer:** OAuth, billing, marketplace, fine-tuning, routing semántico avanzado y optimización multi-modelo.

---

# 3. Agents — **P0/P1**

### Qué heredar

El PA define un agente principal y roles claros en:

- `core/agents/pa-assistant.md`: workflow de 7 pasos, detección de complejidad, validación, preservación, herramientas y permisos.
- `core/agents/AGENTS.md`: `FreakingJSON-PA`, `context-scout`, `skill-finder`, `session-manager`, `doc-writer`, `feature-architect`, `sync-propagator`.
- `core/agents/subagents/context-scout.md`: read-only y verifica rutas antes de recomendar.
- `core/agents/subagents/session-manager.md`: ciclo de sesión, locks y cierre.

### Gap actual

NeuroPA no tiene definición de agente, prompt de sistema persistente, delegación, permisos, ejecución planificada ni trazabilidad de pasos. `ProviderRouter.clarify()` es una función de transformación de inbox, no un agente general.

### Mínimo P0

- Un `NeuroPA` primary agent con contexto de la sesión y workspace activo.
- Contrato de ejecución: entender → plan corto → pedir confirmación para acciones riesgosas → ejecutar tool → validar → devolver resultado/artifact.
- Permisos por tool (`read`, `write`, `network`, `shell`) y modo safe por defecto.
- Presupuesto de pasos y cancelación para evitar loops.

### P1

- Solo dos subagentes especializados si los casos reales lo justifican: `context-scout` read-only y `session-manager`.
- Delegación explícita y observable; no implementar una jerarquía de 5+ agentes de PA en el primer corte.

**Defer:** agente arquitecto, propagación BASE/DEV/PROD, swarm/multi-agent autónomo y evaluación LLM-as-a-judge.

---

# 4. Tools — **P0**

### Qué heredar

`core/skills/skill_executor.py` del PA aporta la abstracción correcta: `ToolProtocol`, `ToolRegistry`, `register`, `list_tools`, `invoke`, normalización de resultados y mocks. El agente principal del PA documenta herramientas `task/read/edit/write/grep/glob/bash` y denials críticos en `core/agents/pa-assistant.md:24-43`.

### Gap actual

No existe `ToolRegistry`, invocación de tools, permisos ni rutas API de tools en NeuroPA. La API actual delega solo a servicios internos (`database`, `TodayService`, `MemoryClaimService`, `ProviderRouter`).

### Mínimo P0

- Registry local de tools con schema de argumentos, resultado estructurado, timeout, cancelación y errores.
- Tools iniciales, en este orden:
  1. leer archivo dentro del workspace;
  2. escribir/editar con preview y confirmación;
  3. listar/buscar archivos;
  4. crear/actualizar task, memory claim y artifact;
  5. invocar provider AI.
- Shell **no** es P0 del producto general. Si se habilita para usuarios avanzados, debe ser una tool separada, desactivada por defecto, con allowlist y confirmación por comando.
- Cada llamada guarda `tool`, argumentos saneados, estado, duración y resultado resumido en la sesión.

**Defer:** MCP remoto, navegador, correo, calendario cloud y conectores de terceros.

---

# 5. Skills — **P0 mínimo / P1 extensible**

### Qué heredar

- Catálogo y discovery-first de `core/skills/SKILLS.md`.
- Skills versionadas y documentadas en `core/skills/core/*/SKILL.md`.
- Executor declarativo TOML en `core/skills/skill_executor.py` (`SkillManifest`, `SkillStep`, `required_capabilities`, retries).
- `@skill-discovery` para evitar scripts duplicados.

El PA documenta una gran biblioteca (PDF, XLSX, DOCX, CSV, ETL, Markdown, PPTX, data-viz, task-management, MCP-builder, etc.), pero esa amplitud no debe copiarse automáticamente.

### Gap actual

`neuropa/domain/models.py` solo define `Skill(name, version, enabled, permissions, source)`; no hay carga de manifests, discovery, execution, catálogo, UI ni endpoints.

### Mínimo P0

- Formato local simple (Markdown con frontmatter o TOML; elegir uno, no ambos).
- `name`, `version`, `description`, `tools_required`, `permissions`, `prompt/instructions`.
- Descubrimiento por carpeta de workspace/app; activar/desactivar; validación de permisos.
- Dos skills iniciales de harness: `context-scout` y `session-save`.
- Registro de la skill usada en cada ejecución.

### P1

Añadir skills de archivo/knowledge (Markdown, PDF, CSV) solo cuando haya una necesidad validada. Portar capacidades por valor de uso, no la lista de 22 skills del PA.

**Defer:** marketplace, instalación remota de skills, evaluación automática y skills que ejecuten comandos arbitrarios.

---

# 6. Artifacts — **P0 básico / P1 lifecycle**

### Qué heredar

En PA, el artifact real es el resultado local controlable: Markdown en `core/.context/`, workspaces, reportes y exports portables descritos en `docs/knowledge-management/README.md:87-174` (`.json`, `.md`, `.pa-export`). El workflow del agente exige validación y preservación (`core/agents/pa-assistant.md`).

### Estado actual

`neuropa/domain/models.py` ya tiene `Artifact(type, path, blob_ref, title, tags, version, links)`, pero no hay endpoint, servicio, almacenamiento de blobs, vínculo a conversación/tool/task ni UI. El export de `neuropa/api/app.py` exporta entidades JSON, no artefactos como productos navegables.

### Mínimo P0

- Resultado de cada acción que crea un archivo: artifact con `path`, `type`, `title`, `created_from_session` y checksum opcional.
- Vista/descarga local y vínculo desde el mensaje que lo produjo.
- Export/import JSON mantiene metadata; los archivos se exportan bajo un directorio seguro.
- No almacenar blobs duplicados dentro de SQLite: filesystem local + metadata es suficiente.

### P1

- Versiones, tags, links a task/project/memory y diff básico.
- Paquete portable `.neuropa-export` inspirado en `.pa-export`, con manifest y validación de paths.

**Defer:** editor colaborativo, object storage, previews de todos los formatos y publicación web.

---

# 7. Projects / workspaces — **P0**

### Qué heredar

- `workspaces/` y seis disciplinas preconfiguradas documentadas en `docs/technical/README-FULL.md`.
- Registro/search de proyectos de `core/scripts/project_register.py`, que sincroniza SQLite, Wiki, registry Markdown y JSON.
- Preservación durante updates: `core/scripts/update.py:190-210` protege workspaces y proyectos de contexto.

### Gap actual

`Project` existe como dataclass y `Task.project_id` apunta a él, pero no hay CRUD API, selección de workspace, aislamiento de paths ni frontend de projects. No existe un directorio workspace gestionado por NeuroPA.

### Mínimo P0

- `Workspace`: nombre, path raíz, activo/inactivo.
- `Project`: nombre, por qué importa, estado, siguiente acción, workspace_id.
- Crear/seleccionar/archivar workspace y project; asociar conversación, task y artifact.
- Restricción de filesystem: tools no pueden escapar del workspace activo sin confirmación.
- Un workspace por defecto y descubrimiento explícito; no seis plantillas obligatorias.

**Defer:** sincronización GitHub, múltiples workspaces simultáneos, colaboración y registry duplicado en 4 almacenes. Una tabla SQLite + export es suficiente.

---

# 8. Memory / Wiki — **P0/P1/Defer**

### Qué heredar

El PA tiene el modelo más valioso de continuidad en:

- `docs/MEMORY-ARCHITECTURE.md`: cuatro capas complementarias: Sessions Markdown, Memory MD, SQLite y Wiki.
- `core/memory/session_memory.py` y `core/memory/user_memory.py`.
- `core/scripts/message_hook.py`, `memory_pipeline.py`, `knowledge_miner.py`, `knowledge_extractor.py`, `knowledge_indexer.py`.
- `core/scripts/session_search.py`, `knowledge_export.py`, `knowledge_import.py`.
- `core/scripts/wiki_autopopulate.py`, `kb_updater.py` para conocimiento relacional.

### Estado actual NeuroPA

`neuropa/memory/__init__.py` implementa `MemoryClaimService`: claims con `source_type`, `source_ref`, `confidence`, supersession y búsqueda literal. `neuropa/domain/storage.py` ofrece SQLite/WAL, migración v1, soft delete y export/import. También existen implementaciones heredadas en `neuropa/core/memory/session_memory.py` y `user_memory.py`, pero no están cableadas a `neuropa/api/app.py` como runtime de chat.

### Mínimo P0

- Una memoria de sesión conversacional persistente.
- Claims explícitos con fuente/confianza, ya soportados por `MemoryClaimService`.
- Comando/acción de guardar, corregir, superseder y olvidar memoria.
- Recuperación pequeña y explicable: qué se recuperó y de qué fuente.
- Export/import portable como garantía de soberanía.

### P1

- Indexar sesiones y archivos Markdown con SQLite FTS5/BM25 o índice equivalente local.
- Consolidación al cierre/umbral, con resumen revisable por el usuario.
- Importar PA `.md` y reconstruir sesiones/claims sin acoplar el runtime a la estructura PA.

### Defer

Wiki relacional, grafo, autopoblado, extracción heurística masiva, cron de aprendizaje y analytics de uso. El PA los tiene (`docs/MEMORY-ARCHITECTURE.md:25-53`), pero serían complejidad prematura frente a un harness sin chat todavía.

---

# 9. Installer / config / updater — **P0/P1**

### Qué heredar

- UX de instalación guiada de `core/scripts/install.py` y launchers `pa.sh`/`pa.bat`.
- Configuración local de providers de `docs/SETUP-STANDALONE.md:21-49`.
- Requisitos y modo sin API key/local Ollama de `README.md:136-171`.
- Backup, protected paths, migraciones y restauración de `core/scripts/update.py`.
- Checks de sistema: `core/scripts/system_check.py`.

### Estado actual

NeuroPA se instala con `uv tool install neuropa` o pip y arranca con `neuropa` (`README.md`). `neuropa/cli.py` ofrece `--status`, `--export`, `--port`, y `neuropa/domain/storage.py` permite `NEUROPA_DATA_DIR`. No existe un panel/CLI para providers, modelos, permisos, rutas de workspace o updater seguro.

### Mínimo P0

- Primer arranque no técnico: elegir directorio de datos, provider local, modelo disponible, workspace y privacidad.
- Configuración versionada local; secretos solo en variables de entorno o archivo con permisos 0600.
- `neuropa --status` debe reportar DB, configuración, provider, modelo y modo de red.
- Backup/export antes de cambios de schema.
- Sin telemetría, analytics remotos ni llamadas de “check update” automáticas.

### P1

- `neuropa update --check` opt-in y `neuropa update` con backup, migraciones y restauración de datos, inspirado en `update.py`.
- Importador de configuración/knowledge desde PA.
- Instalador empaquetado para usuarios no técnicos (desktop bundle) cuando el flujo CLI esté probado.

**Defer:** auto-update silencioso, cloud account, sync SaaS y configuraciones distribuidas.

---

# 10. Calendar / reminders — **P1**

### Evidencia

PA es fuerte en sesiones y pendientes, pero no presenta un subsistema de calendario equivalente al dominio futuro de NeuroPA. NeuroPA ya modela `Reminder` y `CalendarEvent` en `neuropa/domain/models.py:52-64` y `:89-97`, y `Task` incluye `due_at` (`:37-49`), pero `neuropa/api/app.py` no expone endpoints CRUD, scheduler, notificaciones ni UI para esas entidades.

### Mínimo P1

- Reminders locales ligados a task/project: `trigger_at`, recurrencia simple, snooze y estado.
- Worker local pequeño o revisión al abrir la app; no daemon complejo inicialmente.
- CalendarEvent local de solo lectura/creación manual para contexto de sesión.
- Recordatorio visible en Today y en chat; posibilidad de posponer/descartar.

### Defer

Google/Apple/Outlook sync, invitaciones, zonas horarias complejas, notificaciones push, email/SMS y agenda compartida. No son necesarios para probar el valor del harness.

---

## Capacidades de PA que **no** deben copiarse ahora

1. **Dashboard como home:** `dashboard.html` y `core/scripts/generate_dashboard_data.py` son auxiliares; el home de NeuroPA debe ser harness/chat.
2. **Las 22 skills completas:** `core/skills/SKILLS.md` es catálogo de referencia, no un backlog de porting.
3. **4 capas de memoria simultáneas:** empezar con SQLite + export Markdown; añadir Wiki solo ante evidencia de recuperación insuficiente.
4. **Multi-CLI y propagación de ambientes:** `multi_cli_coordinator.py`, `event_bridge.py`, `sync_auditor.py` y `sync-propagator` son complejidad de plataforma, no P0 local single-user.
5. **MCP/self-healing remoto:** el PA lo documenta en `docs/core/PRP-004-CORE-Self-Healing-MCP.md`; para NeuroPA P0 bastan retries, circuit breaker, errores explicables y fallback local.
6. **Analytics/productivity metrics:** `usage_insights.py`, `optimization_reporter.py` y cron de aprendizaje no deben convertirse en telemetría encubierta.
7. **Cloud-first routing:** nunca copiar literalmente la cadena managed-first de `neuropa/providers/router.py`; la privacidad local es una restricción de arquitectura.

---

## Secuencia de entrega recomendada

### P0 — Harness mínimo

- Chat/sessions persistentes y captura consentida.
- Provider registry/config con Ollama/free local primero, BYOK/managed opt-in.
- Agente principal con contexto, límites y permisos.
- Tool registry seguro y 5 tools locales básicas.
- Skills locales declarativas: discovery + ejecución acotada.
- Workspace activo, projects mínimos y artifacts de archivos/resultados.
- Setup/status/config y export/import como contrato de soberanía.

### P1 — Continuidad operativa

- Session search/FTS y consolidación revisable.
- Portabilidad PA Markdown/`.pa-export` → NeuroPA.
- Artifacts versionados y links.
- Subagentes context/session solo si la carga real lo exige.
- Reminders/calendar local.
- Updater opt-in con backup/migración.

### Defer — Solo con evidencia

- Wiki/grafo/autopopulate.
- MCP y recuperación remota.
- Marketplace de skills y conectores cloud.
- Multi-user/sync/colaboración.
- Calendarios externos y notificaciones push.
- Dashboard analítico y métricas de uso.

## Criterios de aceptación del harness heredado

NeuroPA puede considerarse un AI harness v1 cuando un usuario no técnico pueda, sin salir de la app:

1. abrir una sesión local y conversar con un modelo local gratuito;
2. cambiar explícitamente a otro provider/modelo y ver el impacto de privacidad/coste;
3. pedir una acción, ver el plan corto y aprobar/rechazar tools;
4. producir un archivo/resultado navegable como artifact dentro del workspace;
5. cerrar y reabrir la sesión conservando contexto útil;
6. guardar/corregir/olvidar un recuerdo con fuente;
7. exportar sus datos y restaurarlos sin cuenta ni red;
8. continuar usando captura/Today/Focus como módulo ADHD, no como sustituto del harness.

**Conclusión:** heredar contratos y patrones del PA —contexto local, persistencia, provider abstraction, skills declarativas, tools con permisos y artefactos portables—, no su superficie completa. La ruta YAGNI es convertir el núcleo actual de NeuroPA en un harness pequeño, local y explicable antes de añadir wiki, automatizaciones o integraciones de productividad externas.
