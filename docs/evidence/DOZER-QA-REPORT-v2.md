# Dozer adversarial QA review — NeuroPA v2 harness

**Review date:** 2026-08-01  
**Scope:** commits `d88def0`, `27b527b`, `6c4fec8`, `12ff31a`, plus current `HEAD` live state.  
**Reviewer mode:** fail-closed; no source code changes were made.  
**Global verdict:** **FAIL / DO NOT MERGE**. There are HIGH findings; the existing green checks are not sufficient for release.

## Evidence executed

- `uv run pytest -q --disable-warnings --maxfail=1` → **32 passed** in 4.75s (one environment warning: active `VIRTUAL_ENV` points at a different project).
- `TestClient` against fresh temporary SQLite databases, with fake router only for deterministic local QA. No repository/user data was deleted.
- Live API/browser at `http://127.0.0.1:8474/`: authenticated read-only probes, real DOM snapshot, setup wizard interaction, browser console clear.
- Existing evidence read and integrity-checked:
  - `desktop-1600x1000.png`: actual PNG `1600 x 1063`
  - `tablet-768x900.png`: actual PNG `768 x 1078`
  - `mobile-480x860.png`: actual PNG `480 x 1218`
  - `viewport-results.json` reports all three `passed: true`, no JS/console errors, no HTTP >=400 responses, and no horizontal overflow.
- `tools/qa_frontend.py` could **not** be re-executed in this checkout: both system Python and `uv run python` report `ModuleNotFoundError: No module named 'playwright'`. This is a verification gap, not a frontend PASS.
- Screenshot visual analysis was attempted but the configured vision backend returned HTTP 403 regional availability error. Conclusions below rely on actual image dimensions, DOM/runtime inspection, source audit, and the recorded viewport metrics; no visual claim is made beyond that evidence.

## Gate matrix

| Gate | Result | Evidence / rationale |
|---|---|---|
| Test suite baseline | **PASS WITH NOTE** | 32/32 pass. Playwright QA runner is not reproducible because dependency is absent. |
| API auth and read contracts | **PASS** | Unauthenticated `/api/workspaces` and `/api/agent-modes` return 401; bearer-authenticated reads return 200. `/api/health` is intentionally public. |
| Session mode IDs / persistence | **FAIL — HIGH** | API returns the selected `mode_id` on message records, but does not persist it back to the session. Repro: session created with `clarity` ID `4e6f0d84-8577-4510-bb73-0e55ff154d23`; send with `detail` ID `e65af30b-6497-4366-bec0-f18b6563bc52`; assistant/user records carry `detail`, while `GET /api/sessions/{id}` still returns session `mode_id=clarity`. Reloading the frontend therefore reverts the selected mode. |
| Message persistence and provider failure | **PASS** | Fresh DB TestClient run: successful send persists user `sent` + assistant `completed`; forced provider failure returns 503 with “tu mensaje quedó guardado” and persisted user row has `status=failed`. |
| Privacy-sensitive routing | **PASS WITH NOTE** | Test router received `privacy_sensitive=True` and `mode=local`; router code forces `modes=["local"]`. If local is unavailable it fails closed with 503. |
| Artifact path/checksum | **PASS WITH NOTE** | Artifact was created with relative `artifacts/<message-id>-answer.md`, SHA-256 in `blob_ref` and `links.checksum`, and path stays inside the service data dir. Implementation uses `target.read_bytes()` (`neuropa/services/harness.py:80`), which is non-streaming for large artifacts and lacks a re-open/re-verify step. |
| Setup wizard | **PASS WITH NOTE** | Live DOM showed real capability state: OpenCode enabled, Ollama/BYOK disabled; copy explicitly disclosed remote egress and “seguir sin IA”. No credentials entered into localStorage. Focus restoration exists, but there is no focus trap while the modal is open. |
| No fake controls / honest roadmap | **PASS** | `projects`, `research`, and `calendar` visibly carry `Roadmap`; source says no false forms/CTA; Skills explicitly says tools are not executed yet. |
| LAN pairing scope | **FAIL — HIGH** | `--lan` accepts any syntactically valid CIDR (`neuropa/cli.py:100-106`) and sets `host=0.0.0.0`; `/api/token` grants the bearer to every client inside that CIDR (`neuropa/api/app.py:129-134`). `0.0.0.0/0` or a broad public CIDR is not rejected. This contradicts “trusted LAN” and makes the bearer retrievable by arbitrary reachable clients. |
| Accessibility | **FAIL — HIGH** | Existing QA only enforces 44px minimum on mobile. Recorded metrics show `targetMin=34.234375` at 1600px and `targetMin=36` at 768px. Live DOM confirms 34.2px provider chip, 36.2px command-palette button, and 36px composer chips. Desktop/tablet interactive targets are below the 44px target used by the mobile gate. Setup and palette are `role=dialog aria-modal=true` but lack a focus trap. |
| Mobile composer | **PASS WITH NOTE** | Recorded 480px evidence: no horizontal overflow, composer width 456, target min 44, expected four-item mobile nav, no captured JS/console errors. Runner was not reproducible here because Playwright is missing. |
| Installer safety | **FAIL — HIGH** | `scripts/install.sh:55-59` downloads `https://astral.sh/uv/install.sh` and immediately executes it with `bash`, without checksum/signature verification. Under `--yes`, `scripts/install.sh:117-119` also installs unpinned `opencode-ai` globally via npm. Tests cover syntax/read-only/purge confirmation, not supply-chain integrity. |
| Data-destructive API surface | **FAIL — MEDIUM/HIGH** | Authenticated `POST /api/import` unconditionally executes `DELETE FROM entities` before validating/importing the payload (`neuropa/api/app.py:309-323`). It is not used by this QA, but a malformed/partial import can destroy the local workspace. No transaction/rollback or backup guard exists. |
| False-green protection | **FAIL — HIGH** | The committed frontend runner can report all viewports green while the runner is absent from the declared environment and while its desktop/tablet target-size assertion is intentionally weaker than its mobile assertion. Existing green JSON is evidence of that runner’s prior environment, not a reproducible release gate. |

