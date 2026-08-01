# NeuroPA 2.0 — Research-Backed AI Harness Architecture

**Status:** canonical Plan 2.0  
**Date:** 2026-08-01  
**Supersedes:** `specs/PLAN-2.0.md`, whose center of gravity was a productivity app.  
**Inputs:** current P0, `PRD-v2-HARNESS`, `ARCHITECTURE-v2-HARNESS`, PA gap audit, Dozer/Seraph reviews and `RESEARCH-SOURCES-v2.md`.

## 1. Executive decision

NeuroPA 2.0 is an **open-source, local-first AI workspace/agent harness** designed to reduce the cognitive cost of using AI for people with ADHD/TDAH patterns—without restricting use by neurotypical users and without making clinical claims.

The product is not “tasks plus chat.” The primary loop is:

```text
raw thought / question / material
        ↓
AI session with an explicit cognitive mode
        ↓
selected local context + grounded sources
        ↓
provider route: free OpenCode → local Ollama → explicit BYOK
        ↓
answer + visible process summary + provenance
        ↓
confirmed artifact / memory / project / next action
        ↓
low-friction re-entry in the next session
```

The **public OSS repository is a complete local product**. The future private SaaS repository supplies optional adapters—identity, encrypted sync, managed inference, hosted backup, billing and operations—but the OSS product must remain useful when that repository and every hosted service are absent.

## 2. Result analysis: what exists now

### 2.1 P0 capabilities proven

- FastAPI local API, SQLite/WAL and no-build SPA.
- Persistent workspaces, sessions and messages.
- Four ADHD-first modes: Creativity, Clarity, Detail and Memory.
- Real free-first AI through OpenCode CLI; seven free models detected in the current environment.
- Ollama adapter and honest availability state.
- Provider/model/mode persistence and session-level local-only enforcement.
- Grounded memory claims that return evidence or “no evidence.”
- Markdown artifacts with atomic write, containment and SHA-256.
- Executive Function module: capture, Today and bounded Focus surface.
- Provider setup wizard, command palette, roadmap honesty and 44px actions.
- One-time LAN pairing with device cookie; no LAN master-token disclosure.
- Reproducible gates: 43 pytest tests and Playwright at 1600/768/480.
- No telemetry, no account and no private SaaS dependency.

### 2.2 Current limitations—not bugs disguised as roadmap

1. OpenCode responses are request/response, not streamed through NeuroPA.
2. “Context: this session” is history only; projects/wiki/artifacts are not yet selectable context sources.
3. Memory search is simple lexical matching, not SQLite FTS5/BM25.
4. Tool/skill registry is descriptive; execution and approvals are intentionally disabled.
5. Artifact preview exists, but versioning/editing/source graph are minimal.
6. Projects, Research/Study and Calendar are honest roadmap surfaces.
7. Setup is developer-friendly scripts, not a signed desktop package.
8. No keyring-backed BYOK UX.
9. LAN is trusted-network HTTP; it is not remote access.

### 2.3 Product conclusion

P0 proves the corrected thesis: NeuroPA can be a usable AI harness rather than a wrapper around tasks. The next investment must deepen **context, provenance, permissions and continuity**—not multiply modules.

## 3. Architecture 2.0

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Premium Workspace UI                                               │
│ Session rail · chat · mode/provider/context · artifact canvas      │
│ Executive Function · Wiki/Memory · Projects · Skills · Settings    │
├─────────────────────────────────────────────────────────────────────┤
│ Local Application Services                                        │
│ SessionOrchestrator · ContextBuilder · SearchService               │
│ ArtifactService · MemoryLedger · ProjectService · ApprovalService  │
├─────────────────────────────────────────────────────────────────────┤
│ Policies                                                           │
│ EgressPolicy · ToolPolicy · EvidencePolicy · DataBoundaryPolicy    │
├─────────────────────────────────────────────────────────────────────┤
│ Stable Ports                                                       │
│ LLMProvider · SearchPort · ToolRunner · SecretStore · ExportPort   │
├─────────────────────────────────────────────────────────────────────┤
│ Local Adapters                                                     │
│ SQLite+FTS5 · filesystem · OpenCode · Ollama · OS keyring          │
│ local scheduler/notifier · optional Tauri shell                    │
└─────────────────────────────────────────────────────────────────────┘
                  optional, explicit, replaceable adapters
