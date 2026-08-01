# NeuroPA — PRD v2: AI Workspace / Local Harness

**Estado:** Canonical draft for implementation
**Fecha:** 2026-08-01
**Decisión de producto:** corregir el centro de gravedad de v1
**Base:** `specs/PRD-v1.md`, `architecture/ARCHITECTURE-v1.md` y mensaje
autoritativo de N30

> **Resumen ejecutivo.** NeuroPA es primero un workspace/harness local para
> usar IA: una interfaz no-técnica para conversar, organizar sesiones,
> conectar providers, activar agentes/modos cognitivos, ejecutar tools/skills,
> producir artifacts y conservar contexto en proyectos, wiki y memoria.
> El módulo de Executive Function conserva captura, Today y Focus como una
> superficie integrada, pero no define por sí solo el producto.

## 1. Decisión canónica

### 1.1 Producto principal

El producto principal es **AI Workspace / harness local**. La promesa es:

> “Instala, elige cómo quieres usar IA y trabaja con contexto persistente,
> herramientas y resultados que siguen siendo tuyos.”

Debe servir a personas no técnicas desde el primer arranque y también a
usuarios que desean modelos locales, open-source, BYOK y control detallado.
Las necesidades ADHD orientan los defaults y los modos cognitivos; no son un
límite de audiencia. Personas neurotípicas son bienvenidas.

### 1.2 Distribución y propiedad

- **Repo público OSS:** aplicación local completa y usable, sin cuenta ni
  telemetría obligatoria. Licencia aprobada: core AGPL-3.0.
- **SDK y contratos interoperables:** Apache-2.0 cuando estén separados del
  core para favorecer providers, tools y adaptadores comunitarios.
- **SaaS privado:** repo separado, fuera de este producto/repo público.
  Añade operación gestionada, identidad, sync, backups, cuotas y billing; no
  es requisito para usar el workspace local.
- El SaaS no debe convertirse en la arquitectura de referencia del MVP OSS ni
  introducir dependencias cloud en el core local.

## 2. Problema y usuarios

### Problema

Las herramientas de IA actuales obligan a elegir entre simplicidad cloud sin
control, configuración técnica fragmentada o chats sin memoria ni artifacts.
El usuario pierde sesiones, contexto, instrucciones y resultados; además,
las personas con ADHD sufren fricción de inicio, saturación de opciones y
memoria de trabajo limitada.

### Usuarios prioritarios

1. **Usuario común no técnico:** quiere instalar y empezar a conversar sin
   terminal, API keys ni conceptos de infraestructura.
2. **Creador, investigador, estudiante o profesional:** necesita proyectos,
   sesiones retomables, fuentes, artifacts y memoria grounded.
3. **Usuario local/open-source:** prefiere Ollama/llama.cpp, modelos libres,
   privacidad y ejecución offline.
4. **Usuario ADHD o con funciones ejecutivas variables:** necesita captura,
   reentrada sin culpa, modos de creatividad, foco, detalle y memoria.

## 3. Principios de producto

- **Harness antes que chatbot:** una conversación es una sesión de trabajo,
  no un destino aislado.
- **Free providers primero:** el onboarding debe ofrecer un camino gratuito o
  local antes de pedir una suscripción. Las cuotas son explícitas y nunca se
  prometen como permanentes.
- **Local y open-source por defecto de confianza:** el usuario puede funcionar
  sin red, exportar sus datos y ver qué texto sale del dispositivo.
- **Proceso resumido, no cadena de pensamiento privada:** la UI puede mostrar
  plan, pasos, supuestos, fuentes, decisiones y estado de herramientas; nunca
  solicita ni expone razonamiento interno privado token a token.
- **Grounded memory:** si una respuesta usa memoria/wiki, muestra evidencia;
  si no existe evidencia, la respuesta debe decirlo.
- **Progressive disclosure:** defaults simples, controles avanzados
  disponibles sin convertir el primer arranque en un panel de DevOps.
- **YAGNI estricto:** cada feature debe mejorar conversación, contexto,
  ejecución, resultado o reentrada. Si no, queda fuera.

## 4. Alcance MVP P0 real

P0 es la primera versión que una persona puede instalar, usar y recomendar
sin terminal. P0 no intenta ser un sistema operativo personal completo.

### P0-A — Onboarding no-tech

- Instalar/abrir la app y crear un workspace local sin cuenta.
- Elegir una ruta de IA guiada: provider gratuito disponible, provider local
  detectado/instalable (Ollama), o BYOK opcional.
