# NeuroPA — N30 Human-QA Corrective Program

**Date:** 2026-08-04T15:41:27-05:00  
**Owner:** Hermes / N30  
**Branch:** `feat/p1-integrated`  
**Baseline commit:** `81c6929c39f318742fb2fc4fe9818b4f3e573e82`  
**Status:** corrective execution package — approval/execution pending  
**Supersedes:** the prior `READY_FOR_N30` freeze decision. N30's desktop human QA found real product and interaction gaps.

## 1. Executive decision

A new execution campaign is required. It must not be a single monolithic Codex-Spark turn.

The corrective work is split into three independently gated turns:

1. **Turn A — Interaction and workspace P0:** collapsible shell, session rail, composer proportions/popovers, correct agent naming, processing telemetry, session-vs-artifact semantics.
2. **Turn B — Operational configuration P1:** primary agent profile, real Skills and MCP management, provider/local/OpenCode setup, selective export.
3. **Turn C — Memory product P1:** OKF-inspired Wiki, structured concept relationships, real force-directed graph, styled correction flow.

Each turn must pass tests and real browser QA before the next turn starts. A self-report from the executor is never sufficient.

## 2. Human-QA findings and confirmed causes

| N30 finding | Live/source confirmation | Classification |
|---|---|---|
| Primary desktop aside cannot be hidden | `.shell` has a fixed `248px` first column and no desktop collapse state | P0 interaction bug |
| Session aside cannot be hidden | `state.sessionRail` changes, but base desktop `.workspace-layout` always reserves `minmax(220px,286px)`; `session-open` only affects narrower breakpoints | P0 interaction bug |
| Primary agent cannot be configured | `AgentMode` exists, but there is no `AgentProfile` identity/configuration contract | P1 missing capability |
| Skills/MCP cannot be managed | `Skill` and `ToolDefinition` entities exist, but `/api/tools` is read-only and there is no MCP entity/service/UI | P1 missing capability |
| “Propuesta de IA” appears as agent name | Frontend labels the seeded mode as if it were agent identity | P0 semantic/UI bug |
| Composer is oversized and poorly proportioned | `.composer-wrap`/dock consume excessive vertical space; controls expand downward | P0 UX defect |
| Dropdowns open downward | Current control menu insertion has no viewport-aware positioning | P0 interaction defect |
| “Cambiar sesión” does not work | UI state toggles but desktop grid remains unchanged | P0 functional bug |
| Artifacts are confused with conversation output | API converts assistant messages directly to Markdown artifacts; UI describes artifacts as “saved responses”; no separate session export action | P0 product semantics defect |
| No processing/waiting feedback | `state.loading` changes the button but there is no explicit thinking/processing status contract | P0 feedback defect |
| No context/tok/s metadata | Usage is stored, but duration/context-window metadata is incomplete; UI exposes none | P1 observability gap |
| Memory Map is three rows, not a graph | Node positions are `index % 4` / `floor(index / 4)` fixed-grid coordinates | P0 false-positive QA / P1 visualization defect |
| Memory is not semantically structured or Wiki-navigable | Claims/sources/sessions/supersession exist, but no concept bundle/index/Wiki surface | P1 missing product layer |
| “Corregir memoria” dialog is poorly designed | Modal lacks a governed comparison/layout pattern | P0 UX defect |
| Settings cannot switch runtime/login providers | First-run wizard can select a path, but Settings cannot mutate/verify it; OpenCode auth flow is not surfaced | P1 missing capability |
| Export cannot select content | Current export emits all entity types as JSON and does not provide a governed selective ZIP | P1 portability gap |

## 3. Evidence custody

Current live hashes before this corrective campaign:

```text
frontend  9e63fa92f404d69f6b6eaca4387bdd41d8e080365ec789e4aee80d9212085911
app       9bf15f3714e3e4ffb70760b77946ccfaf38af7580169303d397915bc552fddc9
harness   d28291427ce99b39500e1bff073b8fddd1b591ade663240a94a7de91023329ea
memory    23132e36d5c9537fa09f0c2831cadc8c0c508fece5b99a5275340c5d8779a38e
models    dd6e13ec63abfb6bff4685d6c43d5593653f2f3ee0c4997245aaeca02e8b4bc5
```

