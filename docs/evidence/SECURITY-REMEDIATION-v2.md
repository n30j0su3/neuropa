# NeuroPA P0 Security & QA Remediation v2

**Date:** 2026-08-01  
**Scope:** findings from `SERAPH-SECURITY-REVIEW-v2.md` and `DOZER-QA-REPORT-v2.md`.

## Closed release blockers

| Finding | Remediation | Regression evidence |
|---|---|---|
| LAN returned master bearer to CIDR | `/api/token` is loopback-only and returns no bearer. It issues a device-scoped HttpOnly/SameSite cookie. LAN requires one-time pairing code from URL fragment; code is consumed after one use. | `test_pairing_is_one_time_cookie_and_token_endpoint_is_loopback_only`; live LAN: fragment removed, cookie invisible to JS, replay 403, `/api/token` 403. |
| Broad/public CIDRs accepted | LAN requires private/link-local IPv4 `/24+` or IPv6 `/64+`; public, unspecified, multicast, loopback and broad networks fail. | `test_cidr_policy`; CLI tests. |
| OpenCode ran inside data root | Provider cwd is now a dedicated `~/.cache/neuropa/opencode-workspaces/<session-id>` directory, never the DB/token/artifact directory. | `test_opencode_prompt_is_stdin_and_workspace_is_outside_data_root`. |
| Prompt exposed in process argv | Full prompt is sent through stdin; argv contains only static OpenCode flags/model. | Temporary executable regression test rejects prompt in argv and requires it on stdin; real OpenCode stdin smoke passed. |
| Mode/provider/model reverted after reload | Successful sends update the session with validated mode ID, provider ID and model. Session-level `local_only` is persisted and enforced. | `test_session_send_persists_mode_provider_model_and_local_only`. |
| Imported IDs could traverse artifact path | Artifact filenames use generated UUIDs; resolved path must remain under artifact root; atomic write and streaming SHA-256. | `test_artifact_filename_is_generated_and_contained`. |
| Import deleted before validation | Import requires explicit `replace=true`, validates all types/fields/UUIDs/duplicates first, enforces size limit and replaces within one transaction. | `test_import_rejects_hostile_payload_without_deleting_existing_data`. |
| WebSocket token in LAN query / no Origin check | LAN focus WebSocket uses device cookie only; query bearer remains loopback-only; Origin and Host must match. | Source review + security test suite. |
| Mutable remote installer code | Installer no longer downloads or executes the remote uv shell. Missing uv fails with official manual instructions. OpenCode npm install is pinned to reviewed `1.15.6` and still requires explicit confirmation. | `test_installer_does_not_execute_remote_uv_shell_and_pins_opencode`; bash syntax/check mode. |
| Non-reproducible visual QA | Playwright `1.62.0` is a project dev dependency. Canonical gate is `uv run python tools/qa_frontend.py`; it fails closed when unavailable. | Canonical run PASS in project `.venv`. |
| False-green 34–36px targets | All visible actionable controls are at least 44px in desktop/tablet/mobile; modal focus trap and inert background added. | `viewport-results.json`: targetMin=44 for 1600/768/480, zero overflow/HTTP/JS/console errors. |

## Final executed gates

- `uv run pytest -q` → **43 passed**.
- `python3 -m compileall -q neuropa tests tools` → **PASS**.
- `bash -n scripts/install.sh scripts/run-neuropa.sh scripts/uninstall.sh` → **PASS**.
- `scripts/install.sh --check` → **PASS**, detected OpenCode `1.15.6`.
- `uv run python tools/qa_frontend.py` → **PASS** at 1600×1000, 768×900, 480×860.
- Real OpenCode free provider via LAN paired cookie → response `LAN_AI_OK`.
- LAN pairing replay → **403**; LAN master-token bootstrap → **403**.

## Residual P1 hardening (not P0 blockers)

- HTTPS for use outside a trusted private LAN; LAN remains explicit and temporary.
- OS keyring and encrypted-at-rest workspace option.
- Scoped tool sandbox before enabling arbitrary skills/process execution.
- Streaming responses/cancellation at provider transport level.
- Signed desktop packages and platform-native installer.

The public OSS core remains functional without the private SaaS repository. No telemetry was added.

## Product-policy update — 2026-08-04

N30 removed mandatory pairing from the trusted-LAN default because it was an unnecessary
local usability barrier. `--lan` now grants direct access only to clients inside the
validated private `/24+` or `/64+` CIDR; `/api/token` remains loopback-only and the master
bearer is never returned to LAN clients. The one-time gate remains available as the explicit
opt-in `--lan --pairing`. Regression coverage: direct trusted LAN 200 without cookie,
pairing opt-in 401 before pairing, one-time code replay 403, and public/broad CIDRs rejected.