┌─────────────────────────────────────────────────────────────────────┐
│ PRIVATE SaaS REPO                                                  │
│ Auth/tenants · E2E sync · managed provider gateway · hosted backup │
│ entitlements/billing · operations (no OSS-domain duplication)      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 New P1 domain objects

| Object | Purpose | YAGNI boundary |
|---|---|---|
| `SourceRef` | Stable link to session/message/memory/artifact/project plus excerpt/hash/time. | No RDF database; W3C PROV concepts inform fields only. |
| `SessionEvent` | Append-only visible actions: provider choice, context selection, tool request, artifact created. | No hidden reasoning or raw chain-of-thought. |
| `ContextSelection` | Explicit sources included/excluded for one request. | No automatic “send everything.” |
| `ArtifactVersion` | Content hash, source message/session, previous version and local path. | Markdown/text first; no collaborative editor. |
| `SkillManifest` | Name, source/version, input/output schema and requested permissions. | Catalog before marketplace. |
| `ToolInvocation` | Tool, scopes, sanitized args summary, approval/result state. | No arbitrary execution in P1. |
| `ApprovalRequest` | Human decision for network/write/process/calendar/destructive scopes. | Deny by default. |
| `ProjectContext` | Purpose, next action, linked sessions/sources/artifacts. | One-user local project, no team collaboration. |

### 3.2 ContextBuilder

```text
user message
  + session.local_only / workspace policy
  + explicitly selected context
        ↓
SearchService (FTS5/BM25, type/time/project filters)
        ↓
ranked SourceRefs with excerpts and hashes
        ↓
context budgeter (never full-history by default)
        ↓
provider request + egress decision
        ↓
answer + citations + public ProcessSummary
```

Rules:

- No source is included merely because it exists.
- Local-only blocks remote providers server-side.
- Retrieved document instructions are untrusted data.
- Each persisted claim records source, capture time, evidence type and supersession.
- No evidence produces an explicit uncertainty state.
- ProcessSummary shows objective, short plan, actions/tools, sources, assumptions and result—not private model reasoning.

### 3.3 Search architecture

P1 uses SQLite FTS5 with BM25 and weighted fields:

- title/name: high weight;
- claim/artifact/session body: normal weight;
- tags/project/mode: filters, not prompt stuffing;
- recency and user-pinned source: bounded reranking.

**Embedding gate:** add local embeddings only if a frozen 100-query benchmark shows FTS5 Recall@5 below 85% on semantic paraphrases **and** the embedding lane fits local install/storage budgets. No external vector database in 2.0.

### 3.4 Provider architecture

`LLMProvider` contract evolves to:

```text
capabilities() -> models, stream, tools, vision, context limit, egress class
health()       -> configured / reachable / authenticated / limited
complete()     -> typed events or final result
cancel()       -> best-effort cancellation
```

Routing policy:

1. Session/workspace `local_only` → compatible local model or fail closed.
2. Explicit provider/model choice → no silent switch across privacy classes.
3. Default no-tech route → OpenCode free model selected from detected availability.
4. Fallback within the same egress class only unless the user confirms a change.
5. BYOK keys live in OS keyring; never frontend, SQLite, logs or exports.

OpenCode remains an adapter, not the domain. Its tools are disabled/denied until NeuroPA owns a tested permission profile.

### 3.5 Tool and skill security

A tool declares:

```text
fs_read · fs_write · network · process · calendar · destructive · open_world
```

MCP annotations are imported only as **untrusted hints**. NeuroPA computes the actual policy:

- read-only local search: allow when selected;
- artifact write inside workspace: ask once or use a user rule;
- network/process/calendar/destructive: contextual confirmation every time in P1;
- external content never grants permissions;
- provider cannot approve its own tool request;
- every invocation produces a sanitized event and result reference.

No skill execution ships until path containment, timeouts, output caps, approval UX and adversarial prompt-injection tests pass.

## 4. Premium UX architecture

“Premium” means calm control and continuity, not more cards.

### 4.1 Workspace hierarchy

1. **Transcript** is the visual center.
2. **Composer** always shows model, cognitive mode, selected context and egress.
3. **Session rail** answers “where was I?” with title, mode and last activity.
4. **Artifact canvas** opens only for a real saved output.
5. **Provenance drawer** answers “how does it know?” without displaying hidden thought.
6. **Executive Function** is a secondary recovery surface, not the home.

