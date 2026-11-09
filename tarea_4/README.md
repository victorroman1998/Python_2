# Tarea 4 · Agente de investigación socioeconómica

**Estado.** Investigación integrada y verificada desde Codex. El servidor BCRP se invocó por MCP stdio con FastMCP y las tres Skills ENAHO se ejecutaron mediante `uv`. La demostración nativa de Claude Code queda pendiente de una sesión autenticada.

**Pregunta.** ¿Cómo evolucionó la inflación de alimentos y bebidas en Lima Metropolitana entre 2020 y 2024, y qué diferencias por área de residencia, sexo y departamento presentó la pobreza monetaria en el Perú en 2024?

[Enunciado y rúbrica](https://github.com/d2cml-ai/Data-Science-Python/issues/201) · [Sesión 04](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code/proyecto) · [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho)

## Alcance y arquitectura

El objetivo es responder preguntas verificables sobre precios y pobreza en el Perú con fuentes oficiales y procedimientos que otra persona pueda ejecutar. La Fase 4 mide la exactitud y la trazabilidad de las respuestas cuando el agente dispone del MCP y las Skills.

El coordinador identifica las series en el catálogo del BCRP, consulta el servidor MCP, ejecuta las Skills de ENAHO y valida las salidas antes de generar el informe. El servidor obtiene y calcula series oficiales. Los scripts de las Skills procesan microdatos locales y generan tablas, gráficos y mapa.

```text
Pregunta → Plan ┬→ FastMCP por stdio → BCRP → series, resúmenes y comparación
                └→ Skills ENAHO → lote validado → indicadores, gráficos y mapa
         → contrastes independientes → informes/informe_final.md
```

[PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md) contiene la matriz de 20 puntos y la planificación general.

## Ejecutar la investigación integrada

Desde `tarea_4/` con HTTPS y `uv` disponible en el PATH.

```bash
uv sync --locked --python 3.12
uv run --locked python scripts/investigar.py --desde-cero
uv run --locked pytest -q
```

La ejecución comprueba los contratos, registra el plan, consulta el BCRP, ejecuta ENAHO y contrasta las cifras antes de publicar el informe y las figuras en el checkout. Si el lote ENAHO falta o falla su validación, activa la limpieza antes de los dos consumidores y se detiene si la limpieza falla. `--desde-cero` demuestra esa dependencia con un directorio de trabajo vacío, manteniendo disponible el lote existente. El coordinador conserva los archivos que coinciden byte por byte. `--sin-descarga` usa insumos ENAHO preparados en `datos/`. El MCP y la verificación del BCRP requieren acceso de red.

La bitácora local se crea en `evidencias_ia/integracion/ejecucion_local.jsonl`. Para repetir el flujo conservando ese registro, indica una ruta nueva con `--bitacora`. [Informe](informes/informe_final.md) · [Verificación de cifras](informes/verificacion_cifras.md) · [Ejecución Codex](evidencias_ia/integracion/README.md) · [Guía para Claude Code](evidencias_ia/integracion/claude_code.md).

## Instalación y verificación de la Parte 1

Trabajar **desde `tarea_4/`** con `uv` en el PATH, Python ≥3.11 y acceso HTTPS a BCRPData. El entorno se validó con Python 3.12.15 y las versiones fijadas en `uv.lock`.

Las dependencias de ejecución son FastMCP, HTTPX, pandas, PyArrow, GeoPandas y Matplotlib. Pytest se instala con el grupo de desarrollo. Los enlaces de descarga del INEI, el contraste departamental y la geometría están en [datos/README.md](datos/README.md). Las observaciones de precios provienen de [BCRPData](https://estadisticas.bcrp.gob.pe/estadisticas/series/).

```bash
cd tarea_4
uv sync --locked --python 3.12
uv run --locked pytest -q mcp/
uv run --locked python evidencias_ia/mcp/verificar_stdio.py
```

Las ocho pruebas de la sesión 04 se conservan en `mcp/test_server.py`. Las dos propias cubren la alineación y los faltantes, y el rechazo de frecuencias distintas. El verificador por stdio arranca el comando de `.mcp.json`, comprueba los componentes MCP y contrasta sus resultados con la API. La salida y los límites de la prueba con Claude Code están en [evidencias_ia/mcp/validacion.md](evidencias_ia/mcp/validacion.md).

### Contrato del servidor

| Herramienta | Entrada | Resultado |
|---|---|---|
| `buscar_series` | Texto, frecuencia opcional y límite | Códigos y metadatos del catálogo oficial |
| `serie` | Código y fechas inclusivas | Observaciones, periodos publicados sin valor, metadatos y URL de consulta |
| `resumen` | Código y fechas inclusivas | Primera y última observación, cambio, variación relativa, promedio y extremos |
| `comparar_series` | Dos códigos de la misma frecuencia y fechas inclusivas | Pares por periodo, faltantes por serie, correlación de Pearson y ambas URLs |

Usar `AAAA-MM-DD` para series diarias, `AAAA-MM` para mensuales, `AAAA-T1` a `AAAA-T4` para trimestrales y `AAAA` para anuales. El resumen devuelve variación relativa nula cuando el valor inicial es cero. La comparación usa la unión de los periodos que publicó al menos una serie e informa los faltantes sin imputarlos. Pearson se calcula sobre los pares completos y se devuelve nula con menos de dos pares o con una serie constante. Los valores conservan sus unidades de origen.

La primera consulta del proceso carga el catálogo. El CSV local se reutiliza si tiene menos de 24 horas al cargarlo y el catálogo queda en memoria durante el proceso. Las consultas de series se reutilizan en bloques de 15 minutos durante el mismo proceso. El BCRP puede entregar JSON con cabecera `text/html` o responder con una página HTML temporal. El servidor comprueba el contenido y reintenta fallos transitorios.

### Claude Code

Desde `tarea_4/`, ejecutar `claude`, iniciar sesión y aprobar el servidor de proyecto `bcrp`. Comprobar la conexión con `claude mcp list` y consultar las herramientas en `/mcp`. La configuración de proyecto arranca `uv run --locked python mcp/server.py` por stdio.

En una sesión autenticada, pedir «Consulta el IPC mensual de Lima de marzo de 2025 con la serie PN01271PM e incluye la fuente oficial». La guía se puede seleccionar con `@bcrp:bcrp://catalogo` y el prompt se puede invocar con `/mcp__bcrp__informe inflación`. La plantilla `bcrp://serie/{codigo}` devuelve la ficha de un código conocido. [Guía MCP de Claude Code](https://code.claude.com/docs/en/mcp)

## Reproducir las Skills de ENAHO 2024

Desde `tarea_4/`, con Python 3.12 y el entorno de `uv.lock`:

```bash
uv sync --locked --python 3.12
uv run --locked python .claude/skills/limpiando-enaho/scripts/limpiar.py
uv run --locked python .claude/skills/graficando-enaho/scripts/graficar.py
uv run --locked python .claude/skills/mapeando-enaho/scripts/mapear.py
uv run --locked pytest -q tests/
uv run --locked pytest -q mcp/
```

Limpieza descarga los dos ZIP oficiales y el CSV de contraste. Mapeo descarga el GeoJSON. Si el entorno carece de HTTPS, guarda los archivos en `datos/` como se indica en [la guía de descarga](datos/README.md) y añade `--sin-descarga` a limpieza y mapeo. Las pruebas ENAHO usan datos sintéticos controlados y pueden ejecutarse sin red con `uv run --locked --offline pytest -q tests/`. Las pruebas MCP consultan el BCRP.

- `limpiando-enaho` publica [indicadores.csv](salidas/indicadores.csv), [validacion.txt](salidas/validacion.txt) y el Parquet local `salidas/personas_2024.parquet`. El CSV distingue `personas` (residentes con `facpob07`) y `sumaria` (estimación poblacional de hogares con `factor07 × mieperho`). Consulta la [metodología](.claude/skills/limpiando-enaho/reference.md) para interpretar los denominadores y las tolerancias.
- `graficando-enaho` crea las barras por [área](figuras/pobreza_area_2024.png), [sexo](figuras/pobreza_sexo_2024.png) y [departamento](figuras/pobreza_departamento_2024.png). Usa `--grupo area`, `--grupo sexo` o `--grupo departamento` para generar una sola figura.
- `mapeando-enaho` crea el [mapa departamental](mapas/pobreza_departamento_2024.png) a partir de las mismas tasas por persona, tras contrastar los 25 ámbitos y unir `ubigeo[:2]` a `FIRST_IDDP`.

El informe registra recuentos, estructura, denominadores, diferencias absolutas y tolerancias. Las visualizaciones requieren el estado `APROBADO` y comprueban que el CSV y el Parquet correspondan a esa validación mediante SHA-256. Si se clona el repositorio o cambia un archivo del lote, ejecuta primero la limpieza. Los PNG y los agregados están versionados para consulta.

### Resultados verificados

La ejecución del 8 de noviembre de 2026 leyó 33 691 hogares y 117 721 registros de miembros. El filtro seleccionó 108 664 residentes habituales. La unión conservó todos los residentes y el GeoJSON aportó 25 unidades válidas, con Callao (07) y Lima (15) separados.

| Pobreza monetaria | Personas | Sumaria | Referencia |
| --- | ---: | ---: | ---: |
| Nacional | 27,5287 % | 27,5795 % | 27,6 % |
| Urbana | 24,7352 % | 24,8070 % | 24,8 % |
| Rural | 39,4417 % | 39,3028 % | 39,3 % |

El desvío nacional con `facpob07` fue 0,0713 pp frente al límite de 0,10 pp. Los 25 departamentos coincidieron con el CSV de referencia al redondear Sumaria a una décima. En el cálculo directo, el mayor desvío fue 0,5177 pp en Puno frente a la tolerancia de 0,60 pp. El [registro de ejecución](evidencias_ia/skills/03_ejecucion_enaho.txt) detalla las comprobaciones.

## Evaluación experimental

El [protocolo](evaluacion/README.md) compara las mismas diez preguntas en dos condiciones. A dispone de los datos originales y de herramientas generales. B dispone también del MCP BCRP y de las tres Skills ENAHO. Cada pregunta se envía en una sesión independiente. Los criterios y el SHA-256 del patrón se fijaron antes de lanzar el lote. Se requiere Codex CLI autenticado para repetir esta alternativa. La demostración nativa con Claude Code sigue pendiente.

El lote con `gpt-6.1-sol` registró 20 sesiones. A acertó 10/10 con 81,12 s de media y B acertó 10/10 con 44,30 s de media. B registró 15 llamadas MCP y seis ejecuciones verificadas de `limpiando-enaho`. La diferencia de tiempo es descriptiva y corresponde a una sola repetición por pregunta y condición. [Comparación por pregunta](evaluacion/comparacion.md)

Desde `tarea_4/` en PowerShell, prepara los insumos según [datos/README.md](datos/README.md) y verifica que `codex exec --help` incluya las opciones del protocolo. Los siguientes comandos reproducen el patrón y lanzan un lote nuevo en Windows con MXC. La carpeta temporal del lote queda separada del repositorio.

```powershell
uv sync --locked --python 3.12
uv run --locked python evaluacion/referencias.py --bcrp datos/bcrp-evaluacion --descargar-bcrp --salida datos/preguntas-reconstruidas.csv
Get-FileHash evaluacion/preguntas.csv,datos/preguntas-reconstruidas.csv -Algorithm SHA256
$runtimeEvaluacion = Join-Path $env:TEMP "tarea4-fase4-runtime"
$env:UV_PROJECT_ENVIRONMENT = $runtimeEvaluacion
uv sync --locked --python 3.12
Remove-Item Env:UV_PROJECT_ENVIRONMENT
uv run --locked python evaluacion/ejecutar.py --bcrp datos/bcrp-evaluacion --runtime $runtimeEvaluacion --evidencias datos/nueva-evaluacion
uv run --locked pytest -q
```

El ejecutor comprueba los SHA-256 del prerregistro y hace los controles de aislamiento y conexión antes de enviar preguntas. Si una fuente cambia de bytes, conserva el patrón histórico y utiliza los insumos con las huellas registradas para replicarlo. Las respuestas de un lote nuevo requieren una nueva extracción según los mismos criterios. Para reproducir el cálculo de métricas del lote publicado, ejecuta `uv run --locked python evaluacion/calificar.py --salida datos/resultados-reconstruidos.csv`.

[Preguntas y referencias](evaluacion/preguntas.csv) · [Prerregistro](evaluacion/prerregistro.json) · [Resultados por ejecución](evaluacion/resultados.csv) · [Comparación y limitaciones](evaluacion/comparacion.md) · [Transcripciones y controles](evidencias_ia/evaluacion/)

## Evidencias y entrega

[evidencias_ia/README.md](evidencias_ia/README.md) inventaría las trazas, extractos y resúmenes publicados, e identifica los historiales conversacionales faltantes. El lote de 20 sesiones de evaluación sí conserva las transcripciones de la CLI; eso no completa las conversaciones de planificación y desarrollo. La entrega final requiere un comentario en el [Issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201) con enlaces públicos a informe, pruebas, validaciones, evaluación, integración y evidencias disponibles. El plazo del enunciado es el **8 de noviembre de 2026 a las 23:59, hora de Perú**.
