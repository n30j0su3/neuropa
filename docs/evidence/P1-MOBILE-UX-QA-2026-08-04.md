# NeuroPA P1 — Mobile UX Recovery QA

**Date:** 2026-08-04  
**Scope:** Recovery from the reverted GLM UI regression; controlled P1 interaction pass.

## Decisions

- Chat is session-first: the composer cannot silently create a chat session. With no active session it is disabled and directs the user to create/open one.
- Mobile AI settings use progressive disclosure: the compact `IA · provider · model` trigger expands the Control Dock only on demand.
- Navigation is YAGNI-scoped to four working P1 surfaces: Workspace, Memoria, Artifacts, Ajustes.
- Memory Graph remains native SVG and auto-fetches its real API data; the empty state tells the user how to create the first connection.
- Artifacts use provenance cards, not a decorative gallery: title, type, date, checksum prefix, and open-preview affordance.

## Automated gates

- JavaScript extracted from `neuropa/frontend/index.html`: `node --check` PASS.
- Full test suite: **73 passed**.
- `git diff --check`: PASS.

## Browser interaction QA

Fresh local-first onboarding was completed through the visible wizard before test interactions.

| Viewport | Graph | Artifacts | Mobile controls | Errors / overflow |
|---|---|---|---|---|
| 1600 × 1000 | Visible, 10 SVG nodes | Visible, 3 cards | n/a | None |
| 768 × 900 | Visible, 10 SVG nodes | Visible, 3 cards | n/a | None |
| 480 × 860 | Visible, 10 SVG nodes | Visible, 3 cards | `none → grid` on trigger | None |

No browser console errors, page errors, HTTP >=400 responses, or horizontal overflow were observed.

## LAN QA

Runtime is bound to `0.0.0.0:8474` for trusted LAN QA:

`http://192.168.1.21:8474`
