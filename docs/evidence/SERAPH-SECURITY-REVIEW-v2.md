# Seraph Security & Privacy Review v2

**Scope:** NeuroPA local harness and LAN pairing at `12ff31a` (`fix: harden LAN pairing and responsive harness UX`).

**Reviewer:** Seraph security subagent
**Date:** 2026-08-01
**Mode:** Read-only source audit plus non-destructive tests. No production code changed.

## Verdict

**REQUEST_CHANGES / P0 security gate not approved.** The default loopback mode is materially safer than LAN mode, and the frontend avoids the obvious DOM XSS sinks, but LAN pairing currently exposes the full bearer credential to every client inside the configured CIDR. Separately, the OpenCode subprocess is started in the data directory and receives the complete prompt as a process argument; this is incompatible with the stated local-first/privacy boundary when OpenCode is remote.

## Evidence executed

- `python3 -m compileall -q neuropa tests` — **PASS**.
- `.venv/bin/pytest -q` — **32 passed in 2.90s**.
- `bash -n scripts/install.sh scripts/run-neuropa.sh scripts/uninstall.sh` — **PASS**.
- `git diff --check` — **PASS**.
- Repository/history credential-pattern scan for common AWS/OpenAI/GitHub/Slack token forms — **no matches**.
- Token file observed at `~/.local/share/neuropa/token`: mode `0600`, owned by the current user, 43 bytes.
- Direct CIDR behavior probe:
  - `192.168.1.50` in `192.168.1.0/24` → `True`.
  - `192.168.2.50` in `192.168.1.0/24` → `False`.
  - `not-an-ip` with valid CIDR → `False`.
  - `10.1.2.3` and `8.8.8.8` in `0.0.0.0/0` → `True`.
  - IPv4-mapped IPv6 `::ffff:192.168.1.50` is not accepted against the IPv4 CIDR.
- Static sink scan found OpenCode calls with `shell=False`, explicit timeouts, and no `innerHTML`/`eval`/`document.write` usage in the frontend.

The test suite is green, but it does not cover the destructive import, LAN token disclosure, Origin policy, prompt-in-argv exposure, imported-ID traversal, or OpenCode workspace isolation described below.

## Threat model

The primary threat is a malicious or compromised host on a Wi-Fi/LAN that the user considers trusted, plus a malicious webpage opened on the same machine, a same-user local process, and a malicious/compromised configured provider. NeuroPA stores private sessions, inbox, memory claims, artifacts, and the bearer token on disk. `--lan` binds Uvicorn to `0.0.0.0`; the bearer token is effectively full read/write authority for the API.

LAN mode is therefore not merely UI sharing: it is remote control of the local workspace. A CIDR is an address filter, not device identity, pairing proof, encryption, or authorization.

## Findings

### BLOCKER — LAN token endpoint is bearer-token disclosure, not pairing

**Where:** `neuropa/api/app.py:24-34, 128-134`; `neuropa/cli.py:100-108`.

`/api/token` returns the long-lived full API bearer token to any request whose source address is loopback or inside `NEUROPA_LAN_CIDR`. In `--lan` mode the default detected network is a `/24`; any host on that network can fetch the token directly. A malicious LAN peer does not need to guess, phish, or race a one-time code. `0.0.0.0/0` and `::/0` are also accepted if supplied by the operator, making accidental Internet-wide pairing possible when the server is reachable.

**Impact:** Full workspace read/write access, including export, import, message generation, artifact creation, and destructive state changes. Plain HTTP also permits interception on an untrusted network.

**YAGNI fix:** Keep loopback pairing as-is. For LAN, require an explicit one-time pairing code shown in the terminal and exchange it once for a random device-scoped token; never return the master token from a network endpoint. Reject non-private/non-link-local CIDRs and reject broad prefixes (at minimum IPv4 broader than `/16`, IPv6 broader than `/64`) unless an explicit expert override is added. Document that LAN is unauthenticated plaintext unless TLS/reverse proxy is supplied.

### BLOCKER — OpenCode subprocess can access the NeuroPA data root

**Where:** `neuropa/services/harness.py:64`; `neuropa/providers/opencode_cli.py:83-90`.

The harness passes `workspace=str(self.data_dir)` and OpenCode uses it as `cwd`. That directory contains `neuropa.db`, `token`, and `artifacts/`. OpenCode is explicitly a remote/free provider path, so a provider-side agent or tool execution operating from this cwd may discover local secrets and private records. `--pure` is not a filesystem sandbox.

**Impact:** Token/database/artifact disclosure or unintended writes from an optional provider integration; this defeats the local-first privacy boundary.

**YAGNI fix:** Use a dedicated empty project/workspace directory outside the data root, preferably a per-session directory with only explicitly exported project files. Never make the data directory the provider cwd. Do not claim filesystem isolation until an actual sandbox exists.

