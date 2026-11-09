# Tarea 4 · Agente de investigación socioeconómica

**Estado.** Servidor MCP del BCRP y Skills de ENAHO 2024 verificados con fuentes oficiales. Las Skills se ejecutaron mediante `uv` desde Codex. La prueba conversacional en Claude Code requiere una sesión autenticada.

**Pregunta inicial:** ¿Cómo evolucionó la inflación de alimentos entre 2020 y 2024 en el Perú, y qué diferencias territoriales y sociodemográficas presentaba la pobreza monetaria en 2024?

[Enunciado y rúbrica](https://github.com/d2cml-ai/Data-Science-Python/issues/201) · [Sesión 04](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code/proyecto) · [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho)

## Alcance y arquitectura

Claude Code coordinará una misma investigación: identifica la serie de inflación de alimentos en el catálogo del BCRP, consulta el servidor MCP, ejecuta las Skills de ENAHO, comprueba las salidas y redacta el informe con trazabilidad. El servidor solo obtiene y calcula series oficiales; los scripts de las Skills procesan microdatos locales y generan tablas, gráficos y mapa. Ninguna cifra del informe debe provenir de memoria del modelo.

```text
Pregunta → Claude Code ┬→ MCP BCRP → series, resúmenes y comparaciones → salidas/figuras
                      └→ Skills ENAHO → Parquet validado → indicadores/figuras/mapa
             → verificación de cifras → informes/informe_final.md
```

[PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md) contiene la matriz de 20 puntos, la estructura prevista, los responsables y las pruebas pendientes.

## Instalación y verificación de la Parte 1

Trabajar **desde `tarea_4/`** con `uv` en el PATH, Python ≥3.11 y acceso HTTPS a BCRPData. El entorno se validó con Python 3.12.15 y las versiones fijadas en `uv.lock`.

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

### Relevo a la integración

Las tres Skills y su dependencia se comprobaron por CLI desde Codex. En una sesión autenticada de Claude Code, verifica el enrutamiento con un pedido como «Elabora un mapa de pobreza monetaria departamental con ENAHO 2024» desde una copia sin Parquet y guarda la conversación real. La fase de integración debe vincular la ejecución de estas Skills con las herramientas MCP del BCRP para contestar la pregunta de investigación.

## Evidencias y entrega

Registrar desde ahora los historiales completos de Work, Codex y Claude Code en `evidencias_ia/`, por fase y en orden cronológico, tras ocultar información sensible. [evidencias_ia/README.md](evidencias_ia/README.md) define el registro. La entrega final requiere un comentario en el [Issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201) con enlaces públicos a informe, pruebas, validaciones, evaluación, integración y conversaciones completas. El plazo del enunciado es el **8 de noviembre de 2026 a las 23:59, hora de Perú**. No publicar una entrega con campos de resultados sin ejecutar.
