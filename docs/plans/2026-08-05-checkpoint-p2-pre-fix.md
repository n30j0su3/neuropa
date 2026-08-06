# NeuroPA — Checkpoint 2026-08-05 P2-pre-fix

**Estado:** instantánea documentada antes de aplicar los 7 fixes solicitados por N30.  
**Branch:** `feat/p1-integrated`  
**HEAD:** `81c6929c39f318742fb2fc4fe9818b4f3e573e82`  
**Fecha:** 2026-08-05T10:41:18-05:00  
**Worktree:** sucio (21 archivos modificados, 15 sin trackear, 1265 inserciones, 138 borrados)

## Qué está funcional en este checkpoint

1. **Composer B móvil + Desktop** — auto-grow caps 132px/180px, textarea full-width, send 32px + área táctil 44px, chevron retractable, `prefers-reduced-motion`.
2. **Modos personalizables** — CRUD API (`/api/agent-modes`) + UI en Ajustes con crear/editar/activar/eliminar.
3. **Export de sesión** — HTML offline autocontenido, Markdown, JSON desde menú de sesión.
4. **Import JSON completo** — confirmación explícita, reemplazo gobernado.
5. **Capas permanentes** — `identity/SOUL.md` + `identity/AGENTS.md` con persistencia atómica `0o600`, endpoint `/api/identity` GET/PUT, UI en Ajustes con textareas.
6. **OpenRouter BYOK free-first** — catálogo con caché TTL 300s, prioridad `openrouter/free` → `:free` → explícitos.
7. **Distribución** — `Dockerfile` + `compose.yaml` + `scripts/install.ps1` + `scripts/run-neuropa.ps1` + `docs/SETUP.md` extendido.
8. **Tests** — 146 passed, compileall PASS, `git diff --check` PASS.
9. **Docker** — build exitoso, imagen `sha256:919ea4685d21…`, `/api/health` + `/api/identity` verificados en contenedor.
10. **Wiki** — `analyses/neuropa-owner-batch-2026-08-05.md` servida en `:9120`.

## Hashes de archivos clave

| Archivo | SHA-256 |
|---------|---------|
| `neuropa/frontend/index.html` | `51e0234d9f9fb49079efd828ff98b01071dc199a606f0176b4a560512a2164e1` |
| `neuropa/api/app.py` | `4205950b1bb5635036c3ac360771e31d3224b3c43928f54f62298ed349b1812c` |
| `neuropa/services/harness.py` | `d13b5967b3d38483c71af4b4956f258f43e918aa319fae1837fb0e9a2fc2fbf1` |
| `neuropa/providers/router.py` | `13bf67cb39132f93ddefc4c105c9fab8c9aee47b0fa0649f538da6d06093a168` |
| `Dockerfile` | `ab647f04c1a2b9ea64ed2f672c20763c069c150c37bbeca3c6a26ea5b68eb208` |
| `compose.yaml` | `8ede7ca903a6c6526d1607fdd177ed7d8ba2385208e1aa3fc278be87c59ee690` |
| `docs/SETUP.md` | `e57137076dfc66ec426387addf803096067c2aab0432be8e66b5bd3b5151df48` |

## Cómo revertir a este checkpoint

```bash
cd /home/freakingjson/Hermes-Stuff/projects/neuro-sass/neuropa
git stash list  # verificar que no hay stash previo conflictivo
git stash push -m "checkpoint-2026-08-05-p2-pre-fix" -- neuropa/frontend/index.html neuropa/api/app.py neuropa/services/harness.py neuropa/providers/router.py
# O para revertir TODO el worktree:
# git checkout -- .
# git clean -fd docs/evidence/ux-audit-2026-08-04/ docs/plans/ docs/handoffs/ Dockerfile compose.yaml scripts/
```

## Receipt de evidencia

`docs/evidence/ux-audit-2026-08-04/n30-owner-batch-receipt.json`  
SHA-256: `71fe801ef040afd3cd136286f488cabf8c3f9a4cf0345c84491e066a88c25432`

## Runtime activo

- NeuroPA LAN: `http://192.168.1.21:8474/` (proc_ba86bedff6d3, pid 3937576)
- Wiki-LLM: `http://127.0.0.1:9120/` (systemd wiki-llm.service)