### HIGH — Prompt content is placed in the subprocess argv

**Where:** `neuropa/providers/opencode_cli.py:86-89`.

The entire system prompt plus up to twelve messages is joined into `prompt` and passed as the final command-line argument. On Linux, command arguments are observable to same-user processes through `/proc`; they may also appear in process-monitoring/audit tooling. This leaks private prompt content during every OpenCode invocation, even before provider egress is considered.

**YAGNI fix:** Pass prompt content through stdin if the OpenCode CLI supports it; otherwise use a short-lived `0600` input file in a dedicated workspace and pass only its path, then remove it. Add a regression test that asserts secrets are not present in the command argument list.

### HIGH — Imported message IDs enable artifact path traversal

**Where:** `neuropa/api/app.py:309-323`; `neuropa/services/harness.py:71-81`.

Import accepts caller-controlled `id` values for `ChatMessage` without schema or identifier validation. `create_artifact()` constructs `Path("artifacts") / f"{message.id}-{safe}.md"`. A valid authenticated import can use an ID containing `../` or an absolute/path-like component, then trigger artifact creation to write outside `data_dir`. The content-derived `safe` portion is sanitized, but the ID component is not.

**Impact:** Authenticated LAN attacker (or malicious backup) can overwrite/create files reachable by the NeuroPA user, subject to filesystem permissions.

**YAGNI fix:** Validate imported IDs against a strict UUID/opaque-ID regex, or ignore imported IDs and generate fresh IDs. Before writing, resolve the target and require `target.parent`/`target` to remain under the resolved artifacts root. Prefer a generated filename independent of user content and IDs.

### HIGH — Import is destructive before validation and is not atomic

**Where:** `neuropa/api/app.py:309-323`.

`DELETE FROM entities` is committed before payload rows are validated or created. A malformed row, unknown constructor field, duplicate ID, oversized payload, or process interruption leaves the database empty or partially imported. The endpoint has no transaction rollback, schema validation, payload size cap, or backup/restore boundary.

**Impact:** One bad import or compromised bearer token causes irreversible data loss. This is especially dangerous because LAN pairing currently exposes that bearer token to every CIDR member.

**YAGNI fix:** Parse/validate all rows first; import in one transaction; rollback on any error; only replace current data after validation succeeds. Add a small maximum request size and reject duplicate IDs/unknown entity fields. Offer an explicit `replace=true` semantics rather than silently destructive POST behavior.

### HIGH — WebSocket bearer is carried in the URL and Origin is not checked

**Where:** `neuropa/api/app.py:263-267`.

`/ws/focus?token=...` authenticates with a bearer in the query string and accepts any WebSocket Origin. Query strings can enter browser history, reverse-proxy/access logs, telemetry, screenshots, and referrer-like operational records. There is no Origin allowlist or same-origin check. The HTTP API's bearer-header requirement reduces classic cross-site CSRF for HTTP routes, but it does not solve a leaked query token or cross-origin WebSocket connection.

**YAGNI fix:** Authenticate the WebSocket with a header/cookie-backed mechanism that is not URL-visible; at minimum validate `Origin` against loopback/LAN UI origins and explicitly reject unexpected origins. If query auth must remain temporarily, redact query strings from logs and make the token short-lived/scoped.

### HIGH — Installer executes unauthenticated remote shell code

**Where:** `scripts/install.sh:54-60`.

The script improves on `curl | bash` by downloading to a visible temporary file, but it still executes the current contents from `https://astral.sh/uv/install.sh` without pinning a checksum, signature, or version. `--yes` makes this non-interactive and directly executable in automation.

**Impact:** DNS/TLS compromise, upstream compromise, proxy tampering, or URL replacement becomes arbitrary code execution as the user.

**YAGNI fix:** Pin a documented uv installer version and verify a published checksum/signature before `bash`; otherwise require manual download/review and keep the installer check-only path offline. Do not present “visible download” as integrity verification.

### MEDIUM — CIDR parsing is syntactically safe but policy-unsafe

**Where:** `neuropa/api/app.py:30-32`; `neuropa/cli.py:101-105`.

`ipaddress` parsing correctly rejects malformed input, but `strict=False` normalizes arbitrary networks and there is no policy check for private/local ranges or prefix width. The automatic `/24` is only a heuristic and may include unrelated devices; `0.0.0.0/0` is accepted and tested `True` for public hosts.

**YAGNI fix:** Validate that configured networks are private/link-local and narrow enough for the intended LAN. Print the detected host address and require explicit confirmation when the requested CIDR differs from the detected private network.

### MEDIUM — Privacy-sensitive/local-only is request-level, not a durable server policy

