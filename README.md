# NeuroPA

> Tu segunda memoria local para capturar lo que aparece en tu cabeza, elegir el siguiente paso y volver a encontrarlo cuando lo necesites.

[![Licencia: AGPL-3.0](https://img.shields.io/badge/licencia-AGPL--3.0-blue.svg)](LICENSE)

## ¿Qué es?

NeuroPA es un asistente personal pensado para cerebros con TDAH: cuando una idea, tarea o preocupación aparece, la guardas sin tener que organizarla en ese instante. Después puedes convertir ese caos en un siguiente paso pequeño, revisar tu día y recuperar lo importante sin depender de tu memoria de trabajo.

No intenta convertirte en una máquina de productividad. Te ayuda a volver al foco después de una interrupción, aparcar lo que no toca ahora y recordar por qué algo importaba. NeuroPA funciona en tu propio equipo, con una interfaz local y un lenguaje humano: menos fricción, más continuidad.

## Instalación rápida

### Con `uv` (recomendado)

```bash
uv tool install neuropa
neuropa
```

### Con `pip`

```bash
python -m pip install neuropa
neuropa
```

### Desde el código fuente

```bash
git clone https://github.com/FreakingJSON/neuropa.git
cd neuropa
uv sync
uv run neuropa
```

Al arrancar, NeuroPA abre automáticamente `http://127.0.0.1:8474` en tu navegador. Tus datos se guardan localmente; no necesitas crear una cuenta.

## Uso

```bash
# Abrir NeuroPA y la interfaz local
neuropa

# Usar otro puerto
NEUROPA_PORT=9000 neuropa
# o
neuropa --port 9000

# Ver dónde están tus datos y tu token local
neuropa --status

# Hacer una copia JSON de todo lo guardado
neuropa --export backup.json
# También puedes imprimirla en pantalla
neuropa --export

# Ver la versión instalada
neuropa --version
```

Desde la interfaz puedes:

- **Capturar**: guardar una idea, tarea o nota en segundos.
- **Today**: elegir tu MIT (Most Important Thing), ver el parking lot y recuperar el ritmo.
- **Memory**: guardar y consultar recuerdos con su fuente y nivel de confianza.
- **Focus**: iniciar un bloque de concentración, pausarlo y cerrarlo sin perder el contexto.

Pulsa `Ctrl+C` en la terminal para cerrar NeuroPA de forma limpia. Tus datos permanecen en tu equipo.

## Features

- Captura rápida tipo inbox, sin clasificación obligatoria.
- Vista **Today** con prioridad, siguiente acción y recuperación.
- Memoria con evidencia: cada afirmación puede conservar su fuente.
- Bloques de foco con pausa, finalización y reflexión breve.
- API local protegida por token loopback.
- Exportación e importación JSON para copias y portabilidad.
- Router de proveedores preparado para uso local, BYOK o servicio gestionado.
- Frontend premium servido desde la misma aplicación.
- SQLite local con migraciones y modo WAL.

## Privacidad primero

NeuroPA es **local-first**: por defecto la base de datos y el token viven en tu máquina, en `~/.local/share/neuropa/` en Linux (o la ruta equivalente de tu sistema). Puedes cambiar la ubicación con `NEUROPA_DATA_DIR`.

No incluye telemetría ni rastreo oculto. La API solo se expone en loopback (`127.0.0.1`) y las funciones protegidas requieren el token local. Si conectas un proveedor externo, esa decisión es tuya y debes revisar sus propias políticas de privacidad.

## Self-hosted vs SaaS

NeuroPA es **open-core**:

- **Self-hosted**: ejecuta todo localmente, controla tus datos, proveedores, backups y actualizaciones.
- **SaaS / gestionado**: puede ofrecer comodidad, sincronización, colaboración o soporte, pero implica confiar datos a un tercero y revisar sus condiciones.

El núcleo local sigue siendo útil por sí solo. El servicio gestionado no es obligatorio para empezar.

## Para developers

```bash
uv sync --extra dev
uv run pytest -q
```

Contribuir es sencillo:

1. Abre una issue explicando el problema o la propuesta.
2. Crea una rama pequeña y enfocada.
3. Añade o actualiza pruebas para el comportamiento nuevo.
4. Ejecuta la suite completa y abre un pull request.

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para estilo de commits, pruebas y expectativas de revisión.

## Licencia

NeuroPA se distribuye bajo la licencia [GNU Affero General Public License v3.0](LICENSE). Si modificas y ofreces este software a través de una red, conserva las libertades de la AGPL y publica el código fuente correspondiente.