### 4.2 ADHD-first interaction contracts

- One primary decision per state.
- Capture never requires classification.
- Default outputs: one next step, optional expansion.
- “Resume without extra context” after abandonment.
- No streaks, red debt, overdue shame or engagement mechanics.
- Clear location, mode and progress for re-entry.
- Every visible action ≥44px (stricter than WCAG minimum).
- `prefers-reduced-motion`, focus trap, keyboard path and zero horizontal overflow.
- Roadmap views are explanations, never fake controls.
- Neurotypical users see the same product; no diagnostic gate.

### 4.3 P1 screens

- Workspace/chat with streaming and selectable context.
- Search overlay across sessions, memory and artifacts.
- Project continuity page with purpose, next action, sessions and outputs.
- Memory ledger with source/conflict/supersede review.
- Artifact versions with source graph and Markdown export.
- Skills catalog with permissions; execution still gated.
- Provider/keyring setup with configured/reachable/authenticated states.

## 5. Public OSS vs private SaaS

| Public OSS — complete local product | Private SaaS — optional convenience |
|---|---|
| Domain/entities/policies | OIDC, accounts, tenants |
| SQLite/FTS5 and filesystem | Postgres/RLS control plane |
| OpenCode/Ollama/BYOK | Managed inference gateway/quotas |
| Sessions/context/memory/artifacts/projects | Encrypted multi-device sync transport |
| Tool/skill manifests and local approvals | Hosted connectors/jobs after consent |
| Local export/import/backups | Encrypted hosted backup |
| No telemetry | Operational metrics only for hosted service, documented/consented |
| AGPL core + Apache SDK boundary | Billing/entitlements/MoR integration |

The SaaS consumes versioned ports/contracts. It must not fork domain semantics or make the public edition intentionally incomplete.

## 6. Eight-week execution plan

### Week 0 — certified baseline (complete)

- Correct product definition.
- P0 harness, free OpenCode, modes, sessions, artifacts, memory, setup.
- Security remediation and responsive QA.

**Gate:** 43 tests, browser 3/3, real AI, pairing replay rejection.

### Week 1 — FTS5 and SourceRef

- Schema/migration for SourceRef and FTS tables.
- Index sessions/messages/memory/artifacts.
- Search API with BM25, type/project/time filters.
- Frozen retrieval benchmark and citations UI.

**Gate:** Recall@5 ≥85% lexical set, 100% citations resolve to existing local objects, no source leak across workspace.

### Week 2 — ContextBuilder and streaming

- Explicit context chips: none/session/memory/artifact/project.
- Token/context budget and egress receipt.
- SSE typed events for text/status/usage/citations; cancellation.
- Failure preserves user input and partial result state.

**Gate:** no silent provider/privacy switch; cancel/retry/reload tests; 0 prompt in argv/logs.

### Week 3 — projects and artifact lineage

- Minimal ProjectContext: purpose, next action, linked sessions/sources/artifacts.
- ArtifactVersion and atomic export.
- “Save as artifact” / “link to project” confirmation flow.

**Gate:** every artifact resolves to source session/message/hash; rollback/import tests; no fake editor.

### Week 4 — memory ledger

- Claims, evidence, conflict and supersession review.
- Session-end proposal: save decisions/claims explicitly.
- Memory context is opt-in and source-cited.

**Gate:** contradiction tests; no-evidence state; old claim preserved after supersession; user can export/delete locally.

### Week 5 — skills/tool permissions (read-only pilot)

- SkillManifest parser with source/version/checksum/schema/scopes.
- ApprovalRequest UX and ToolInvocation ledger.
- Only built-in read-only search and artifact write pilot.
- Prompt-injection adversarial suite.

**Gate:** default deny; external text cannot grant permissions; destructive/process/network tools remain disabled.

### Week 6 — no-tech beta packaging

- Decide desktop shell using measured onboarding friction.
- If Tauri wins: minimal shell around existing local API, explicit capabilities, no extra frontend rewrite.
- Signed Windows/macOS/Linux release process; signed updates if enabled.
- OS keyring BYOK and uninstall/data retention flows.

**Gate:** fresh-machine install on three OS targets, signed artifact verification, no terminal after install, upgrade/rollback receipts.

### Week 7 — OSS beta and private adapter contract