**Where:** `neuropa/api/app.py:80-85, 194-199`; `neuropa/services/harness.py:54-69`; `neuropa/providers/router.py:46-66`.

The `privacy_sensitive` flag forces `modes=["local"]` for that request and does not silently fall back to cloud, which is good. However, it is caller-controlled and not persisted as a session/workspace invariant; a direct API caller can omit it or set `false`, and the provider/model fields are also caller-controlled. This is a transparency/control gap rather than an observed bypass of a correctly marked request.

**YAGNI fix:** Persist a session/workspace `local_only` flag and enforce it server-side for every message in that scope. Return an explicit egress decision in the API response/log without logging content.

### MEDIUM — Provider egress labels can be optimistic or misrouted

**Where:** `neuropa/providers/router.py:26-38, 68-77`; `neuropa/core/providers/multi_engine.py:208-270, 335-454`.

The primary `ProviderRouter` labels OpenCode as `remote/free`, local as `local`, and the frontend renders remote egress warnings; this is a PASS for basic honesty. Residual risks remain: cloud “health” is only `bool(api_key)`, not reachability/auth health; `_cloud()` silently falls back to `api.openai.com/v1` when a managed provider value does not start with `http`; and the vendored `MultiEngine` has an always-healthy mock fallback that fabricates `[MOCK]` responses after engine failures. If that older wrapper is used by another path, it can make provider failure look like success and obscure egress reality.

**YAGNI fix:** Preserve provider ID/base URL in status, mark cloud health as `configured` rather than `healthy` until probed, reject malformed provider URLs instead of rewriting them, and remove/disable mock fallback outside explicit test mode.

### MEDIUM — Import/export and CLI export have privacy and overwrite edge cases

**Where:** `neuropa/api/app.py:305-323`; `neuropa/cli.py:32-50`.

Export correctly requires auth in the API, but it returns the complete workspace in one unbounded JSON response and the CLI writes an operator-selected path with direct overwrite semantics. The docs warn users to keep backups private, but there is no restrictive mode/atomic write for CLI output and no size limit for API import/export.

**YAGNI fix:** Use atomic temp-file + rename for CLI export, set mode `0600` when creating a new export, refuse an existing destination unless `--force`, and cap/stream API payloads if large workspaces are expected.

### LOW — Token creation has a minor race/permission-hardening gap

**Where:** `neuropa/api/app.py:40-45`.

The normal observed token mode is `0600`, and the test environment confirmed it. Creation uses `write_text()` then `chmod()`, leaving a small window where the process umask controls permissions; concurrent first requests can also race. This is low risk for a single-user local process but avoidable.

**YAGNI fix:** Create with `os.open(..., O_CREAT|O_EXCL, 0o600)` and handle an existing file; optionally verify mode/owner before use.

## Clean / passing areas

- **Secret literals:** No common credential patterns were found in the working tree or Git history scan. Configuration reads keys from environment; the token file is mode `0600` in the observed environment.
- **Subprocess shell injection:** OpenCode uses an argument list, `shell=False`, and explicit timeouts. User prompt content is not shell-interpreted; the remaining argv privacy issue is separate.
- **Artifact content filename sanitization:** The content prefix is reduced to `[A-Za-z0-9_-]` and cannot itself introduce `../`; traversal still exists through imported `message.id`.
- **Frontend XSS handling:** Dynamic application content is created through DOM nodes and `textContent`; static HTML contains no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `eval`, or `document.write` sink in the audited file.
- **localStorage:** Only `wizard_done` and `selected_path` are persisted. The bearer token is held in memory (`state.token`) and is not written to localStorage. The selected path is not a secret.
- **Uninstall default behavior:** Repository root is canonicalized with `pwd -P`; default removal is an explicit repository cache allowlist; `--dry-run` and exact `PURGE NEUROPA DATA` confirmation were covered by tests. Residual hardening would be a symlink/race-aware deletion helper and a stronger data-directory identity check.
- **CSRF on ordinary HTTP routes:** Authenticated routes require an `Authorization: Bearer` header, so a normal cross-site form cannot supply credentials. This is not a substitute for Origin enforcement once a token is leaked or for WebSocket handling.

## P0 remediation order

1. Remove the master-token-over-CIDR design; implement one-time LAN pairing or keep LAN disabled by default.
2. Stop OpenCode from using the data directory as cwd and stop placing private prompts in argv.
3. Make import validate-then-commit atomically, with strict IDs; fix artifact target containment.
4. Remove WebSocket query-token auth or add short-lived scoped tokens plus Origin validation.
5. Pin/verify the installer download and tighten CIDR policy.
6. Persist/enforce local-only at session/workspace scope and make provider status/egress claims exact.

No code changes were made in this review; this report is the only intended worktree artifact.
