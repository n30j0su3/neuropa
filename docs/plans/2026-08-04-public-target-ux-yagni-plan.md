# NeuroPA Public-Target UX YAGNI Implementation Plan

> **Executor:** GLM-5.2 executes this plan block-by-block. Hermes performs the final zero-trust review before any commit or merge.

**Goal:** Make NeuroPA understandable and resumable for a non-technical ADHD/neurodivergent user without redesigning the product or expanding P1 scope.

**Architecture:** Preserve the single-file SPA and current Python service/domain boundaries. Two bounded cross-layer behaviors live in the existing `HarnessService`: deterministic first-message session titling through `Database.update`, and safe readback of an existing artifact file through one authenticated GET route. No new dependency, framework, storage entity, schema, or service.

**Tech stack:** Existing vanilla HTML/CSS/JS, native SVG, Python dataclasses/services, pytest, Playwright.

**Live-tree baseline:** branch `feat/p1-integrated`, HEAD `81c6929c39f318742fb2fc4fe9818b4f3e573e82`, with approved uncommitted work. Do not reset to HEAD.

---

## 1. Product diagnosis

NeuroPA already has a calm visual foundation, four-item navigation, 44 px mobile targets, session-first composer, no horizontal overflow, and real local data. The public-target gap is meaning, not decoration:

1. **Memory Graph is not actually rendered.** `renderMemoryGraph()` creates `svg`, `g`, `line`, `circle`, and `text` with the HTML factory (`document.createElement`). Ten `<circle>` tags exist, but zero are `SVGCircleElement`; the first node has rendered width `0 px`.
2. **Sessions cannot be recognized reliably.** Three of five visible sessions are named `Nueva sesión`, contradicting the promise of easy context resumption.
3. **Product language leaks implementation vocabulary.** Normal surfaces expose `Provider`, `Model`, `Context`, `Evidence inspector`, `Confidence`, `created_at`, `Status`, `Registry real`, `checksum`, `egress`, `LAN CIDR`, `BYOK`, and raw model IDs.
4. **Saved-result cards promise more than they deliver.** A card opens a panel that says `Sin preview disponible`, exposes a raw filesystem path, and has `content=false`, although the markdown file already exists under the controlled artifact root.
5. **Settings is an engineering diagnostics page.** It presents every provider/model/unavailable route before the three decisions a user needs: where IA runs, whether this session must stay local, and how to export data.

### Public-target success questions

The user must be able to answer, without technical knowledge:

- **Where do I continue?** A session has a recognizable title.
- **What does NeuroPA remember?** The graph is visible and a selected memory explains its origin in plain language.
- **Where is my text processed?** The current route is explained as `en este dispositivo` or `servicio online`; technical details are secondary.
- **What did I save?** Saved-result cards have readable titles, date/source, and honest detail states.

---

## 2. Layer separation map

| User promise | Existing layer | Minimal change | Explicitly not added |
|---|---|---|---|
| Recognize a session | `HarnessService.send_message` → `Database.update` | Derive title once from first user message | Rename endpoint, LLM summarizer, title-edit UI |
| See memory relationships | Frontend `renderMemoryGraph` | Native `createElementNS` SVG factory | D3, canvas engine, force simulation |
| Understand privacy and IA | Frontend copy/progressive disclosure | Plain-language labels and collapsed technical details | Provider redesign, credential management |
| Retrieve a saved result | Existing artifact file + list/canvas | One authenticated safe-content GET + human card/detail | Download manager, editor, conversion pipeline |

Codebase-memory evidence: NeuroPA is a small Python + one-HTML project (398 indexed nodes). `services → domain` is the strongest real boundary (23 calls); `Database.update` is an existing hotspot used by 10 callers. The session-title change belongs in the existing service boundary, not in a new API.

---

## 3. Block plan

### G0 — Live-tree custody and RED evidence (~15 min)

**Objective:** Prove the executor is modifying the audited live baseline and cannot erase approved uncommitted work.

**Files:** no repository writes.

