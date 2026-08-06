# Manual de uso de NeuroPA

> Guía para personas que usan NeuroPA a diario. No requiere conocimientos técnicos.

## 1. Qué es NeuroPA

NeuroPA es un espacio de trabajo con IA que vive en **tu dispositivo**. Tus sesiones, tu memoria y tus guardados se almacenan localmente (`~/.local/share/neuropa/`). No hay cuenta, no hay suscripción obligatoria y no hay telemetría oculta.

Cuando la IA responde, puedes ver siempre **qué provider y modelo contestaron** y **si tu mensaje salió del dispositivo** (indicador "Evidencia y egress" en cada respuesta).

## 2. Instalación (una sola vez)

```bash
git clone https://github.com/n30j0su3/neuropa.git
cd neuropa
scripts/install.sh
scripts/run-neuropa.sh
```

Abre `http://127.0.0.1:8474` en tu navegador. Eso es todo.

- Windows: usa `scripts\install.ps1` y `scripts\run-neuropa.ps1`.
- ¿Revisar requisitos sin cambiar nada? `scripts/install.sh --check`.
- ¿Desinstalar? `scripts/uninstall.sh`.

## 3. Primer arranque

La primera vez verás el asistente **"¿Dónde quieres que piense tu IA?"**:

| Opción | Qué significa | Privacidad |
|---|---|---|
| **Usar IA gratuita** (OpenCode) | Empiezas de inmediato, sin claves | Tus mensajes salen a un servicio gratuito |
| **Todo en este dispositivo** (Ollama) | Nada sale de tu equipo | Máxima privacidad, requiere Ollama instalado |
| **Conectar otro servicio** (BYOK) | Usas tu propia clave (ej. OpenRouter gratis) | Sale a tu proveedor con tu clave |
| **Seguir sin IA** | Captura y organiza sin respuestas de IA | Nada sale |

Puedes cambiar la elección cuando quieras en **Ajustes → Ejecutar configuración inicial**. No pierdes nada.

## 4. Tu día a día

### Sesiones

Cada conversación es una **sesión** con título automático. Todo queda guardado aunque cierres el navegador.

- **Nueva sesión:** botón `+ Nueva sesión` (barra de sesiones) o el botón principal.
- **Cambiar de sesión:** botón **Cambiar sesión** o el botón flotante **☰ Sesiones** que aparece en el borde izquierdo cuando la barra está cerrada.
- **Exportar sesión:** menú **Exportar sesión** → HTML offline, Markdown o JSON.

### Escribir

Escribe en la caja inferior y presiona **Enter** (Shift+Enter para salto de línea). Mientras la IA trabaja verás **"Procesando… (Ns)"** tanto en el mensaje como junto al compositor. Puedes **Detener** sin perder lo escrito.

### Controles del compositor (barra "IA · provider · modelo")

- **Provider:** OpenCode gratis / Ollama local / OpenRouter (BYOK).
- **Modelo:** catálogo del provider activo.
- **Modo:** Claridad, Creatividad, Atención al detalle, Memoria. El modo sólo cambia el *enfoque* de la respuesta; **siempre se responde tu solicitud literal actual**.
- **Contexto:** `Esta sesión` (historial reciente), `Memoria · N` (añade los recuerdos que tú elijas como evidencia), `Sin contexto` (pregunta aislada).

### Entregables

Cuando pides algo tangible ("entrégamelo en un solo HTML", "escribe el script", "genera el CSV"), la IA puede crear **archivos reales**. NeuroPA los detecta y los convierte en **Artifacts** automáticamente: verás una fila **📎 Entregables generados** bajo la respuesta con botones **👁 Ver** (el HTML se abre en pestaña nueva, aislado por seguridad) y **⬇ Descargar**.

También puedes guardar cualquier respuesta como entregable Markdown con el botón **Crear entregable Markdown**.

Todo lo guardado vive en **Guardados / Artifacts**: cada tarjeta muestra el tipo (`</>` HTML, `MD` Markdown, `{}` JSON, `ƒx` código), la fecha y acciones rápidas de ver/descargar.

## 5. Memoria con evidencia

La memoria de NeuroPA es **grounded**: un recuerdo (claim) guarda *qué afirma*, *de dónde salió* (fuente) y *cuánta confianza* tiene. Esto evita que la IA "recuerde" cosas inventadas.

- **Guardar un recuerdo:** desde la vista **Memoria**, o pidiéndolo explícitamente ("recuerda que mi proyecto X usa el proveedor Y").
- **Wiki automática:** cada recuerdo crea/actualiza su propia página en la Wiki local — no tienes que mantenerla a mano.
- **Memory Map:** en la vista **Memoria** puedes explorar el grafo de recuerdos, ver cómo se relacionan y abrir sus páginas Wiki.
- **Correcciones:** si algo cambia, el recuerdo viejo se *reemplaza* (supersede), no se borra: siempre puedes auditar qué se creía antes.
- **Usar la memoria en chat:** cambia **Contexto** a `Memoria · N` y selecciona los recuerdos relevantes. La IA los recibe como evidencia citada.

> Nota honesta: hoy la captura de recuerdos es **explícita** (tú decides qué se recuerda). La extracción automática desde conversaciones está en evaluación — la memoria grounded exige fuente declarada y preferimos no contaminarla con inferencias automáticas.

## 6. Privacidad y red

- **Local por defecto:** solo `127.0.0.1`. Nadie más en tu red puede entrar.
- **LAN temporal:** `scripts/run-neuropa.sh --lan` abre acceso directo a dispositivos de tu red de confianza (sin emparejamiento). Si quieres emparejamiento de un solo uso: `--lan --pairing`.
- **Sesión sensible:** activa **"Mantener esta sesión sólo en este dispositivo"** en Ajustes; esos mensajes solo usan IA local (si no hay, se bloquea el envío).
- **Exportar todo:** Ajustes → Exportar e importar → copia JSON con claves redactadas. Importar reemplaza el workspace solo tras tu confirmación.

## 7. Atajos

| Atajo | Acción |
|---|---|
| `Ctrl/Cmd + K` | Paleta de comandos |
| `C` | Nueva captura |
| `M` | Vista Memoria |
| `Enter` / `Shift+Enter` | Enviar / salto de línea |

## 8. Si algo falla

| Síntoma | Qué revisar |
|---|---|
| "No hay provider disponible" (503) | Ajustes → "Dónde trabaja tu IA" muestra el estado; ejecuta la configuración inicial de nuevo |
| 403 al abrir desde otro dispositivo | Arranca con `--lan` (acceso directo) o abre desde el mismo equipo |
| Respuesta tarda | Generar entregables reales puede tomar 1-3 minutos; verás "Procesando…" con el contador |
| OpenRouter con tu clave | Define `NEUROPA_BYOK_KEY` antes de arrancar |
| Timeout en tareas largas | `NEUROPA_PROVIDER_TIMEOUT=600 scripts/run-neuropa.sh` |

## 9. Lo que NeuroPA no es

No diagnostica, no hace claims clínicos y no sustituye atención profesional. Es un workspace de IA con memoria transparente — nada más, y a propósito.
