# Seraph Security Closure v2 — Harness Gate

**Date:** 2026-08-01
**Repository:** `projects/neuro-sass/neuropa`
**Base reviewed:** `f922720` (`docs: define the research-backed NeuroPA 2.0 plan`)
**Review mode:** Read-only source inspection plus non-destructive regression probes. No production code changed.

## Verdict

**PASS — no remaining blocker/high findings.**

The prior v2 blocker/high findings are closed by the remediation present at HEAD. One medium hardening note remains: a non-browser WebSocket client with a valid device cookie and no `Origin` header is accepted; browser cross-origin attempts with a mismatched Origin are rejected, and LAN query-token authentication is rejected. This does not reopen the prior high-impact bearer/query-token finding, but a future hardening change should reject missing/`null` Origin when the deployment requires browser-only WebSockets.

## Fresh verification evidence

- `python3 -m compileall -q neuropa tests` — **PASS**.
- `.venv/bin/pytest -q` — **43 passed, 1 deprecation warning**.
- Focused suite: `.venv/bin/pytest -q tests/test_security_remediation.py tests/test_installer_scripts.py tests/test_opencode_p0.py tests/test_harness_p0.py` — **16 passed, 1 deprecation warning**.
- `bash -n scripts/install.sh scripts/run-neuropa.sh scripts/uninstall.sh` — **PASS**.
- `git diff --check` — **PASS**.
- Secret-pattern scan with `git grep` for common AWS/OpenAI/GitHub/Slack credentials and PEM private-key headers — **no matches**. The evidence document contains no credentials or live token values.
- Pairing object probe — six invalid attempts are rejected; successful code is consumed; replay is rejected; device token is accepted only from the issuing host.
- Installer static policy probe — no `curl`, `wget`, remote uv installer, or `bash "$installer"`; OpenCode install is pinned to `opencode-ai@1.15.6`.
- WebSocket probe with paired LAN cookie and matching `Host`/`Origin` — **accepted**; mismatched evil Origin — **rejected** (`WebSocketDisconnect`). A LAN query token is rejected by source logic.

## Closure map for SERAPH-SECURITY-REVIEW-v2

| Prior finding | Severity then | Re-test / current control | Status |
|---|---:|---|---|
| LAN `/api/token` disclosed master bearer to CIDR clients | BLOCKER | `/api/token` is loopback-only and returns only a pairing state/cookie; LAN probe returned `403`. LAN pairing issues a device token, not the master token. | **CLOSED** |
| OpenCode could access data root through `cwd` | BLOCKER | `HarnessService` uses `~/.cache/neuropa/opencode-workspaces/<session-id>` with mode `0700`; it does not use the database/token/artifact root. Regression test passed. | **CLOSED** |
| Prompt content in OpenCode argv | HIGH | `OpenCodeCLI.generate()` supplies the prompt via `subprocess.run(..., input=prompt)`; argv contains only static flags and model. Temporary executable probe confirmed `TOP_SECRET` absent from argv and present on stdin. | **CLOSED** |
| Imported message IDs enabled artifact traversal | HIGH | Import requires UUID IDs and rejects slash/backslash/path-like IDs; artifact names use a generated UUID, resolve under `artifacts/`, and are written via temp-file plus `os.replace`. Hostile import probe returned `400`; existing data remained. | **CLOSED** |
| Import deleted data before validation / lacked atomic rollback | HIGH | Payload is size-capped, explicit `replace=true`, fully validated for types, fields, UUIDs, duplicates, and entity types before replacement. `Database.replace_entities()` wraps delete/create in `BEGIN`/`commit` with rollback on exception. Validation-before-delete regression passed. | **CLOSED** |
| WebSocket bearer in URL and unrestricted Origin | HIGH | LAN WebSockets require the host-bound HttpOnly device cookie; query bearer is accepted only for loopback and is rejected when a LAN client supplies it. Origin host must match Host; evil Origin probe rejected. | **CLOSED** |
| Installer executed mutable remote shell code | HIGH | Installer no longer downloads/executes a remote uv shell. Missing uv gives manual official instructions. OpenCode npm install is explicitly pinned to `1.15.6` and confirmation-gated. Static and bash checks passed. | **CLOSED** |

## Other requested controls

- **One-time code replay/rate/CIDR:** invalid attempts are capped at five per source; the one-time code is cleared after successful pairing; replay fails; configured CIDRs reject public/broad networks and accept private/link-local ranges only.
- **HttpOnly cookie host binding:** cookie is `HttpOnly`, `SameSite=Strict`, eight-hour max age; device token validation binds it to the issuing client host. Reusing the cookie from another host was rejected.
- **`local_only` enforcement:** session `local_only` is persisted; `HarnessService.send_message()` passes `privacy_sensitive=True` to the router regardless of caller-selected provider/model. The router reduces the mode list to `local` only. Focused test passed.
- **No secrets in repo/evidence:** targeted repository scan returned no common credential/private-key patterns; no token values were copied into this report.

## Residual medium note

The WebSocket handler treats a missing/invalidly unparsable Origin as absent and permits a valid cookie. The tested browser-relevant cross-origin case (`Origin` host different from `Host`) is rejected, and SameSite-Strict limits browser cookie transmission cross-site. For a stricter browser-only contract, reject missing/`null` Origin explicitly and maintain an allowlist of expected origins. This is recorded as medium hardening, not a blocker/high closure failure.

## Worktree / commit boundary

Only this evidence file is intended to be added by this review. Existing unrelated untracked evidence was left untouched. No push performed.