- Explicar en lenguaje claro: local, free, BYOK, cloud, límites y privacidad.
- Ejecutar una conversación de prueba y crear el primer proyecto o artifact.
- Poder continuar offline con funciones locales aunque no haya provider LLM.

**Criterio de aceptación:** una persona no técnica completa el onboarding en
menos de cinco minutos sin abrir terminal ni editar archivos de configuración.

### P0-B — Workspace, chat y sesiones

- Workspace local con navegación por **Home, Sessions, Projects, Wiki/Memory,
  Artifacts, Tools/Skills y Settings**.
- Chat streaming con historial, cancelación, regeneración y edición de
  mensajes.
- Sesiones nombrables, retomables y vinculables a proyecto, artifact o fuente.
- Contexto explícito: qué fuentes se incluyeron, qué provider/modelo se usó y
  qué herramientas se ejecutaron.
- “Resumen de proceso” opcional: objetivo entendido, plan corto, acciones,
  supuestos, fuentes y resultado. Sin revelar chain-of-thought privada.

### P0-C — Providers y routing

- Contrato único de provider con adaptadores para al menos un gateway gratuito,
  OpenRouter `:free` o equivalente, y un runtime local OpenAI-compatible.
- Ollama como integración local prioritaria; llama.cpp queda como adaptador
  compatible o ruta posterior si el empaquetado lo exige.
- BYOK para providers compatibles, almacenado en keyring/secret store local.
- Health check, timeout, cancelación, backoff limitado y fallback explícito.
- Etiquetas visibles: `local`, `free`, `BYOK`, `managed`; coste/privacidad y
  destino del texto antes de enviar.

No se embebe una API key global en el cliente. “Free” describe el acceso
vigente del provider, no un SLA de NeuroPA.

### P0-D — Agentes y modos cognitivos

Un **agent/mode** es una configuración declarativa de instrucciones, contexto,
tools permitidas, formato de salida y límites. P0 incluye presets editables:

- **Creatividad:** divergencia, ideas, combinaciones y exploración.
- **Claridad/ejecución:** convierte ambigüedad en siguiente paso pequeño.
- **Atención al detalle:** checklist, contradicciones, edge cases y revisión.
- **Memoria:** recupera contexto grounded y separa hechos, inferencias y
  preguntas abiertas.

Cada modo puede invocarse desde chat o sesión; el usuario siempre puede ver y
cambiar el modo activo. No se hacen claims clínicos ni se etiqueta/diagnostica
al usuario.

### P0-E — Tools y skills seguras

- Registro local de tools/skills con nombre, versión, descripción y permisos.
- P0 incluye tools internas para buscar memoria/wiki, leer/escribir artifacts,
  consultar proyectos y trabajar con calendario/reminders locales.
- Confirmación humana para acciones externas, destructivas o que envíen datos.
- Allowlist de filesystem, red y comandos; sin ejecución arbitraria por defecto.
- Importación manual de una skill documentada; marketplace y distribución
  remota quedan fuera de P0.

### P0-F — Artifacts y proyectos

- Crear, listar, previsualizar, versionar y exportar artifacts generados o
  adjuntados: Markdown, texto, JSON, HTML y archivos pequeños.
- Vincular artifact ↔ sesión ↔ proyecto ↔ fuentes.
- Proyecto mínimo: propósito, estado, contexto, sesiones y siguiente acción.
- Guardado explícito y autosave local; nunca perder una respuesta por no haber
  creado antes un proyecto.

### P0-G — Wiki/memoria grounded

- Capturar notas, decisiones, hechos y resúmenes de sesión en memoria local.
- Búsqueda local por texto/FTS; embeddings son opcionales, no requisito P0.
- Cada respuesta basada en memoria muestra fuente, fecha y tipo de evidencia.
- Distinguir `hecho`, `preferencia`, `inferencia`, `pregunta` y `sin evidencia`.
- Exportar e importar memoria y wiki sin lock-in.

### P0-H — Executive Function integrado

Este módulo conserva y reencuadra los módulos útiles de v1:

- **Capture:** brain dump de texto sin campos obligatorios.
- **Today:** una acción principal, parking lot y entrada rápida a sesión.
- **Focus:** timer flexible, pausa, reducción de alcance y cierre con próximo
  paso.
- **Reminders/calendar:** reminders locales y calendario local/ICS básico,
  siempre subordinados al workspace.
- **Recovery:** reentrada compasiva después de ausencia, sin backlog punitivo.