- Public docs, examples, issue templates, security policy and migration guide.
- Stable SDK ports for sync/auth/managed inference—interfaces only in public repo.
- Private SaaS architecture ADR; no production SaaS build until OSS beta feedback.

**Gate:** five external beta users complete install→first session→artifact→resume without operator intervention; zero P0 security findings.

## 7. STOP / YAGNI list

Do **not** build in Plan 2.0 unless a gate fails and evidence justifies it:

- vector DB or cloud embeddings;
- CRDT/multi-device sync in the OSS P1 runtime;
- multi-agent swarms/autonomous delegation;
- skill marketplace or arbitrary shell execution;
- collaborative document editor;
- native mobile apps;
- always-on microphone/ambient surveillance;
- behavioral analytics, telemetry or engagement scoring;
- clinical diagnosis, symptom scoring or treatment claims;
- billing/auth/tenant code in the public core;
- full calendar OAuth integrations before local reminder/ICS demand;
- exposing chain-of-thought;
- fake roadmap forms, fake providers or mock AI responses in runtime.

## 8. Threat model and release gates

### Threats

- hostile LAN peer;
- malicious webpage on the same device;
- prompt injection inside files/web content;
- compromised provider/tool/skill;
- backup/import crafted to traverse paths or erase data;
- token/key leakage through argv, logs, frontend or exports;
- supply-chain compromise in installer/update.

### Required controls

- loopback default; explicit one-time LAN pairing; private narrow CIDR; replay/rate limits;
- HttpOnly device token; master token 0600 and never sent over LAN;
- least privilege, explicit approvals and untrusted tool annotations;
- path containment, atomic writes/import and schema/size validation;
- prompt via stdin, isolated provider cwd and sanitized logs;
- pinned dependencies, signed desktop builds/updates;
- security regression tests and Seraph re-review per release.

## 9. Acceptance suite

### Functional

- Fresh user completes setup without terminal when packaged.
- OpenCode free and Ollama local are detected honestly.
- Session/mode/model/context persist after reload.
- Context citations open the exact local source.
- Provider failure preserves message and data.
- Artifact lineage and checksum survive export/import.

### UX/accessibility

- Browser gates at 1600/768/480: 0 overflow/errors/failed API calls.
- Every visible action ≥44px; full keyboard operation; focus trapped/restored.
- First useful AI response in ≤3 user decisions after install.
- Abandoned session can be resumed without reclassification.
- Roadmap surfaces contain no executable fake control.

### Privacy/security

- No master token via LAN; one-time code replay rejected.
- Local-only cannot route remote even with crafted API payload.
- No prompt/key/token in argv, logs, HTML, SQLite export or artifact filename.
- Hostile import rolls back with zero data loss.
- Indirect prompt cannot expand tool permissions.

### Quality

- Unit/integration suite green.
- Retrieval benchmark frozen and versioned.
- Real provider smoke; no runtime mocks.
- Security/source manifests and screenshots preserved per release.

## 10. Agency benchmark rubric (100 points)

| Dimension | Weight | Pass condition |
|---|---:|---|
| Product fidelity | 15 | AI harness is primary; ADHD-first without clinical claims; no scope drift. |
| Functional completeness | 15 | Sessions→AI→artifact→memory/project→resume works with real providers. |
| Grounding/context | 15 | Resolvable citations, uncertainty state, provenance and retrieval benchmark. |
| UX/premium quality | 15 | Calm hierarchy, one primary action, 3-viewports, keyboard and 44px targets. |
| Privacy/security | 20 | Local ownership, egress transparency, permission model, adversarial gates, no P0 findings. |
| Reliability | 10 | Failure preservation, atomic data operations, reproducible tests and rollback. |
| Installability/open source | 10 | Fresh-machine no-tech setup, complete OSS core, docs/licenses/migrations. |

**Promotion threshold:** ≥85/100, no dimension below 70%, zero P0 security/QA findings and N30 human approval.

## 11. Immediate next decision

Run a five-user OSS beta on the corrected P0 before Week 1 scope expands. Collect only voluntary qualitative feedback—no telemetry—on:

1. setup friction;
2. whether the Workspace feels like an AI harness rather than a task app;
3. mode usefulness;
4. trust in egress/provenance;
5. ability to resume after interruption.

The next code block is FTS5 + SourceRef **only if** P0 feedback confirms the corrected product center. This protects YAGNI while preserving the premium architecture.
