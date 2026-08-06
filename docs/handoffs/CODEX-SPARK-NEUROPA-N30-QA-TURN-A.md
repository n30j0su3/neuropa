# Codex-Spark execution brief — NeuroPA N30 Human-QA Turn A

## Role

You are the bounded implementation executor for **Turn A only** of the NeuroPA human-QA corrective program.

Read first:

1. `docs/plans/2026-08-04-n30-human-qa-corrective-program.md`
2. `PRODUCT.md`
3. `neuropa/frontend/index.html`
4. `neuropa/services/harness.py`
5. `neuropa/api/app.py`
6. relevant tests under `tests/`
7. `/home/freakingjson/.hermes/skills/creative/impeccable/SKILL.md`
8. `/home/freakingjson/.hermes/skills/agency/agency-ux-ui-master/SKILL.md`

## Objective

Fix the P0 interaction and product-semantics gaps confirmed by N30's desktop human QA without implementing Turn B agent/Skills/MCP/provider management or Turn C Wiki/force graph.

## Repository and custody

- Root: `/home/freakingjson/Hermes-Stuff/projects/neuro-sass/neuropa`
- Branch: `feat/p1-integrated`
- HEAD: `81c6929c39f318742fb2fc4fe9818b4f3e573e82`
- Worktree is intentionally dirty from prior G/R work. Preserve every unrelated change.
- Do not commit, push, reset, restore, checkout files, rewrite history, or replace the SPA wholesale.

Pre-turn hashes:

```text
9e63fa92f404d69f6b6eaca4387bdd41d8e080365ec789e4aee80d9212085911  neuropa/frontend/index.html
9bf15f3714e3e4ffb70760b77946ccfaf38af7580169303d397915bc552fddc9  neuropa/api/app.py
d28291427ce99b39500e1bff073b8fddd1b591ade663240a94a7de91023329ea  neuropa/services/harness.py
23132e36d5c9537fa09f0c2831cadc8c0c508fece5b99a5275340c5d8779a38e  neuropa/memory/graph.py
dd6e13ec63abfb6bff4685d6c43d5593653f2f3ee0c4997245aaeca02e8b4bc5  neuropa/domain/models.py
```

## Allowed files

- `neuropa/frontend/index.html`
- `neuropa/services/harness.py`
- `neuropa/api/app.py` only for bounded Turn A API/telemetry/session-export changes
- targeted/new tests under `tests/`
- new Turn A evidence/receipt under `docs/evidence/ux-audit-2026-08-04/`
- this handoff's execution-result section

## Forbidden files/surfaces

- `neuropa/domain/models.py`
- `neuropa/domain/`
- `neuropa/providers/`
- `neuropa/memory/`
- `neuropa/cli.py`
- `PRODUCT.md`
- global OpenCode config/credentials
- LAN/auth behavior: `client_allowed_for_token`, cookie `samesite=lax`, CIDR `192.168.1.0/24`, auth dependencies
- runtime `:8474`
- FJSON Studio `:7865`

If Turn A truly requires a forbidden file, stop and report the dependency. Do not expand scope.

## Required implementation

### A1 — Primary desktop rail

- Add a desktop primary-rail toggle in the topbar.
- When hidden, computed shell grid must reclaim the full width; no empty first column.
- Provide an always-reachable restore button.
- Persist only the harmless UI preference.
- Preserve current tablet compact rail and mobile bottom navigation behavior.
- Keyboard and screen-reader labels must describe current action/state.

### A2 — Session rail

- Fix `Cambiar sesión`, close `×`, and keyboard behavior on desktop.
- When hidden, computed `.workspace-layout` first column must be `0px` and `.session-rail` must not intercept pointer/focus.
- When restored, it must be visible, usable, and preserve selected session.
- Do not regress tablet/mobile drawer behavior.

### A3 — Composer layout and adaptive popovers

Apply an Impeccable critique-first refinement:

- reduce vertical footprint and wasted spacing;
- anchor the composer to the bottom of the usable conversation stage instead of leaving it floating mid-canvas when the transcript is short;
- keep input dominant and controls compact;
- do not render provider/model/mode/context as four oversized equal-width cards; use a dense control row that still preserves 44px targets and legible selected values;
- keep every interactive target ≥44px without card inflation;
- make provider/model/mode/context menus viewport-aware;
- prefer opening above the composer;
- flip below only when the available space requires it;
- clamp menus inside viewport;
- close on Escape, outside click, selection, and view/session change;
- return focus to the trigger;
- prevent menus from being clipped by composer/container overflow;
- preserve reduced motion and visible focus.

Do not add a library, CDN, framework, or build step.

### A4 — Identity semantics

- Remove `Propuesta de IA` wherever it appears as the agent name.
- Use `NeuroPA` or `Asistente NeuroPA` as temporary primary identity.
- Mode remains separately labeled as `Modo: <name>`.
- Do not implement AgentProfile; that belongs to Turn B.

### A5 — Processing and measured metadata

- Add an immediate accessible `Procesando…` or `Pensando…` status while request fetch is active.
- Display elapsed waiting time without noisy animation.
- Preserve a clear waiting state at desktop/tablet/mobile.
- Normalize and persist server-side elapsed duration in assistant message metadata.
- Expose/render only measured fields available from `usage`: input, output, elapsed, and output tok/s when valid.
- Context window/remaining must display `No reportado` until a provider supplies trustworthy values.
- Never fabricate token/context values.
- Do not claim server cancellation unless it is actually propagated. If current `Detener` only aborts the client, label the behavior honestly or remove the misleading action.