Executive Function no crea un segundo producto ni duplica Projects/Sessions.
Sus entidades se enlazan con el mismo modelo de workspace.

### P0-I — Privacidad, portabilidad y operación local

- Cero telemetría y cero phone-home por defecto.
- Inventario de egress visible y pruebas de modo sin red.
- SQLite local, backups rotativos y export/import verificable.
- Datos sensibles configurables como local-only.
- Accesibilidad keyboard-first, reduced motion, contraste y lenguaje sin culpa.

## 5. Requisitos no funcionales P0

| Área | Contrato de salida |
|---|---|
| Instalación | Usuario no técnico sin terminal; Windows/macOS/Linux objetivo |
| Offline | Captura, navegación, búsqueda, proyectos, artifacts y export funcionan |
| Rendimiento | Inicio local < 3 s en equipo de referencia; búsqueda < 500 ms/10K items |
| Privacidad | Sin telemetría default; secretos fuera de logs y frontend público |
| Seguridad | API local loopback autenticada; tools con permisos y confirmaciones |
| Accesibilidad | Keyboard-first, focus visible, reduced motion, labels semánticos |
| Portabilidad | Markdown/JSON/ZIP/ICS; restauración en instalación limpia |
| Honestidad IA | Fallback y límites visibles; “no tengo evidencia” permitido |

## 6. Flujo principal de P0

```text
Abrir workspace
  → elegir modo IA (free / local / BYOK)
  → iniciar chat o capturar ruido mental
  → guardar como sesión, proyecto o artifact
  → usar modo cognitivo + tools permitidas
  → registrar resumen, fuentes y decisiones en wiki/memoria
  → retomar desde Home, Projects, Sessions o Today
```

## 7. Fuera de alcance: YAGNI explícito

No se construye en P0 ni se usa para justificar complejidad temprana:

- SaaS, multi-tenancy, auth remota, billing, cuotas operativas y sync cloud.
- Aplicaciones móviles nativas o companion apps.
- Marketplace de skills, plugins remotos o marketplace de prompts.
- Red social, colaboración multiusuario, body doubling humano o videollamadas.
- Integraciones Gmail/Slack/Jira/Notion/Obsidian masivas.
- Diagnóstico, tratamiento, scoring clínico o perfilado ADHD.
- Agentes autónomos de larga duración sin supervisión.
- Razonamiento interno expuesto como chain-of-thought.
- Vector DB, knowledge graph distribuido o RAG cloud obligatorio.
- Billing, gamificación, streaks, enterprise SSO y analítica de comportamiento.

Se reconsideran sólo con evidencia de usuarios, una propuesta de alcance y
una decisión explícita posterior a P0.

## 8. P1 y evolución posterior

P1 puede añadir importadores, más runtimes locales, calendario Google/Apple
con permisos, voz local, jobs largos, sync E2E opt-in y colaboración limitada.
El SaaS privado se planifica aparte, reutilizando contratos públicos pero sin
mover su código al repo OSS.

## 9. Métricas de validación

- Primera conversación o captura completada en < 5 minutos desde instalación.
- Primer artifact o proyecto creado en la primera sesión.
- Retomar una sesión anterior sin reconfigurar provider ni contexto.
- Completar el flujo principal sin red salvo la llamada LLM elegida.
- Exportar y restaurar un workspace en instalación limpia.
- Cero acciones externas ejecutadas por una tool sin confirmación.
- Dogfooding: al menos dos semanas de uso real sin depender de una feature P1.

No se usan como métricas P0 los streaks, horas de uso, volumen de mensajes ni
retención basada en telemetría oculta.

## 10. Trazabilidad con v1

| v1 | Corrección v2 |
|---|---|
| Quick Capture / Today / Focus | Se conservan dentro de Executive Function |
| Provider router gestionado primero | Free/local/BYOK primero; managed no bloquea el core |
| Frontend premium del harness | Pasa a ser la superficie principal, no un módulo adicional |
| Memoria grounded | Se amplía a Wiki/Memory del workspace con provenance |
| SaaS en milestones del mismo producto | Se separa en repo privado y fase posterior |
| Body doubling/integraciones masivas | YAGNI; sólo evidencia posterior puede reabrirlas |

## 11. Licencia y gobernanza

La decisión de licencia queda fijada como **AGPL-3.0 para el core OSS** y
**Apache-2.0 para SDK/contratos separables**. Debe existir un mapa de licencias
por paquete antes de publicar. El SaaS privado no altera la obligación de que
el workspace local sea funcional, exportable y operable sin cuenta.
