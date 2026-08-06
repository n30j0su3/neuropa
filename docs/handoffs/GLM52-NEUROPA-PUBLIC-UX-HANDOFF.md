# GLM-5.2 Handoff — NeuroPA Public-Target UX YAGNI Pass

## Authority

You are the implementation executor. The canonical plan is:

`docs/plans/2026-08-04-public-target-ux-yagni-plan.md`

Integrity manifest: `docs/handoffs/GLM52-NEUROPA-PUBLIC-UX-SHA256SUMS.txt`

Read it completely before using any write tool. The live tree contains approved uncommitted work. **You do not have authority to reset, restore, clean, rebase, merge, commit, rewrite the frontend wholesale, modify production/LAN auth, or expand scope.**

Your maximum final verdict is:

`IMPLEMENTATION_COMPLETE_PENDING_HERMES_ZERO_TRUST_REVIEW`

## First command block — mandatory custody gate

Run from `/home/freakingjson/Hermes-Stuff/projects/neuro-sass/neuropa`:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
sha256sum \
  neuropa/frontend/index.html \
  neuropa/services/harness.py \
  tests/test_frontend_ux_gaps.py \
  tests/test_memory_graph_frontend.py \
  tests/test_harness_p0.py \
  neuropa/api/app.py \
  tests/test_frontend_harness_contract.py
uv run pytest -q --tb=short
```

Required identity:

- Branch: `feat/p1-integrated`
- HEAD: `81c6929c39f318742fb2fc4fe9818b4f3e573e82`
- Existing dirty tree is expected; do not “clean” it.
- Baseline suite: `73 passed`.

Required hashes:

```text
6144f08546dc1f0958b1a10e7cd93eec180557981872c057388cad4872d98eae  neuropa/frontend/index.html
5d144cd3ccc1cbde4f9375a9767a7fd1eedf01e2afe93c80fecbb684207f7ac9  neuropa/services/harness.py
a70d5b16dd26b8f6578a4a72dcf7beb14ad177f709ad6b7173dd9359f6df60ca  tests/test_frontend_ux_gaps.py
46895445f123787001fa041a77a25dd7776d794902362c70b13c23be6128c260  tests/test_memory_graph_frontend.py
617582f5891634824a7ce03e402e02b23e9c90f9738801b2a51c4ba3f156a31c  tests/test_harness_p0.py
89eb9b1b12b949354190cc9f8123f05833488242504c7f152b10e429cb70a868  neuropa/api/app.py
ce0f4a70947a0596e93721c12d48d5afb8b50f418fa528eade8972fbe851c7b2  tests/test_frontend_harness_contract.py
```

If any identity/hash differs, stop and report `BASELINE_DRIFT` with the exact mismatch. Do not fix it.

## Root-cause facts — do not re-diagnose away

1. `neuropa/frontend/index.html:renderMemoryGraph` builds SVG tags through the HTML `make()` helper (`document.createElement`). They are not SVG elements. Browser proof: 10 `<circle>` tags, 0 `SVGCircleElement`, first rendered node width `0 px`, and `getBBox()` is not a function.
2. Five visible sessions currently include three `Nueva sesión` titles. `ChatSession.title` already persists; `Database.update` already exists. Use deterministic local first-message titling, not an LLM or new endpoint.
3. An artifact card opens `Sin preview disponible` and a raw filesystem path while the markdown file already exists under the controlled artifact root. Add exactly one authenticated safe-content GET through `HarnessService`; no download/editor/conversion scope.
4. Settings exposes provider/model infrastructure, unavailable provider cards, egress, LAN CIDR, and raw model IDs before the user’s actual privacy/data decisions.
5. Existing strengths must survive: single-file SPA, `#0f1117` + `#40E0D0`, four-item nav, session-first composer, mobile progressive IA controls, 44 px targets, focus-visible, reduced motion, no global overflow, real API data.

## Execution order

Execute exactly these blocks from the canonical plan:

1. **G1:** Real native SVG Memory Graph.
2. **G2:** Deterministic session titles.
3. **G3:** Plain-language onboarding/Settings and technical-details disclosure.
4. **G4:** Safe artifact readback + honest `Guardados` cards/details.
5. **G5:** Full tests + browser matrix.

For each block:

1. Read the exact current symbol and adjacent CSS/tests.
2. Add a behavioral RED test.
3. Run that exact test and preserve non-zero exit.
4. Apply the smallest patch; never rewrite the whole file.
5. Run focused GREEN tests.
6. Run `git diff --check`.
7. Verify `git diff --name-only` stays within the allowlist.
8. Continue only if green.

## Allowlist

```text
neuropa/frontend/index.html
neuropa/services/harness.py
tests/test_frontend_ux_gaps.py
tests/test_memory_graph_frontend.py
tests/test_harness_p0.py
tests/test_frontend_harness_contract.py
neuropa/api/app.py  # exact adjacent artifact GET hunk only
tests/test_workspace_control_dock.py  # wording-only compatibility if required
```

