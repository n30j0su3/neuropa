# NeuroPA — Mobile Composer B Design

**Fecha:** 2026-08-04  
**Estado:** Aprobado visualmente por N30, pendiente de implementación  
**Superficie:** `neuropa/frontend/index.html`  
**Modo:** Operate · mobile-first

## 1. Job y resultado

En móvil, la persona debe poder escribir y enviar mensajes con el mínimo ruido posible, conservando acceso explícito a provider, modelo, modo y contexto. El textarea es el protagonista; configuración y retracción son controles secundarios.

## 2. Dirección aprobada

### Dos estados globales

1. **Compacto — predeterminado:** muestra resumen de configuración, textarea, Adjuntar, Enviar y control principal de retracción.
2. **Retraído:** muestra únicamente textarea, Enviar y el control principal flotante. Adjuntar y configuración quedan ocultos.

### Configuración por tap

- El resumen `Provider · Modelo · Modo · Contexto` abre una lista plana.
- Cada fila completa es un target táctil de 44–52 px.
- No se usan cards anidadas; la separación se resuelve con espacio y divisores sutiles.
- El indicador del resumen es un icono de **sliders/configuración**, no una flecha.

### Composer

- El textarea inicia en una línea y crece dinámicamente hasta seis líneas.
- Superado el máximo, activa scroll vertical interno.
- Enviar conserva un target de 44 px, con núcleo visual aproximado de 32 px.
- Enviar permanece neutro vacío y toma el acento turquesa cuando existe contenido.
- El botón queda alineado abajo mientras el textarea crece.

### Control principal flotante

- El chevron de compactar/retraer flota fuera del borde superior derecho del módulo.
- No tiene fondo, borde ni contenedor visible.
- Mantiene target accesible de 44 px.
- Su ubicación no puede superponerse al placeholder, texto multilínea ni borde del composer.

## 3. Movimiento

- Transición coordinada de altura, opacidad y contenido con curva ease-out.
- Sin animaciones decorativas adicionales.
- `prefers-reduced-motion: reduce` reduce todas las transiciones a una duración prácticamente instantánea.

## 4. Límites

- No cambiar paleta, tipografía, navegación ni arquitectura single-file.
- No añadir frameworks, librerías ni dependencias.
- No eliminar Adjuntar; sólo ocultarlo en estado retraído.
- No ocultar provider/modelo/modo/contexto en el estado compacto.
- No introducir tercer estado global ni bottom sheet.

## 5. Estados y accesibilidad

- `aria-expanded` refleja configuración y estado global.
- Etiquetas accesibles: `Abrir configuración`, `Retraer panel`, `Expandir panel`, `Enviar mensaje`.
- Todos los targets interactivos miden al menos 44 × 44 px.
- Teclado: `Enter` envía; `Shift+Enter` añade línea.
- Vacío: Enviar no ejecuta una solicitud.
- Envío activo: el textarea conserva su comportamiento actual durante loading/error; no se altera el contrato del harness.

## 6. Gates de aceptación

1. QA real a 480 px: compacto, configuración abierta, textarea de 1 y 6 líneas, retraído vacío y retraído multilínea.
2. Cero overflow horizontal.
3. Cero overlaps entre control flotante, textarea, placeholder y borde.
4. Cero targets menores de 44 px.
5. `prefers-reduced-motion` verificado.
6. Flujo real de envío y Adjuntar preservado.
7. Consola JS y respuestas `/api/*` sin errores nuevos.
8. Suite Python, `node --check` del JS extraído y `git diff --check` verdes.

## 7. Evidencia de diseño

Mockup final interactivo:

- Sesión visual: `.superpowers/brainstorm/3813897-1785901729/content/mobile-composer-approved-final.html`
- URL temporal de revisión: `http://192.168.1.21:64204`
- Comprobación observada: estado retraído con `configHeight=0`, `attachDisplay=none`, composer de 59 px y control flotante completamente fuera del módulo, sin fondo ni borde.