1. Record `git status --short`, branch, HEAD, and SHA-256 for the seven baseline-guarded files into `/tmp/neuropa-glm52-b0.json`.
2. Verify these audited baseline hashes before editing:
   - `neuropa/frontend/index.html`: `6144f08546dc1f0958b1a10e7cd93eec180557981872c057388cad4872d98eae`
   - `neuropa/services/harness.py`: `5d144cd3ccc1cbde4f9375a9767a7fd1eedf01e2afe93c80fecbb684207f7ac9`
   - `tests/test_frontend_ux_gaps.py`: `a70d5b16dd26b8f6578a4a72dcf7beb14ad177f709ad6b7173dd9359f6df60ca`
   - `tests/test_memory_graph_frontend.py`: `46895445f123787001fa041a77a25dd7776d794902362c70b13c23be6128c260`
   - `tests/test_harness_p0.py`: `617582f5891634824a7ce03e402e02b23e9c90f9738801b2a51c4ba3f156a31c`
   - `neuropa/api/app.py`: `89eb9b1b12b949354190cc9f8123f05833488242504c7f152b10e429cb70a868`
   - `tests/test_frontend_harness_contract.py`: `ce0f4a70947a0596e93721c12d48d5afb8b50f418fa528eade8972fbe851c7b2`
3. Run existing suite before edits: `uv run pytest -q --tb=short`. Expected audited baseline: `73 passed`.
4. Add failing tests before implementation; preserve their real non-zero RED exit code.

**Stop:** Any baseline hash mismatch or unexpected file change → report `BASELINE_DRIFT`; do not reset or continue.

### G1 — Render a real, legible native SVG Memory Graph (~90 min)

**Objective:** Make the already-backed graph perceptually visible and selectable at 1600/768/480.

**Files:**
- Modify: `neuropa/frontend/index.html` — `renderMemoryGraph`, graph helpers, Memory copy/styles.
- Modify tests: `tests/test_memory_graph_frontend.py`.

**RED tests:**

1. Assert graph construction uses `document.createElementNS('http://www.w3.org/2000/svg', tag)` for `svg`, `g`, `line`, `circle`, and `text`.
2. Browser assertion: first node is an `SVGCircleElement`, `getBBox()` exists, and `getBoundingClientRect().width > 8` at 1600, 768, and 480.
3. Interaction assertion: clicking/tapping one visible node populates the inspector with claim text and origin.
4. Mobile assertion: `Grafo` and `Origen` are visible 44 px tabs; only one surface is shown at a time.

**Minimal implementation:**

- Add one local SVG helper using `document.createElementNS`; keep the existing HTML `make()` helper unchanged.
- Append SVG to the live DOM before applying camera transform.
- Preserve native pan/zoom/reset and real API data.
- Replace full claim labels on canvas with short, bounded labels; keep full claim text in the inspector and accessible label.
- Rename visible graph terms: `Wiki / Memory` → `Memoria conectada`, `Evidence inspector` → `De dónde viene`, `Source` → `Origen`, `Status` → `Estado`, `Confidence` → `Confianza`, `Reset view` → `Centrar grafo`.
- Do not add a physics engine, minimap, clustering, auto-relations, animation, legend system, or new filters.

**Implementation shape (use this exact namespace; adapt attributes through `setAttribute`):**

```javascript
const SVG_NS = 'http://www.w3.org/2000/svg';
function makeSvg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === 'text') node.textContent = String(value);
    else node.setAttribute(key, String(value));
  });
  return node;
}
```

Use `makeSvg` only for SVG descendants. Continue using existing `make()` for HTML. Append `svg` to `root` before `applyGraphTransform()` so the viewport can be resolved from the live document.

**GREEN:** Focused tests pass; screenshot must visibly show nodes and edges, not just tag counts.

### G2 — Make sessions recognizable without adding session management (~60 min)

**Objective:** Let a returning user identify where to resume.

**Files:**
- Modify: `neuropa/services/harness.py` — `send_message` or one adjacent private helper.
- Modify: `neuropa/frontend/index.html` — refresh current/list title after first successful message.
- Modify tests: `tests/test_harness_p0.py`, `tests/test_frontend_ux_gaps.py`.

**RED tests:**

1. A session titled `Nueva sesión` receiving its first user message gets a deterministic title derived locally from that message.
2. Title normalization collapses whitespace, stays within 60 characters, and does not split the final word when a word boundary exists.
3. Existing custom titles never change.
4. Second and later messages never retitle the session.
5. Frontend refreshes session list/current title after the first successful response.

**Minimal implementation:**

- Use a small pure helper: normalize whitespace, strip surrounding punctuation, choose a maximum 60-character word-boundary prefix, fallback to `Nueva sesión` for blank text.
- Call existing `Database.update` once only when the current title is blank/default and no prior user message exists.
- No LLM title generation, rename modal, PATCH endpoint, title history, tags, folders, favorites, or new entity fields.