Everything else is protected. In particular, never modify:

```text
neuropa/api/app.py outside the exact adjacent artifact GET hunk
neuropa/cli.py
neuropa/providers/
neuropa/domain/
neuropa/memory/
PRODUCT.md
docs/evidence/
```

## Non-negotiable YAGNI bans

- No React/Vite/D3/canvas/graph library/CDN/dependency/build step.
- No new route/API except the single authenticated artifact GET defined in G4; no entity, DB field, settings store, abstraction, design system, illustration, theme, dashboard, notification, tag/folder/favorite feature, rename modal, AI title generator, download/editor/conversion pipeline, or visual rebrand.
- No restored `Executive Function`, Projects, Research, Skills, or Calendar navigation.
- No `innerHTML` for untrusted content.
- No static tag-count test presented as visual proof.
- No modifications to tests that weaken existing behavior.

## Browser proof required

Use a separate QA port if a restart is needed; do not kill or replace the human QA runtime on `:8474`.

At 1600×1000, 768×900, and 480×860, prove:

- first-run onboarding completes normally;
- first message changes only a default session title and it survives reload;
- Memory contains real `SVGCircleElement` nodes with rendered width >8 px;
- a node click/tap opens plain-language origin;
- Settings first fold shows IA location, local-only control, and export before technical details;
- Guardados cards retrieve the existing markdown safely, render it as escaped text, and expose an explicit missing-file state;
- all visible controls ≥44 px;
- no global horizontal overflow;
- zero console/page errors and HTTP ≥400.

Write temporary screenshots only to `/tmp/neuropa-glm52-qa/`. Do not overwrite existing evidence.

## Final response contract

Return:

1. One-line verdict: `IMPLEMENTATION_COMPLETE_PENDING_HERMES_ZERO_TRUST_REVIEW` or a precise blocker.
2. Files changed.
3. RED and GREEN commands with real exit codes.
4. Full-suite count.
5. Browser results for all three viewports.
6. `git diff --check` result.
7. Any deliberate deferral from the plan.
8. Explicit confirmation that no protected file was modified and no commit was created.

---

## Hermes zero-trust closure — 2026-08-04

**Final verdict:** `PASS_AFTER_HERMES_REMEDIATION — READY_FOR_N30_HUMAN_HANDOFF`

GLM-5.2's self-report was not accepted as completion evidence. Hermes reviewed the full live diff, reran B0 tests against the modified source, added negative/security coverage, and executed the required browser journeys at all three viewports.

### Findings Hermes fixed after GLM

1. **BLOCKER — Memory node activation:** SVG pointer capture cancelled node click/tap, so `Origen` never opened. Pan now ignores `.graph-node` targets.
2. **HIGH — Memory public language:** technical labels and unbounded canvas labels remained. Visible text is now human-facing and bounded; full text remains accessible and in the inspector.
3. **HIGH — Session title refresh:** the frontend read stale `state.sessions` before refresh. It now awaits the live session list and verifies title persistence after reload.
4. **HIGH — Settings/onboarding:** provider names/model IDs remained in the first fold. Routes are now outcome-first; provider/model/LAN details stay inside closed `Detalles técnicos`.
5. **HIGH — Guardados:** checksum/source metadata and traversal/missing/non-UTF8/auth/XSS coverage were incomplete. Safe readback and honest missing-file behavior are now tested.
6. **MEDIUM — touch target:** `Cambiar sesión` measured 40px. It is now 44px.
7. **BLOCKER — tablet/mobile new-session flow:** creating a session left the drawer over the composer. New sessions now close the drawer and focus the composer.

### Final gates

- `python3 -m compileall -q neuropa tests`: **PASS**
- `node --check /tmp/neuropa-hermes-review.js`: **PASS**
- `uv run pytest -q --tb=short`: **88 passed, 0 failed**
- `git diff --check`: **PASS**
- Browser onboarding: **PASS**
- Browser journeys — Settings, SVG node→Origen, Guardados exact/XSS/missing, session title immediate+reload: **PASS 3/3 viewports**
- Viewports: **1600×1000, 768×900, 480×860**
- Overflow: **0/3**
- Visible targets below 44px: **0/3**
- Unexpected console/page errors: **0/3**
- Expected negative case: missing artifact returns **HTTP 400** and the UI renders the explicit recovery state. This deliberate non-2xx is isolated from the zero-unexpected-error gate.

### Custody

- `neuropa/api/app.py` reconstructed without the exact G4 GET hunk hashes to the sealed B0 value `89eb9b1b12b949354190cc9f8123f05833488242504c7f152b10e429cb70a868`; LAN/auth remained byte-identical outside G4.
- Human runtime `:8474`: **not touched**.
- QA runtime `:8586`: temporary only.
- Commit created: **no**.
- Screenshots: `/tmp/neuropa-zero-trust-{desktop,tablet,mobile}.png` only.
- Machine-readable receipt: `docs/evidence/ux-audit-2026-08-04/hermes-zero-trust-review.json`.
