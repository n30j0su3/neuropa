# NeuroPA Mobile Composer B Implementation Plan

> **For Hermes:** Execute this plan in-place on the existing `feat/p1-integrated` worktree; do not reset, restore, commit, or overwrite unrelated dirty changes.

**Goal:** Implement the N30-approved two-state adaptive composer across mobile, tablet, and desktop with a dominant auto-growing textarea, subtle send action, flat expandable configuration, a sliders icon, and an overlap-safe floating retract control.

**Architecture:** Preserve the indexed single-file frontend boundary (`neuropa/frontend/index.html`; codebase_memory: 3 scoped nodes, HTML-only). Add only DOM/CSS state inside the existing `composer()` factory and one Boolean in the existing `state` object. No framework, dependency, new runtime module, or persistence layer.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, existing `make`/`makeSvg` helpers, pytest static contract tests, Playwright/browser runtime QA.

---

## Existing boundary evidence

| Layer | Current owner | Planned change |
|---|---|---|
| UI state | `state` in `neuropa/frontend/index.html` | Add `composerRetracted:false` only |
| DOM | `composer()` | Recompose existing controls into toggle, flat config, input row, status footer |
| Styling | Existing inline `<style>` | Append scoped `.composer-*` rules and mobile overrides |
| Regression contracts | `tests/test_handoff_fixes.py` | Add smallest structural contract tests |
| Runtime QA | Live NeuroPA on `:8474` | Exercise both states and multiline input at 480/768/1600 |

## Task 1: Lock the approved DOM and behavior contract

**Objective:** Add tests that fail until the approved adaptive composer structure exists.

**Files:**
- Modify: `tests/test_handoff_fixes.py`
- Test: `tests/test_handoff_fixes.py`

**Step 1 — RED:** Add tests asserting these exact production markers:

```python
def test_b3_mobile_composer_uses_approved_two_state_contract():
    assert "composerRetracted:false" in HTML
    assert "class:`composer${state.composerRetracted?' retracted':''}`" in HTML
    assert "class:'composer-collapse'" in HTML
    assert "class:'composer-row'" in HTML
    assert "class:'composer-input-shell'" in HTML
    assert "class:'dock-settings-icon'" in HTML
    assert "class:'send-btn'" in HTML and "aria-label':'Enviar mensaje'" in HTML


def test_b3_composer_autogrows_and_caps_mobile_height():
    assert "function resizeComposerInput(input)" in HTML
    assert "input.style.height='44px'" in HTML
    assert "window.matchMedia('(max-width: 700px)').matches?132:180" in HTML
    assert "input.scrollHeight>cap?'auto':'hidden'" in HTML


def test_b3_desktop_uses_same_two_state_composer_contract():
    shared = HTML.split("/* N30-approved Composer B", 1)[1].split("@media(max-width:700px)", 1)[0]
    assert ".composer-collapse{position:absolute" in shared
    assert ".composer-collapse{display:none}" not in shared
    assert ".dock-toggle{display:flex" in shared
    assert ".control-dock{display:none" in shared
    assert ".control-dock.expanded{display:grid" in shared
```

**Step 2:** Run:

```bash
uv run pytest -q tests/test_handoff_fixes.py -k b3 --tb=short
```

Expected: FAIL because the approved markers are not implemented.

**Step 3:** Do not alter the tests after observing the expected failure.

## Task 2: Implement the minimal composer behavior

**Objective:** Make Task 1 green while preserving send, stop, provider/model/mode/context, and Enter/Shift+Enter behavior.

**Files:**
- Modify: `neuropa/frontend/index.html`
- Test: `tests/test_handoff_fixes.py`

**Step 1:** Add `composerRetracted:false` to the existing `state` object.

**Step 2:** Add the single helper:

```js
function resizeComposerInput(input){
  const cap=window.matchMedia('(max-width: 700px)').matches?132:180;
  input.style.height='44px';
  input.style.height=Math.min(input.scrollHeight,cap)+'px';
  input.style.overflowY=input.scrollHeight>cap?'auto':'hidden';
}
```

**Step 3:** Refactor only `composer()` so that:

- `composer-collapse` toggles `state.composerRetracted` and `.retracted` without rerendering.
- The control summary remains tap-expandable and receives a native `makeSvg` sliders icon.
- `composer-row` contains `composer-input-shell` plus the send/stop action.
- The send action has a 44 px hit target, arrow icon, accessible label, and `ready` class only for non-empty content.
- The existing four `control(...)` calls remain unchanged.
- `Enter` sends and `Shift+Enter` inserts a newline.
- Input events call `resizeComposerInput(input)`.

**Step 4:** Append scoped CSS rather than rewriting unrelated existing CSS:

- `.composer-collapse`: absolute, `top:-40px`, right aligned, transparent, borderless.
- `.composer-row`: input-first two-column grid.
- `.composer-input-shell`: dominant neutral input surface.
- `.send-btn`: 44 px hit target with a visually smaller 32 px pseudo-element.
- `.composer.retracted`: hides `.dock-toggle`, `.control-dock`, `.composer-footer`; keeps input and action.
- Mobile `.dock-toggle`: flat, borderless except one divider; no nested card styling.
- `prefers-reduced-motion` remains authoritative.

**Step 5 — GREEN:** Run:

```bash
uv run pytest -q tests/test_handoff_fixes.py -k b3 --tb=short
```

Expected: 3 passed.

## Task 3: Preserve existing frontend and backend contracts

**Objective:** Prove the focused refactor did not break unrelated behavior.

**Files:** No additional production files.

**Step 1:** Extract the inline script to `/tmp/neuropa-inline.js` and run:

```bash
node --check /tmp/neuropa-inline.js
```

Expected: exit 0.

**Step 2:** Run focused frontend tests:

```bash
uv run pytest -q tests/test_handoff_fixes.py tests/test_frontend_ux_gaps.py tests/test_frontend_harness_contract.py --tb=short
```

Expected: all pass.

**Step 3:** Run full gates:

```bash
python3 -m compileall -q neuropa tests
uv run pytest -q --tb=short
git diff --check
```

Expected: all pass.

## Task 4: Runtime and visual QA

**Objective:** Verify semantic effectiveness—not merely class changes—at all required viewports.

**Files:**
- Create/update evidence only under `docs/evidence/ux-audit-2026-08-04/` if needed.

**Step 1:** Restart only the authorized NeuroPA runtime on `:8474`; do not touch Studio `:7865`.

**Step 2:** At 480 px verify:

1. Compact state shows configuration summary, textarea and send.
2. Sliders icon opens/closes the flat provider/model/mode/context list.
3. Textarea grows from 44 px through at least four lines, then caps at 132 px.
4. Send remains bottom-aligned and visually secondary.
5. Retracted state hides configuration and status but retains textarea/send.
6. Floating chevron is outside the composer, transparent, borderless, and overlap-free with empty and multiline text.
7. Enter/Shift+Enter and a real send still work.

**Step 3:** At 768 px and 1600 px verify the same two-state contract, a 180 px textarea cap, flat two-column configuration grid, visible sliders icon, and overlap-free floating chevron. Repeat geometry, overflow, keyboard, and console checks.

**Step 4:** Verify `prefers-reduced-motion` and zero console errors.

## Skipped / Deferred (YAGNI)

- No third global composer state.
- No bottom sheet.
- No new component framework or dependency.
- No persistence of the retract state across reloads.
- No redesign of provider popovers beyond the approved adaptive composer scope.
- No commit while the existing worktree contains unrelated changes.

**Estimated effort:** ~45–75 minutes including three-viewport runtime QA.