The branch is intentionally dirty from the prior G/R campaign. Executors must preserve unrelated changes and must not reset, restore, commit, push, or rewrite the SPA wholesale.

## 4. Product and architecture decisions

### 4.1 Agent identity is not an AgentMode

Add a minimal `AgentProfile` entity/service for the primary NeuroPA agent:

- `name`
- `description`
- `system_prompt`
- default `mode_id`, `provider_id`, and `model`
- selected `skill_ids`, `tool_ids`, and `mcp_server_ids`
- `enabled`

`AgentMode` remains a conversational/cognitive mode. The UI must never show a mode name as the agent's identity.

### 4.2 Skills and MCP activation must reach the runtime

A database-only toggle is forbidden.

Use project/session-scoped OpenCode workspaces under NeuroPA's existing workspace root. Materialize only enabled agent/skill/MCP configuration into that scoped workspace before execution. Do not modify the user's global `~/.config/opencode`.

OpenCode 1.4.6 live evidence:

- `opencode auth login/list/logout` exists;
- `opencode mcp add/list/auth/logout/debug` exists;
- OpenCode config supports `mcp.<name>.enabled`;
- active MCP tools become available to the OpenCode model.

The executable is currently `/home/freakingjson/.opencode/bin/opencode`; make resolution explicit/configurable. Do not depend on a login shell PATH.

Secrets must remain in OpenCode's credential store. NeuroPA may show sanitized provider/auth status but must not read, return, log, persist, or export secret values.

### 4.3 Session and Artifact are different products

- **Session:** conversation history and execution trace. It may be exported or saved as a transcript.
- **Artifact:** an intentional deliverable emitted by an agent/tool or explicitly converted from a selected assistant output.
- A normal message is not automatically an artifact.
- UI actions must say exactly what happens: `Exportar sesión`, `Guardar transcripción`, or `Crear entregable Markdown`.
- Artifact records retain source session/message, checksum, MIME/type, version, tags, and file path.

### 4.4 Telemetry must be truthful

Add server-side elapsed time and normalized usage metadata to assistant messages.

Display only measured/provider-reported fields:

- input tokens;
- output tokens;
- elapsed time;
- output tokens/second when output tokens and duration are valid;
- context window and remaining context only when the provider/model reports a trustworthy context limit.

When unavailable, show `No reportado`; never estimate or fabricate.

During a request, expose an immediate `Procesando…`/`Pensando…` live region with elapsed waiting time. Do not claim server-side cancellation unless cancellation is actually propagated.

### 4.5 Memory uses OKF patterns, not the Understory server

Do not vendor Understory, its Express server, AgentBox, React frontend, Docker socket surfaces, or unauthenticated MCP manager.

Adopt these patterns inside NeuroPA:

- plain Markdown concept pages with constrained YAML frontmatter;
- deterministic code validation and root-path sandboxing;
- typed wikilinks/relationships;
- create-vs-enrich behavior;
- supersede contradictions instead of keeping parallel truths;
- deterministic lint for orphans and broken links;
- searchable index and recent change log;
- source/session/claim provenance;
- force-directed graph and accessible equivalent list.

PA-prealpha is inspiration for lossless raw storage → structured extraction → Wiki/KB → navigation, but its empty/demo indexes and heuristic miner must not be copied as production truth.

### 4.6 Export is selective and secret-free

Provide a user-selectable export contract for:

- workspace/agent configuration;
- sessions/messages;
- memory claims and Wiki pages;
- artifacts and artifact files;
- skills/tools/MCP metadata;
- provider selection metadata.

Exclude tokens, API keys, OAuth credentials, pairing codes, auth cookies, raw secret refs, and global OpenCode configuration. ZIP exports require a manifest with schema version, selected sections, file hashes, and omitted-secret declaration.