**Implementation shape (private pure helper, no dependency):**

```python
def _title_from_first_message(text: str, limit: int = 60) -> str:
    normalized = " ".join(text.split()).strip(" .,:;!?-_\t\r\n")
    if not normalized:
        return "Nueva sesión"
    if len(normalized) <= limit:
        return normalized
    prefix = normalized[: limit + 1]
    bounded = prefix.rsplit(" ", 1)[0].strip()
    return bounded or normalized[:limit].strip()
```

Before persisting, determine whether the session has any prior `role == "user"` message. Update only when there is none and the title is blank or exactly `Nueva sesión`.

**GREEN:** Five sessions seeded with distinct first messages produce recognizable deterministic titles; custom titles remain byte-identical.

### G3 — Distill onboarding and Settings into human decisions (~90 min)

**Objective:** Remove implementation translation work while preserving provider/model control and honest privacy behavior.

**Files:**
- Modify: `neuropa/frontend/index.html` only.
- Modify tests: `tests/test_frontend_ux_gaps.py`, `tests/test_workspace_control_dock.py` only if existing contract assertions require wording updates.

**Changes:**

1. Onboarding path cards lead with outcomes:
   - `Usar IA gratuita` — `Recomendado para empezar; usa un servicio online y puede tener límites.`
   - `Mantener todo en este dispositivo` — `Disponible cuando un modelo de conversación local esté listo.`
   - Unavailable routes are disabled and visually secondary; `Seguir sin IA` remains visible.
   - Provider names/model IDs move to a secondary technical line, not the heading.
2. Settings first fold contains only:
   - `Dónde trabaja tu IA` with current route and plain-language status.
   - `Mantener esta sesión en este dispositivo` toggle.
   - `Exportar mis datos` action.
3. Provider health, full model IDs, BYOK, managed provider, egress details, and LAN CIDR move under one closed `Detalles técnicos` disclosure.
4. Hide the `Ctrl/Cmd+K` shortcut badge on touch/mobile; do not remove keyboard support on desktop.
5. Preserve separate provider/model controls inside IA configuration. Do not silently change the selected provider or model.
6. Preserve `#0f1117`, `#40E0D0`, existing spacing system, 44 px targets, reduced motion, and focus-visible behavior.

**Forbidden:** new onboarding steps, illustrations, mascot, gamification, mood tracking, themes, settings routes, feature tours, notifications, or rewritten design system.

### G4 — Make saved results honest and actually retrievable (~75 min)

**Objective:** Replace developer registry language with readable cards and load the content file NeuroPA already created.

**Files:**
- Modify: `neuropa/services/harness.py` — add one safe artifact read method.
- Modify: `neuropa/api/app.py:304-311` — add one authenticated `GET /api/artifacts/{artifact_id}` adjacent to existing artifact routes; no other app.py hunk.
- Modify: `neuropa/frontend/index.html` — card/detail fetch and human copy.
- Modify tests: `tests/test_harness_p0.py`, `tests/test_frontend_harness_contract.py`, `tests/test_frontend_ux_gaps.py`.

**Changes:**

- Nav/surface label: `Artifacts` → `Guardados`; internal route ID remains `artifacts`.
- Card title: humanize the existing artifact title locally (hyphens/underscores → spaces, sentence case, bounded to two lines); never fabricate content.
- Primary metadata: save date + source session when present.
- Move checksum and raw path into closed `Detalles técnicos` inside the opened panel.
- `HarnessService.read_artifact(artifact_id)` resolves the stored relative path under `(data_dir / 'artifacts').resolve()`, rejects traversal/non-file/non-markdown/oversize (>2 MiB), reads UTF-8, and returns the existing artifact dict plus `content`.
- The GET route stays behind existing `require_auth`; `KeyError` → 404 and invalid/unsafe path → 400. Do not alter auth, cookies, pairing, CIDR, or exception middleware.
- On card open, fetch that artifact ID and render markdown as escaped plain text in the existing preview. No Markdown library and no `innerHTML` for file content.
- If the file is absent, say `No encontramos el archivo guardado. Su origen y checksum siguen disponibles en Detalles técnicos.`
- Change `Registry real` → `Resultados guardados`; remove `Nada decorativo` and `Sin checksum publicado` from the normal card.

