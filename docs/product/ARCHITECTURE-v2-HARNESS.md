# NeuroPA — Architecture v2: Local AI Workspace / Harness

**Estado:** Canonical architecture for P0
**Fecha:** 2026-08-01
**PRD:** `specs/PRD-v2-HARNESS.md`
**Base:** `architecture/ARCHITECTURE-v1.md` y mensaje autoritativo de N30

## 1. Decisión arquitectónica central

NeuroPA se diseña como una aplicación local de AI Workspace/harness. Chat,
sessions, agents/modes, tools/skills, artifacts, projects, wiki/memory y
Executive Function son capacidades del mismo workspace y comparten identidad,
contexto, permisos y almacenamiento.

El repo OSS contiene el runtime local completo. El SaaS privado es un control
plane separado que puede implementar adapters para sync, identidad, backups,
managed AI y billing, pero no es una dependencia del core.

## 2. Principios

1. **Ports & adapters:** el dominio no importa SDKs de providers, UI, cloud ni
   runtimes concretos.
2. **Local-first por contrato:** P0 funciona sin red y sin cuenta; sólo la
   capacidad LLM escogida puede requerir red.
3. **Free/local/open-source primero:** el orden de resolución favorece runtime
   local, providers gratuitos compatibles y BYOK; managed es opcional.
4. **Harness observable:** cada sesión registra entradas, contexto permitido,
   tools, artifacts, fuentes, eventos y resumen de proceso.
5. **Grounding y consentimiento:** memory/wiki sólo entra al contexto si la
   sesión lo permite; las fuentes se preservan; acciones externas requieren
   confirmación.
6. **No chain-of-thought:** el sistema produce un proceso resumido estructurado
   (plan, pasos, fuentes, decisiones y resultado), no razonamiento interno.
7. **YAGNI:** SQLite, FTS y jobs locales son suficientes para P0; no se añade
   una plataforma distribuida para anticipar el SaaS.

## 3. Vista de capas

```text
┌──────────────────────────────────────────────────────────────────┐
│ UI local: Home · Chat · Sessions · Projects · Wiki · Artifacts   │
│ Tools/Skills · Executive Function · Settings                    │
├──────────────────────────────────────────────────────────────────┤
│ Local Application API: commands, queries, streaming, events      │
├──────────────────────────────────────────────────────────────────┤
│ Application services: Workspace · Session · Agent · Artifact    │
│ Memory · Project · Tool · ExecutiveFunction · Export             │
├──────────────────────────────────────────────────────────────────┤
│ Domain core: entities, value objects, policies, ports, events    │
├──────────────────────────────────────────────────────────────────┤
│ Adapters: SQLite/FTS · filesystem · keyring · scheduler ·       │
│ local notifications · Ollama/llama.cpp · free/BYOK HTTP         │
└──────────────────────────────────────────────────────────────────┘
                  │ optional, explicit adapters only
┌─────────────────▼────────────────────────────────────────────────┐
│ PRIVATE SaaS REPO: auth · tenants · sync · managed AI · billing  │
│ backups · operations · hosted notifications                       │
└──────────────────────────────────────────────────────────────────┘
```

La flecha al SaaS no representa una llamada obligatoria desde el core. El
workspace puede operar con todos esos adapters deshabilitados.

## 4. Bounded contexts del core local

### 4.1 Workspace

`Workspace`, `WorkspaceSettings`, provider preferences, privacy policy local,
active project y rutas de datos. Un workspace es una frontera de exportación y
no implica una cuenta remota.

### 4.2 Conversations y Sessions

`Conversation`, `Message`, `Session`, `SessionEvent` y `ProcessSummary`.
Una sesión agrupa conversación, objetivo, contexto, modo, tools usadas,
artifacts y resultado. Los mensajes son append-only desde el punto de vista de
la auditoría; las ediciones crean una nueva versión.

### 4.3 Agents y cognitive modes

`AgentDefinition` declarativo:

- instrucciones y formato de salida;
- fuentes de contexto permitidas;
- tools allowlisted;
- provider/model preference;
- límites de tokens, tiempo y acciones;
- esquema de `ProcessSummary`.

Los presets P0 (`creativity`, `clarity`, `detail`, `memory`) son datos
versionados, no clases especiales. Esto permite añadir modos sin duplicar el
orquestador ni inferir un diagnóstico.

### 4.4 Tools y Skills

`ToolDefinition`, `SkillManifest`, `PermissionSet`, `ToolInvocation` y
`ApprovalRequest`. La skill describe composición y metadata; la tool ejecuta
una capacidad concreta. Todas las invocaciones pasan por policy, permisos,
redacción de secretos y confirmación cuando corresponda.

### 4.5 Projects y Artifacts

`Project` enlaza objetivo, contexto, sesiones, artifacts y siguiente acción.
`Artifact` usa almacenamiento por referencia (`artifact_id`, tipo, versión,
checksum, path/blob local) para no introducir blobs grandes en mensajes.