## 5. Turn A — Interaction and workspace P0

### A1. Collapsible shell

- Add a persistent desktop primary-rail open/collapsed state.
- Add an always-reachable topbar control to restore it.
- Full collapse must reclaim layout width; hiding visual content while preserving an empty column fails.
- At `701–1100px`, preserve compact-icon behavior without conflicting states.
- At `≤700px`, preserve the bottom navigation.
- Store only harmless UI preference in localStorage.

### A2. Functional session rail

- Desktop `Cambiar sesión`, close `×`, and keyboard controls must toggle the grid between zero and the session column.
- Restoring the rail must preserve current session selection and focus the rail heading/new-session action.
- Opening/closing cannot shift the artifact canvas over the composer or create overflow.

### A3. Composer Impeccable pass

- Reduce unused vertical space and establish a compact, stable composer footprint.
- Use a clear hierarchy: input → compact controls → status/action row.
- Provider/model/mode/context menus must use viewport-aware popovers: prefer above the composer, flip below only when required, remain inside viewport, and close on Escape/outside click.
- Keep all targets ≥44px without turning every control into a large card.
- Preserve visible focus, reduced motion, and keyboard selection.
- Run the Impeccable critique/detector before and after implementation.

### A4. Correct identity and labels

- Until `AgentProfile` lands in Turn B, use a neutral `NeuroPA`/`Asistente NeuroPA` identity.
- Display mode labels as modes (`Modo: Propuesta`) rather than agent names.
- Remove `Propuesta de IA` anywhere it reads as the agent identity.

### A5. Processing and result metadata shell

- Immediate `aria-live` processing state during fetch.
- Waiting timer and selected provider/model are visible but unobtrusive.
- On completion, render normalized usage fields available today.
- Unknown context fields explicitly say `No reportado`.

### A6. Session/artifact vocabulary

- Rename ambiguous message actions.
- Add an explicit session export/transcript action.
- Artifact registry copy must describe deliverables, not conversations.
- Preserve current file checksum/read security.

### A7. Turn A acceptance

- Desktop primary rail width becomes 0 when hidden and is recoverable.
- Desktop session rail width becomes 0 when hidden and is recoverable.
- `Cambiar sesión` changes computed grid columns in browser, not just state/class.
- Composer menus open above at standard desktop/tablet composer positions and flip only near top.
- No menu or composer is clipped at 1600×1000, 768×900, or 480×860.
- Processing live region appears before the response completes.
- A session export is not inserted into `/api/artifacts` unless the user explicitly creates an artifact.
- No console/page errors; no horizontal overflow; targets ≥44px.

## 6. Turn B — Operational configuration P1

### B1. Primary AgentProfile

- Add domain entity, migration/serialization support, service, CRUD API, and Settings UI.
- Seed exactly one primary profile without overwriting existing user data.
- Use the profile's system prompt/defaults in `HarnessService.send_message`.
- Session-specific choices may override profile defaults without mutating the profile.

### B2. Skills management

Extend `Skill` with sufficient metadata/content reference for real use:

- name, description, version, source, enabled, permissions, tags;
- safe local content/path or governed imported body;
- validation before activation;
- CRUD endpoints and enable/disable.

Enabled skills selected by the primary agent must be materialized into its scoped OpenCode workspace and observed by a real execution smoke. A UI toggle with no runtime change fails.

### B3. MCP management

Add `MCPServer` with safe typed configuration:

- name;
- type: local or remote;
- command array or URL;
- enabled;
- OAuth/auth status without secret values;
- last health/error summary;
- agent binding.

Requirements:

- validate names and types;
- sandbox writes to NeuroPA's project-scoped OpenCode config;
- never accept shell strings; local commands are argv arrays;
- never return environment secret values;
- remote URLs require `http(s)` and LAN/auth governance;
- enable/disable must change generated OpenCode config;
- `opencode mcp list` readback must verify status;
- one harmless fixture MCP must be invoked in an isolated test workspace.

