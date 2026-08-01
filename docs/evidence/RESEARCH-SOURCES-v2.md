# NeuroPA 2.0 — Research Sources and Decisions

**Research date:** 2026-08-01  
**Method:** official/primary sources located through live web search, cross-checked against the installed OpenCode/Ollama/SQLite runtime and the implemented NeuroPA P0. The configured web backend is search-only, so findings below are limited to indexed official descriptions and locally verified behavior; no unverified page detail is claimed.

## Source ledger

| # | Source | Verified finding | NeuroPA decision |
|---|---|---|---|
| 1 | [OpenCode CLI](https://opencode.ai/docs/cli/) | OpenCode exposes CLI commands, provider authentication and model selection. Local verification confirmed `opencode run --pure --format json -m …` and JSONL events. | Keep OpenCodeCLI as the no-tech/free-first bridge; parse public text/usage only; prompt via stdin; never expose private reasoning. |
| 2 | [OpenCode Providers](https://opencode.ai/docs/providers/) | OpenCode documents support for 75+ providers through AI SDK/Models.dev and local models; provider credentials are configured explicitly. | NeuroPA uses an adapter and capability discovery instead of rebuilding 75 integrations. Credential UI remains a later keyring-backed adapter. |
| 3 | [OpenCode Agents](https://opencode.ai/docs/agents/) and [Permissions](https://opencode.ai/docs/permissions/) | Agents combine prompts/model/tool permissions. Permission keys can deny or ask for built-in, custom and MCP tools. | Agent modes remain declarative. Tools default deny/ask; no autonomous process/network tool in P0. |
| 4 | [OpenCode Tools](https://opencode.ai/docs/tools) | Built-ins and MCP tools can act on a codebase; behavior is controlled through permissions. | An OpenCode CLI bridge is not a sandbox. NeuroPA uses isolated cwd and will add explicit permission profiles before enabling tools. |
| 5 | [Ollama chat API](https://docs.ollama.com/api/chat) and [model listing](https://docs.ollama.com/api/tags) | Ollama provides local chat and model discovery endpoints. | Ollama stays the local-only provider. Detection must distinguish installed runtime from an actually available model. |
| 6 | [SQLite FTS5](https://www.sqlite.org/fts5.html) | FTS5 supports full-text `MATCH` and BM25 ranking/column weights. | Implement lexical/BM25 retrieval before adding embeddings or a vector database. |
| 7 | [W3C COGA — short critical paths](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o5p02-short-paths/) | Streamlined workflows reduce distraction, mistakes and mental fatigue. | Composer-first home, one primary action, short setup and explicit recovery paths. |
| 8 | [W3C COGA — clear steps](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o1p04-clear-steps/) | Clear current location/progress helps users resume after loss of focus. | Session rail, current mode/provider, process summary and re-entry copy remain visible. |
| 9 | [W3C COGA — manageable quantity](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o5p03-manageable-quantity/) | Simplified content and consistent design reduce overload and fatigue. | No dashboard/KPI theater; progressive disclosure; roadmap controls are non-interactive. |
| 10 | [WCAG 2.2 target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | WCAG 2.2 defines a 24×24 CSS px minimum with exceptions. | NeuroPA intentionally sets a stronger product gate: every visible action ≥44 px at 1600/768/480. |
| 11 | [NIMH ADHD information](https://www.nimh.nih.gov/health/publications/adhd-what-you-need-to-know) | NIMH is an authoritative source for symptoms, diagnosis, treatment and support; diagnosis/treatment belong to qualified care. | NeuroPA is cognitive scaffolding, not diagnosis or treatment. No clinical outcome claims, symptom scoring or medication advice. |
| 12 | [MCP Authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) | MCP defines transport-level authorization for restricted HTTP servers. | Remote MCP is P2 only, with explicit auth and scopes; local tools do not inherit blanket trust. |
| 13 | [MCP Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) and [schema](https://modelcontextprotocol.io/specification/2025-06-18/schema) | Tool annotations include read-only/destructive/idempotent/open-world hints, but clients must treat annotations as untrusted unless the server is trusted. | Store annotations as hints, then enforce NeuroPA-owned permissions and approvals independently. |
| 14 | [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) and [AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) | OWASP recommends least privilege; agent tool abuse and indirect prompt injection are core risks. | Retrieved content is data, never authority. Tool execution is allowlisted, scoped, confirmed and logged without sensitive payloads. |
| 15 | [Ink & Switch local-first](https://www.inkandswitch.com/essay/local-first/) | Local-first prioritizes ownership, offline work, longevity and user control while allowing optional collaboration. | SQLite/filesystem are the primary copy. SaaS sync is an optional private adapter, never a dependency of the OSS core. |
| 16 | [W3C PROV Overview](https://www.w3.org/TR/prov-overview/) | Provenance models identify objects, attribution and processing steps. | NeuroPA SourceRef/SessionEvent/ArtifactVersion record source, actor/provider and transformation without storing hidden chain-of-thought. |
| 17 | [Tauri capabilities](https://v2.tauri.app/security/capabilities/) | Tauri 2 constrains frontend access to core/plugin commands through capabilities and permissions. | Tauri is a conditional P2 desktop shell, not P1. Adopt only after the browser-local product proves retention and packaging is the measured blocker. |
| 18 | [Tauri updater](https://v2.tauri.app/plugin/updater/) | Tauri updater requires signed updates and does not allow signature verification to be disabled. | If desktop packaging is promoted, signed artifacts/updates are release gates, not polish. |
| 19 | [Python `secrets`](https://docs.python.org/3/library/secrets.html) | `secrets` is intended for authentication tokens and related secrets. | Pairing codes/device tokens use `secrets`; master token remains 0600 and is never returned over LAN. |

## Live evidence that constrains the plan

- Installed OpenCode `1.15.6` listed seven free models and returned exact JSONL text through stdin.
- Ollama executable exists, but no local model was detected; UI correctly marks it unavailable.
- NeuroPA P0 has 43 tests and a reproducible Playwright gate at 1600/768/480.
- One-time LAN pairing issues an HttpOnly cookie, removes the URL fragment, rejects replay and does not expose the master token.
- The current workspace supports sessions, four cognitive modes, real AI chat, memory claims, artifacts, provider status, capture/Today and honest roadmap surfaces.

These sources support an incremental harness roadmap. They do **not** support prematurely adding multi-agent autonomy, vector infrastructure, CRDT sync, a skill marketplace or clinical features.