## Findings, prioritized

### P0 / blocker candidates

No demonstrated data-loss or unauthorized-access exploit was executed against production data. However, release remains blocked by the HIGH findings below; no global PASS is permitted.

### HIGH-01 — Session mode selection is not durable (**BLOCK release**) 

**Where:** `neuropa/services/harness.py:44-69`; frontend `index.html:118-132`.  
**Observed:** `POST /api/sessions/{id}/messages` accepts `mode_id` and stores it on message rows, but never updates `ChatSession.mode_id`. The exact TestClient run above shows the selected `detail` UUID on both message rows and the old `clarity` UUID on the session.  
**Impact:** after reload/reopen, `loadSession()` derives `state.mode` from the stale session mode, so a user’s selected agent mode silently changes back. This violates the session mode ID contract and can make subsequent prompts route with the wrong system prompt.  
**Exact fix:** validate `mode_id` against `agent_mode`; in the same transaction as message creation/update, persist `session.mode_id=mode.id` and `session.provider_id=selected_provider` (and `session.model=model`) before/with the send. Add a reload test asserting selected mode/provider/model survive `GET /api/sessions/{id}` and a second send.

### HIGH-02 — LAN pairing can expose the bearer outside a trusted LAN (**BLOCK release**) 

**Where:** `neuropa/cli.py:100-106`; `neuropa/api/app.py:129-134`.  
**Observed:** arbitrary valid CIDR is accepted and the server binds to `0.0.0.0`; `/api/token` returns the long-lived token to any request whose source IP is in that CIDR.  
**Impact:** a typo or broad CIDR (`0.0.0.0/0`, public network, or overly broad shared network) makes token theft trivial for any reachable client. The browser then uses that bearer for all authenticated API calls.  
**Exact fix:** reject unspecified/global/loopback/multicast/reserved networks; require a private/link-local network and enforce a documented maximum scope. Do not return the bearer to LAN clients by default: use a one-time pairing code displayed locally, bind the issued session token to the pairing client, expire it, and rate-limit `/api/token`. Add tests for `0.0.0.0/0`, `::/0`, public CIDRs, and a valid private `/24`.

### HIGH-03 — Desktop/tablet accessibility gate is false-green (**BLOCK release**) 