### B4. Provider/local/OpenCode setup

Settings must support:

- select `local`, `opencode_free`, `byok`, or managed when available;
- list sanitized provider readiness;
- refresh local/OpenCode models;
- trigger/guide OpenCode login via its own credential flow;
- verify auth after completion;
- logout with explicit confirmation;
- never capture credentials in the SPA.

If a provider requires an interactive terminal/OAuth step that cannot be completed in the web process, the UI must launch or present the exact local flow and poll sanitized status. It must not show a false “connected” state.

### B5. Selective export

- Add explicit export request schema with selected sections.
- Support JSON and ZIP.
- ZIP includes artifact files and Wiki Markdown only when selected.
- Add manifest + SHA256 per included file.
- Exclude secrets by construction and test forbidden-key scans.
- UI provides checkboxes, select-all/none, size/count preview, and download.

### B6. Turn B acceptance

- Primary agent rename/system prompt/default provider survive restart.
- Disabled skill is absent from scoped execution; enabled skill is present and used in a controlled smoke.
- Disabled MCP is absent from effective config/tool list; enabled fixture MCP is callable.
- Switching to local changes the effective provider for a new session.
- OpenCode auth status is sanitized and no secret appears in API/log/DOM/export.
- Selective export includes exactly selected sections and passes forbidden-secret scan.

## 7. Turn C — Memory Wiki and graph P1

### C1. Wiki bundle service

Create a NeuroPA-owned memory bundle under the app data directory:

- `index.md`
- `log.md`
- `entities/`
- `concepts/`
- `comparisons/`
- `queries/`
- `raw/` only where product-relevant

Frontmatter minimum:

- title;
- type;
- tags;
- created/updated;
- summary;
- source claim/session IDs;
- related concept slugs.

All paths must be sandboxed to the bundle root. Writes are atomic. Markdown/body and frontmatter are validated in deterministic code.

### C2. Structured relationship behavior

- A new fact enriches an existing concept when identity/type matches.
- Distinct concepts are created with backlinks.
- Contradictions use the existing supersession model.
- Broken wikilinks and orphans are reported by deterministic lint.
- Claims remain the evidence layer; Wiki pages are the navigable concept layer.
- FTS/lexical search is sufficient for initial scale; embeddings are deferred until evidence shows need.

### C3. Wiki UI inside Memoria

Provide tabs/panes:

- `Mapa`
- `Wiki`
- `Cambios/Salud`

Wiki must support search, type/tag filters, tree/list navigation, page viewer, backlinks, related concepts, provenance, and opening the associated graph node.

The inspector must collapse or let the graph reclaim its width when no node/page is selected; do not reserve a large empty right column. Raw `ref:*` IDs belong in technical details, not as primary node/page labels.

### C4. Real force-directed graph

No CDN/framework. Implement a deterministic bounded force simulation suitable for the SPA:

- seeded initial positions;
- repulsion;
- spring edges;
- collision avoidance;
- bounded viewport;
- drag node, pan, zoom, reset;
- type colors and degree-based sizing;
- orphan ring;
- click opens source/Wiki inspector;
- readable labels with collision/overlap handling; labels must not render on top of unrelated nodes or other labels;
- accessible list mirrors all nodes and relationships.

Do not use fixed index-grid positions.

### C5. Correction dialog redesign

- Proper `<dialog>` semantics and focus trap/return.
- Current memory and replacement shown side-by-side on desktop, stacked on mobile.
- Every textarea/input has a visible aligned label; fields may not overlap or sit on mismatched baselines.
- Show source, confidence, affected relationships, and explicit supersession outcome.
- Primary action: `Guardar corrección`; secondary: `Cancelar`.
- Do not expose implementation jargon such as `claim` or `supersede` in the primary user journey; reserve it for technical details.
- No raw IDs as primary copy; IDs remain in technical details.

### C6. Turn C acceptance

