# NeuroPA — Product Contract

## Qué es

NeuroPA es un AI Workspace local-first para personas neurodivergentes y perfiles con TDAH. Reduce fricción al capturar, pensar, decidir y volver a una sesión sin convertir la organización en otra obligación.

## Usuario principal

Una persona que necesita descargar pensamiento, recuperar contexto y avanzar con ayuda de IA sin perder control sobre datos, provider, modelo ni memoria.

## Job to be done

> Cuando mi atención está fragmentada o necesito retomar algo, quiero abrir un workspace tranquilo que recuerde lo necesario, me muestre de dónde viene ese contexto y me permita elegir cómo y con qué IA trabajar.

## Principios del producto

1. **Local-first real:** la copia primaria vive en el dispositivo.
2. **Honestidad funcional:** ningún control puede aparentar una capacidad que el backend no ejecuta.
3. **Una cosa empezable:** priorizar el siguiente paso sobre dashboards de deuda.
4. **Memoria con provenance:** hechos, inferencias y fuentes no se mezclan.
5. **Control de egress:** provider, modelo y contexto son decisiones visibles del usuario.
6. **No lock-in:** exportación y uso local siguen siendo completos.
7. **Accesibilidad ADHD-first:** jerarquía clara, reducción de ruido, keyboard-first y targets mínimos de 44 px.

## Promesa P0 ya cumplida

- Workspace con sesiones persistentes.
- OpenCode gratuito y provider local.
- Modos cognitivos.
- Captura, Today, Focus, Memory y Artifacts.
- Pairing LAN one-time y seguridad local-first.

## Slice aprobado P1.1–P1.2

### Workspace Control Dock

Provider, modelo, modo y contexto son controles separados, persistentes, accesibles y funcionales. Modelos se filtran por provider y el cambio nunca ocurre silenciosamente.

### Memory Graph

La memoria se puede explorar, filtrar e inspeccionar como grafo. Cada claim conserva fuente, confidence, estado y cadena de supersession. El usuario puede seleccionar claims como contexto y corregir memoria creando una nueva versión confirmada; no existe edición destructiva libre.

## Alcance de contexto inicial

- `none`: sólo el mensaje actual y el system prompt del modo.
- `session`: historial reciente de la sesión.
- `session_memory`: historial reciente + claims explícitamente seleccionados.

Projects, research corpus y artifacts sólo entrarán cuando tengan SourceRef y contratos reales.

## Qué NO es este slice

- No es un fork ni embed completo de Understory.
- No añade React, Vite, D3, vector DB ni otro servidor.
- No infiere relaciones semánticas automáticamente.
- No expone chain-of-thought.
- No ejecuta tools arbitrarias.
- No convierte memoria en un editor libre propenso a pérdida de provenance.

## Referencia externa auditada

Understory (`thecodacus/understory`) commit `dd93484ebb00afaf17b036b4db121cb61775eb63`, Apache-2.0. Se adaptan patrones de interacción: force graph, pan/zoom/drag, neighbor highlighting, tipos por color, orphan visibility y concept inspector. Query-path replay queda diferido hasta que NeuroPA tenga event ledger propio.

## Métricas de éxito del slice

- Provider y modelo se seleccionan por separado y la combinación enviada es válida.
- Mode y Context no usan prompts nativos del navegador.
- Context elegido altera realmente el payload al provider.
- Todo claim usado aparece como fuente visible en el mensaje/proceso.
- Memory Graph permite encontrar y entender la procedencia de una memoria en menos de tres interacciones.
- Browser QA pasa a 1600, 768 y 480 px sin errores JS/HTTP ni overflow horizontal.
- Suite completa, compileall, Bash syntax y diff check pasan.