### 4.6 Wiki y Memory

`MemoryEntry`, `MemoryClaim`, `SourceRef`, `Evidence` y `MemoryLink`. Wiki es
una vista navegable de entradas y claims, no un segundo motor paralelo. La
memoria distingue hechos, preferencias, inferencias, preguntas y resúmenes.

### 4.7 Executive Function

`InboxItem`, `Task`, `FocusSession`, `Reminder`, `CalendarEvent` y `Preset`.
Es un bounded context integrado: sus referencias pueden apuntar a Project,
Session, Artifact y Memory sin copiar sus datos. Capture, Today, Focus y
recovery son vistas/policies sobre el mismo workspace.

## 5. Puertos

Los puertos son interfaces estables del core. Cada puerto debe tener fake/in-
memory adapter para tests P0.

| Puerto | Responsabilidad | Adapters P0 |
|---|---|---|
| `WorkspaceStore` | perfiles, settings, preferencias | SQLite |
| `SessionStore` | conversaciones, eventos, resúmenes | SQLite |
| `ProjectStore` | proyectos, enlaces y siguiente acción | SQLite |
| `ArtifactStore` | metadata, versiones y archivos | SQLite + filesystem |
| `MemoryStore` | claims, fuentes, links y revisiones | SQLite + FTS |
| `ExecutiveStore` | inbox, tasks, focus, reminders, calendar | SQLite |
| `SearchPort` | búsqueda textual y filtros | SQLite FTS5 |
| `LLMProvider` | health, chat/stream, cancelación | Ollama, free HTTP, BYOK |
| `ProviderRouter` | selección, fallback y policy | local/free/BYOK |
| `ToolRunner` | ejecutar tool con permisos | built-ins locales |
| `ApprovalPort` | pedir/registrar consentimiento | UI local |
| `Scheduler` | reminders y eventos temporales | job local |
| `Notifier` | notificaciones al usuario | OS/local UI |
| `SecretStore` | API keys y tokens | OS keyring |
| `ExportPort` | export/import versionado | ZIP + Markdown/JSON/ICS |
| `NetworkPolicy` | permitir/bloquear egress | offline gate |

`SyncTransport`, `AuthProvider`, `ManagedLLM`, `BillingEntitlements` y
`HostedBackup` son puertos reservados para el adapter del SaaS privado, no
requisitos de P0. No deben aparecer en el camino de arranque local.

## 6. Flujo de una sesión harness

```text
UI command
  → Application service inicia Session
  → AgentPolicy selecciona modo y contexto permitido
  → Memory/Search recupera fuentes con provenance
  → ProviderRouter elige local → free → BYOK (según policy del usuario)
  → LLM stream emite mensajes y ProcessSummary
  → ToolRunner ejecuta sólo allowlist; ApprovalPort confirma lo externo
  → ArtifactStore guarda resultados versionados
  → SessionStore persiste eventos, fuentes, provider y resumen
  → MemoryStore ofrece guardar claims/decisiones de forma explícita
```

El router no puede cambiar de local a cloud para contenido marcado local-only.
Un fallback se comunica en la UI con provider, motivo, límites y privacidad.

## 7. Provider architecture

### 7.1 Contrato mínimo

```text
LLMProvider
  capabilities() -> streaming, tools, vision, context_limit
  health_check() -> status, latency, error
  complete(request, cancellation) -> stream[LLMEvent]
```

`LLMRequest` contiene mensajes, contexto autorizado, mode id, tool schemas,
privacy classification y budget. `LLMEvent` distingue delta de texto, tool
request, usage, finish, error y process-summary update.

### 7.2 Resolución P0

1. Runtime local configurado y compatible (Ollama primero).
2. Provider gratuito elegido por el usuario o disponible en el onboarding.
3. BYOK guardado localmente.
4. Managed provider sólo si un futuro producto/distribución lo habilita
   explícitamente; jamás como dependencia oculta.

La aplicación muestra la ruta y permite fijar “local only”, “no network” o un
provider concreto por workspace, proyecto o sesión.

### 7.3 Seguridad

Keys sólo en `SecretStore`; nunca en HTML/JS, artifacts, eventos ni logs.
HTTP adapters usan timeout, límite de contexto, backoff acotado para 429/5xx,
circuit breaker y cancelación. La app no manda el historial completo si el
contexto seleccionado no lo requiere.

## 8. Grounded memory y proceso resumido

```text
Sources (session/project/wiki)
       ↓ explicit selection + policy
SearchPort (FTS; embeddings optional later)
       ↓ ranked SourceRef
ContextBuilder
       ↓ claims + citations
LLMProvider
       ↓ answer + ProcessSummary + source refs
SessionStore / ArtifactStore / optional MemoryStore save
```

Reglas obligatorias:

- cada claim persistido tiene `source_ref`, `captured_at` y `evidence_type`;
- conflictos crean una nueva versión y no borran silenciosamente la anterior;
- la respuesta separa evidencia, inferencia y propuesta;
- ausencia de fuente produce “no tengo evidencia suficiente”;
- `ProcessSummary` expone objetivo, plan corto, pasos ejecutados, tools,
  fuentes, supuestos, decisiones y resultado; no el razonamiento privado.

## 9. Tool/skill security model

Cada tool declara `fs_read`, `fs_write`, `network`, `process`, `calendar` y
`destructive` scopes. El policy engine combina esos scopes con policy del
workspace, modo activo y consentimiento de la sesión.

- Lectura de memoria/wiki local: permitida si la sesión la habilita.
- Escritura de artifact/proyecto: confirmación o regla previamente aprobada.
- Red, comandos, envío de mensajes, borrado y cambios de calendario:
  confirmación humana obligatoria en P0.
- Skill importada: manifiesto validado, versión fijada y permisos visibles.
- No se ejecutan instrucciones recibidas desde un documento como permisos.

## 10. API y proceso local

- Un proceso local sirve API y frontend en loopback; el frontend no toca
  SQLite directamente.
- API autenticada con token privado de instalación y validación de origin.
- REST/JSON para commands/queries; streaming SSE o WebSocket para chat y
  eventos de tools/timer.
- Contratos versionados y errores tipados (`ProviderUnavailable`,
  `ApprovalRequired`, `EvidenceMissing`, `OfflineOnly`).
- Shutdown y recuperación deben dejar eventos y archivos en estado consistente.

No se usa `0.0.0.0`, docker socket ni endpoint remoto implícito en P0.

## 11. Persistencia y portabilidad

- SQLite en un único data directory por workspace, WAL y migraciones
  versionadas.
- Filesystem separado para artifacts con checksum y nombres no derivados
  directamente de input no confiable.
- FTS5 para sesiones, projects, wiki, memory y artifacts textuales.
- Backups locales rotativos; export ZIP con manifest, schema version, JSON
  estructurado, Markdown legible, artifacts y calendario ICS.
- Import es transaccional: validar manifest, escribir staging, verificar
  checksums y activar sólo después de pasar validación.

## 12. UI composition

La UI se organiza por tareas del harness, no por tablas internas:

- **Home:** iniciar chat, retomar sesión, proyecto reciente y Today.
- **Chat/Session:** conversación, modo, contexto, resumen de proceso, tools y
  artifacts.
- **Projects:** propósito, sesiones, outputs y siguiente acción.
- **Wiki/Memory:** búsqueda, fuentes, claims y revisión.
- **Artifacts:** preview, versiones, links y export.
- **Tools/Skills:** catálogo, permisos, health y activación.
- **Executive Function:** Capture, Today, Focus, reminders y calendar.
- **Settings:** providers, privacidad, offline, keyring, export e idioma.

Progressive disclosure mantiene simple Home y Chat; no se ocultan controles de
privacidad, provider ni permisos cuando una acción puede sacar datos del equipo.

## 13. SaaS privado y frontera de repositorios

```text
Public OSS repo                         Private SaaS repo
─────────────────                       ─────────────────────────
Local domain + ports                    Auth/OIDC + tenants
SQLite/filesystem                       Sync API + Postgres/RLS
Local/free/BYOK adapters                Managed LLM gateway + quotas
Local scheduler/notifier                Hosted jobs/notifications
Export/import                            E2E sync + hosted backups
No telemetry                             Billing/entitlements/operations
```

El SaaS puede consumir contratos publicados y aportar adapters. No se copia la
lógica de dominio para crear una segunda semántica. El core local sigue siendo
usable aunque el repo privado o sus servicios no existan.

## 14. Quality gates P0

1. **Domain:** tests de entidades, policies, invariantes y migraciones.
2. **Harness:** sesión con modo, memoria grounded, tool approval y artifact.
3. **Provider:** local/free/BYOK health, timeout, fallback y redacción.
4. **Offline:** capture, chat mock, búsqueda, projects, artifacts, export e
   import sin red.
5. **Security:** no keys en frontend/logs; tool scopes; loopback auth; egress
   inventory.
6. **UX:** onboarding no-tech, keyboard-first, reduced motion, empty states y
   reentrada Executive Function.
7. **Packaging:** instalación limpia en plataformas objetivo y arranque sin
   terminal.

## 15. Decisiones diferidas explícitamente

- Framework frontend pesado frente a SPA modular; elegir por evidencia de P0.
- Embeddings/vector store, jobs autónomos y modelos multimodales.
- Sincronización, colaboración, identity y hosted operations.
- Mobile nativo, marketplace, integraciones externas y calendario OAuth.

Cualquier decisión que rompa la frontera local o agregue un servicio obligatorio
requiere actualizar este documento y el PRD antes de implementar.