Seed a controlled fixture of at least 20 nodes across claims, concepts, sources, sessions, supersession, and one orphan.

Browser assertions:

- positions vary on both X and Y axes;
- connected nodes have rendered edges;
- no fixed four-column row pattern;
- no overlapping primary labels and no raw `ref:*` identifier used as the user-facing title;
- collisions are below defined tolerance;
- all nodes remain reachable by pan/zoom/reset;
- drag changes a node position;
- selecting node opens correct provenance;
- orphan is visibly and accessibly marked;
- Wiki search opens correct page and backlinks;
- correction creates one supersession edge and preserves old evidence;
- 1600/768/480 pass with no overflow/errors.

## 8. Global security and custody constraints

- Preserve LAN CIDR `192.168.1.0/24`, `client_allowed_for_token`, cookie `samesite=lax`, auth dependencies, and `0.0.0.0:8474` operational behavior.
- Do not test against or restart human runtime `:8474`; use an ephemeral port/database.
- Do not touch FJSON Studio `:7865`.
- No global OpenCode config mutation.
- No secret printing or fixture based on real credentials.
- No CDN, framework, build step, or full SPA rewrite.
- No `git reset`, `restore`, commit, push, or history rewrite.
- Screenshots go to `/tmp` only.
- Preserve unrelated dirty worktree changes.

## 9. Verification gates per turn

1. Targeted unit/contract tests first.
2. `python3 -m compileall -q neuropa tests`.
3. `node --check` against extracted SPA script.
4. `uv run pytest -q --tb=short`.
5. `git diff --check`.
6. Fresh ephemeral server/database.
7. Real browser journeys at 1600×1000, 768×900, 480×860.
8. Console, page-error, failed-request, overflow, focus, target-size checks.
9. Readback of persisted records/config/files after restart.
10. Security forbidden-key/path/traversal tests.
11. Hermes zero-trust review of every block, not only the latest diff.
12. N30 human QA before promotion/commit.

## 10. Stop conditions

Stop the active turn and report instead of improvising when:

- a change requires global OpenCode credential/config mutation;
- an MCP requires arbitrary shell execution or exposes secrets;
- a provider login cannot be completed without an interactive user flow;
- the work would require replacing the SPA/framework;
- the human runtime or LAN/auth behavior changes;
- tests or browser gates cannot be made deterministic;
- a later turn depends on an unverified previous turn.

## 11. Final promotion rule

No `READY_FOR_N30` verdict until all three turns are independently green and N30 completes the final human journey. Static string tests and screenshots alone cannot certify interaction, graph topology, runtime skill/MCP activation, provider switching, or export correctness.

## 12. Post-corrective owner batch — execution addendum

N30 approved continuing beyond the Composer B correction. The following owner-facing portability and personalization surfaces are now implemented on the dirty feature branch and remain pending final N30 human promotion:

- Composer B contract shared by mobile and desktop, with 132px/180px textarea caps and 44px targets.
- AgentMode CRUD in Ajustes; modes remain style/focus modifiers subordinate to the literal current request.
- Session export as JSON, Markdown and self-contained SPA-HTML offline, separate from artifacts.
- Confirmed full-workspace JSON import with bounded payload validation; full backups round-trip `SOUL.md` and `AGENTS.md`.
- Permanent identity layers stored as owner-editable `identity/SOUL.md` and `identity/AGENTS.md`, written atomically and included in the runtime prompt with explicit literal-request precedence.
- OpenRouter BYOK defaults to the official OpenAI-compatible endpoint, refreshes its public catalog and prioritizes `openrouter/free`/`:free` models.
- Platform surfaces for Linux, macOS, Windows PowerShell, Docker and Android/Termux; Docker image build and live `/api/health` smoke are mandatory release evidence.

The failed `deleg_5d9c76e6` fan-out produced no audit evidence: all three children were rejected upstream with HTTP 403 before inspecting the repository. It must not be counted as review coverage. Hermes performed direct source, test, runtime, export, Docker and three-viewport browser verification instead.
