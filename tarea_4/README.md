# Tarea 4 · Agente de investigación socioeconómica

**Estado:** servidor MCP de la Parte 1 implementado y verificado con datos oficiales. La conexión y el descubrimiento MCP en Claude Code se comprobaron en un perfil temporal. La ejecución con el modelo requiere iniciar sesión.

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

### Relevo a la Parte 2

Partir del commit de la Parte 1, instalar desde `uv.lock` y repetir las diez pruebas con acceso al BCRP. Completar la comprobación conversacional en Claude Code con una sesión autenticada. Para implementar la limpieza de ENAHO se necesitan los módulos 34 y 02 de 2024 en las rutas documentadas abajo. La integración BCRP–ENAHO corresponde a la fase posterior a la validación de las Skills.

## Datos y reproducción

Descargar por separado los módulos 34 y 02 de ENAHO 2024 y la geometría departamental; consultar [datos/README.md](datos/README.md). Los microdatos originales, el catálogo BCRP descargado y el entorno virtual quedan fuera de Git. Las salidas agregadas, pruebas, informe y evidencias revisadas sí deben versionarse. No publicar identificadores personales, credenciales ni conversaciones sin revisión.

La meta de validación es pobreza nacional cercana a 27.6 % (máximo 0.1 puntos porcentuales de diferencia), 108,664 residentes habituales y 25 unidades territoriales. Estos son **valores de referencia del enunciado**, no resultados de este repositorio. El procesamiento debe calcularlos y registrar fallos sin ajustar datos artificialmente.

## Evidencias y entrega

Registrar desde ahora los historiales completos de Work, Codex y Claude Code en `evidencias_ia/`, por fase y en orden cronológico, tras ocultar información sensible. [evidencias_ia/README.md](evidencias_ia/README.md) define el registro. La entrega final requiere un comentario en el [Issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201) con enlaces públicos a informe, pruebas, validaciones, evaluación, integración y conversaciones completas. El plazo del enunciado es el **8 de noviembre de 2026 a las 23:59, hora de Perú**. No publicar una entrega con campos de resultados sin ejecutar.