**RED tests:** successful readback returns exact content; traversal path is rejected; missing file is explicit; unauthenticated GET is denied; frontend escapes `<script>` artifact content and never inserts it with `innerHTML`.

**Deferred by YAGNI:** download/archive/edit/version UI, Markdown renderer, conversion pipeline, search, tags, folders, or external opening.

### G5 — Public-use QA and bounded closure (~45 min)

**Objective:** Prove the four public questions can be answered in real use.

1. `node --check` on extracted inline JavaScript.
2. `uv run pytest -q --tb=short` — all baseline + new tests pass.
3. `git diff --check` — PASS.
4. Browser at 1600×1000, 768×900, 480×860:
   - onboarding completes through normal visible controls;
   - first message creates a recognizable title and survives reload;
   - graph visibly renders SVG nodes/edges, and a node opens plain-language origin;
   - Settings exposes only the three primary decisions before technical details;
   - Guardados card loads the exact existing markdown as escaped text and handles a missing file explicitly;
   - all visible controls ≥44 px; no global horizontal overflow;
   - zero console errors, page errors, or HTTP ≥400.
5. Save screenshots outside tracked baseline during GLM execution (`/tmp/neuropa-glm52-qa/`). Hermes decides what evidence enters the repo.
6. Final executor status must be exactly: `IMPLEMENTATION_COMPLETE_PENDING_HERMES_ZERO_TRUST_REVIEW`.

---

## 4. Allowed and protected surfaces

### Allowed files only

- `neuropa/frontend/index.html`
- `neuropa/services/harness.py`
- `tests/test_frontend_ux_gaps.py`
- `tests/test_memory_graph_frontend.py`
- `tests/test_harness_p0.py`
- `tests/test_frontend_harness_contract.py`
- `neuropa/api/app.py` only for the exact authenticated artifact GET adjacent to lines 304-311
- `tests/test_workspace_control_dock.py` only if a wording assertion fails after G3; behavior assertions must not be weakened.

### Protected — do not modify

- `neuropa/api/app.py` outside the exact adjacent artifact-route hunk — contains the approved LAN/token remediation.
- `neuropa/cli.py`, `neuropa/providers/`, `neuropa/domain/`, `neuropa/memory/`.
- `PRODUCT.md`, existing evidence, prior screenshots, QA JSON, and all files outside the allowlist.
- Do not change auth, pairing, cookies, CIDR, provider routing, model availability, context payloads, memory API, artifact creation, or persistence schema. The only artifact API change is the one read-only GET defined in G4.

### Forbidden operations

- `git reset`, `git restore`, `git checkout --`, `git clean`, rebase, merge, or commit.
- Whole-file rewrite of `index.html`.
- Broad regex replacement without exact surrounding context and readback.
- New framework, dependency, CDN, build step, SVG library, router, API endpoint beyond the exact G4 GET, database field, or abstraction.
- Removing tests, weakening assertions, replacing behavioral checks with static string counts, or declaring success from DOM tag counts alone.

---

## 5. Acceptance criteria

- [ ] Real `SVGCircleElement` nodes have non-zero rendered geometry at all three viewports.
- [ ] Node selection explains claim and origin in plain Spanish in ≤3 interactions.
- [ ] Default sessions receive deterministic first-message titles; custom titles never change.
- [ ] A non-technical user sees no provider/model list, egress, checksum, path, LAN CIDR, BYOK, or managed provider before opening `Detalles técnicos`.
- [ ] Provider and model remain separately controllable; no silent provider/model change.
- [ ] Saved-result cards are readable; opening one retrieves existing markdown safely, renders it escaped, and keeps path/checksum secondary.
- [ ] Existing mobile bottom navigation, session-first composer, LAN access, auth, privacy guard, memory provenance, 44 px targets, focus-visible, and reduced-motion behavior remain intact.
- [ ] Full suite and real browser matrix pass.

## 6. Skipped / deferred by YAGNI

- Artifact download/archive/edit/version UI and Markdown rendering pipeline.
- Manual session rename UI.
- Memory graph physics/clustering/minimap/search redesign.
- New user profile, preference store, themes, reminders, notifications, dashboards, analytics, or onboarding tour.
- Visual rebrand, new typography, illustration system, or FJSON Studio clone.

The plan adds no dependency, one deterministic title behavior, and one bounded safe-read route over a file NeuroPA already created. Everything else is deletion, relabeling, progressive disclosure, or correction of the existing native SVG implementation.