**Where:** `tools/qa_frontend.py:36-38,58-65`; source CSS `neuropa/frontend/index.html:9-16`.  
**Observed:** recorded results say `passed=true` for desktop/tablet despite `targetMin=34.234375` and `targetMin=36`; the 44px assertion is only applied when `name == "mobile"`. Live DOM confirms provider/model/context controls at 36px and a 34.2px provider rail button.  
**Impact:** keyboard/mouse/touch interaction is harder on exactly the large and tablet layouts most likely to be used at a desk; the green QA artifact masks the defect.  
**Exact fix:** use a shared minimum target assertion for every viewport (`>=44` unless an explicitly documented exception), measure all visible actionable controls including dynamically-created buttons, and fail the runner if Playwright is unavailable. Add focus-visible and dialog focus-trap assertions.

### HIGH-04 — Installer executes mutable remote code without integrity pinning (**BLOCK release**) 

**Where:** `scripts/install.sh:55-59,117-119`.  
**Observed:** remote shell installer is downloaded and executed; npm package is installed globally without a version or lock/integrity check.  
**Impact:** compromised DNS/TLS endpoint, package takeover, or registry drift becomes arbitrary code execution during setup.  
**Exact fix:** prefer a package-manager/verified release path; otherwise pin a version and verify a published SHA-256/signature before execution, abort on mismatch, and record the installed versions. Pin `opencode-ai` to a reviewed version and use a project-local environment rather than global npm by default.

### HIGH-05 — Playwright gate is not reproducible in the project environment (**BLOCK release**) 

**Where:** `tools/qa_frontend.py`, `pyproject.toml`/lockfile.  
**Observed:** `python3 tools/qa_frontend.py` and `uv run python tools/qa_frontend.py` both fail immediately with `ModuleNotFoundError: No module named 'playwright'`; there is no successful fresh run from this checkout.  
**Impact:** viewport evidence cannot be independently regenerated; `docs/evidence/qa-v2/viewport-results.json` can remain green after frontend regressions.  
**Exact fix:** declare Playwright as a dev dependency, install browsers in the documented QA setup, run the tool via one canonical command in CI, and make the gate assert the expected dependency/version. Do not commit/update evidence unless the canonical command succeeds.

### MEDIUM — Import endpoint can wipe the database before validation

**Where:** `neuropa/api/app.py:309-323`.  
**Exact fix:** parse and validate every entity first; wrap replacement in a transaction; create a timestamped backup; rollback on any constructor/DB error; reject unknown entity types or report them explicitly. Add malformed/partial import tests and a recovery test.

### MEDIUM — Artifact hashing is not robust for large files / TOCTOU

**Where:** `neuropa/services/harness.py:71-81`.  
**Exact fix:** hash incrementally through an opened file descriptor, write atomically via temp file + rename, then re-stat/re-hash immediately before registering the artifact; add a large-file and concurrent replacement test.

### MEDIUM — Dialog accessibility lacks focus containment

**Where:** `neuropa/frontend/index.html:25-33,134-141`.  
**Observed:** both dialogs advertise `aria-modal=true`; code saves/restores focus but only handles Escape and does not trap Tab inside the active dialog.  
**Exact fix:** implement a reusable modal controller that traps Tab/Shift+Tab, marks background inert while open, restores focus on close, and tests keyboard traversal for setup and command palette.

## What passed cleanly

- SQLite entity persistence and soft-delete paths exercised by the existing 32-test suite.
- Missing bearer protection on authenticated read/write endpoints.
- Failure-path message retention and explicit 503 response.
- Privacy-sensitive provider selection failed closed to local-only rather than falling back to remote.
- OpenCode JSONL parser hides reasoning events and retains only public text/usage in its unit test.
- Roadmap surfaces are labeled honestly; no fake project/research/calendar forms were observed.
- Mobile recorded evidence has no horizontal overflow and the composer is wide enough at 480px.

## Required re-review checklist

1. Fix HIGH-01 through HIGH-05 and add regression tests.
2. Re-run `uv run pytest -q` in a clean project environment.
3. Re-run the canonical Playwright command at 1600, 768, and 480; require 44px targets at all viewports and zero HTTP/JS errors.
4. Re-test LAN pairing with private valid CIDR plus public/broad/unspecified CIDR rejection.
5. Test provider/mode/model persistence across reload and forced provider failure.
6. Test installer checksum/signature mismatch and offline behavior.
7. Test import rollback with malformed payload; verify no pre-import entities are lost.
8. Re-submit only after a new evidence bundle is generated by the reproducible runner.

**Final decision:** **FAIL — no global PASS.**