### A6 — Session vs Artifact vocabulary and flow

- Session history is a conversation, not an artifact.
- Add an explicit user action to export/download the current session transcript without inserting an Artifact record.
- Keep explicit `Crear entregable Markdown` from a selected assistant response if the user chooses it.
- Keep the deliverable action attached to the specific assistant message; do not leave a global `Guardar artifact` action detached below the composer.
- Artifact UI copy must describe intentional deliverables, not generic saved conversations.
- Preserve artifact root sandbox, atomic write, checksum, source readback, UTF-8/size constraints, and missing-file honesty.
- A session transcript export must not change `/api/artifacts` count.

### A7 — Density polish

- Audit desktop 1600×1000 for unused space, excessive padding, and overlarge panels.
- Current evidence shows the two open rails reserve up to 534px before the main content; tighten their open widths/padding while preserving readable session titles and do not let navigation dominate the work surface.
- Keep the main transcript/composer column visually centered within the reclaimed space after either rail closes.
- Improve information density without dropping below 44px targets or creating visual noise.
- Preserve palette `#0f1117` + `#40E0D0`, single-file SPA, local-first copy, and ADHD-first progressive disclosure.

Impeccable baseline detector (run once by Hermes after the delegated detector failed at provider preflight) found three warnings:

1. `side-tab` — replace the thick cyan left-border status treatment with a subtler dot/badge or neutral emphasis;
2. `single-font` — strengthen hierarchy with the existing local/system font stack, weight, size, and spacing; do not add CDN fonts merely to silence the detector;
3. `dark-glow` — remove decorative cyan glow and use restrained border/elevation contrast.

These are manual design inputs, not permission for a visual rewrite.

## Mandatory tests

Write failing tests first for each contract. Static string assertions are not sufficient for interaction claims.

At minimum cover:

- rail state/class and browser-computed grid transitions;
- focus restoration and Escape behavior;
- popover preferred-above and fallback-below geometry;
- session selection preserved through rail toggle;
- agent identity vs mode label;
- processing live region present before delayed response resolves;
- elapsed/tok-s normalization with measured fixture usage;
- unknown context displays `No reportado`;
- session transcript download does not create an Artifact;
- explicit message-to-deliverable still creates one valid Artifact;
- existing artifact traversal/missing/non-UTF8 protections;
- no regression in LAN/auth tests.

## Verification commands

Use an ephemeral QA data directory and port; never restart or mutate `:8474`.

```bash
python3 -m compileall -q neuropa tests
uv run pytest -q --tb=short
git diff --check
```

Extract the SPA `<script>` to `/tmp` and run `node --check`.

## Browser gate

Use fresh browser contexts at:

- desktop `1600×1000`
- tablet `768×900`
- mobile `480×860`

Required journeys:

1. complete/skip onboarding;
2. desktop hide/show primary rail and verify reclaimed width;
3. desktop hide/show sessions and verify reclaimed width;
4. create/select sessions and confirm `Cambiar sesión` is functional;
5. open every composer menu and assert its bounding box stays in viewport and opens in the correct direction;
6. send a delayed fixture message and observe processing state before completion;
7. inspect measured response metadata and unknown-context fallback;
8. export session transcript and verify artifact count unchanged;
9. explicitly create a Markdown deliverable and verify artifact count + source/readback;
10. verify keyboard navigation, focus return, no horizontal overflow, no unexpected console/page/HTTP errors, and visible target sizes ≥44px.

A screenshot alone cannot pass any journey. Store screenshots only in `/tmp`.

## Required receipt

Write `docs/evidence/ux-audit-2026-08-04/codex-spark-turn-a-receipt.json` with:

- executor/model identity;
- start/end timestamps;
- baseline and final hashes for every touched source/test;
- exact files changed;
- exact tests added/changed;
- full command results and pass counts;
- browser matrix with assertions, not prose only;
- console/page/HTTP error counts;
- artifact/session count assertions;
- known residuals;
- forbidden-file hash comparison;
- verdict: `PASS_FOR_HERMES_REVIEW` or `FAIL`.

Do not write `READY_FOR_N30`; only Hermes may issue that after zero-trust review.

## Delegation failure disclosure

The independent assessment batch `deleg_ba65d2b2` produced no UX/architecture reports. All three workers stopped at provider preflight with HTTP 403 because `deepseek-v4-flash` requires an unapproved China-hosting opt-in. The scheduler's `status=completed` is a false completion; classify the batch as `INFRA_FAILURE` and exclude it from model/task scoring.

Hermes replaced the missing work directly with source/API/domain reads, live browser inspection, PA-prealpha/Understory comparison, and one Impeccable detector run. Do not cite the failed subagents as reviewers and do not enable regional opt-in.

## Stop conditions

Stop and report rather than improvise if:

- Turn A requires domain/provider/memory changes;
- a change touches global OpenCode or credentials;
- human runtime `:8474` would need restart/mutation;
- a UX behavior cannot be asserted in a real browser;
- tests reveal a dependency on Turn B or C;
- preserving current dirty worktree changes is impossible.

## Execution result

`PASS_FOR_HERMES_REVIEW` after zero-trust review. See `docs/evidence/ux-audit-2026-08-04/codex-spark-turn-a-receipt.json` for exact hashes, browser assertions, tests, residuals and forbidden-file comparison.
