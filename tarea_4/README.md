# Tarea 4 · Agente de investigación socioeconómica

**Estado:** estructura y contrato de pruebas preparados; servidor, Skills, investigación y evaluación pendientes de implementación y ejecución. No hay resultados validados ni pruebas aprobadas que declarar.

**Pregunta inicial:** ¿Cómo evolucionó la inflación de alimentos entre 2020 y 2024 en el Perú, y qué diferencias territoriales y sociodemográficas presentaba la pobreza monetaria en 2024?

[Enunciado y rúbrica](https://github.com/d2cml-ai/Data-Science-Python/issues/201) · [Sesión 04](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code/proyecto) · [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho)

## Alcance y arquitectura

Claude Code coordinará una misma investigación: identifica la serie de inflación de alimentos en el catálogo del BCRP, consulta el servidor MCP, ejecuta las Skills de ENAHO, comprueba las salidas y redacta el informe con trazabilidad. El servidor solo obtiene y calcula series oficiales; los scripts de las Skills procesan microdatos locales y generan tablas, gráficos y mapa. Ninguna cifra del informe debe provenir de memoria del modelo.

```text
Pregunta → Claude Code ┬→ MCP BCRP → serie, resumen y gráfico → salidas/figuras
                      └→ Skills ENAHO → Parquet validado → indicadores/figuras/mapa
             → verificación de cifras → informes/informe_final.md
```

[PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md) contiene la matriz de 20 puntos, la estructura prevista, los responsables y las pruebas pendientes.

## Entorno previsto

Trabajar **desde `tarea_4/`**. `pyproject.toml` define un entorno independiente con Python ≥3.11, FastMCP 4, httpx, Pandas, PyArrow, GeoPandas, Matplotlib y Pytest. Al implementar, generar y versionar `uv.lock` con `uv lock`; después instalar con `uv sync --locked`. El terminal de preparación no pudo resolver github.com, por lo que aquí no se instalaron dependencias ni se ejecutaron pruebas.

```bash
cd tarea_4
uv lock
uv sync --locked
uv run pytest -q mcp/test_server.py
claude
```

`.mcp.json` configura el servidor local para Claude Code. Su conexión, recurso, prompt y herramientas deben comprobarse en Claude Code cuando el servidor esté terminado. La presencia del archivo no demuestra esa integración.

## Datos y reproducción

Descargar por separado los módulos 34 y 02 de ENAHO 2024 y la geometría departamental; consultar [datos/README.md](datos/README.md). Los microdatos originales, el catálogo BCRP descargado y el entorno virtual quedan fuera de Git. Las salidas agregadas, pruebas, informe y evidencias revisadas sí deben versionarse. No publicar identificadores personales, credenciales ni conversaciones sin revisión.

La meta de validación es pobreza nacional cercana a 27.6 % (máximo 0.1 puntos porcentuales de diferencia), 108,664 residentes habituales y 25 unidades territoriales. Estos son **valores de referencia del enunciado**, no resultados de este repositorio. El procesamiento debe calcularlos y registrar fallos sin ajustar datos artificialmente.

## Evidencias y entrega

Registrar desde ahora los historiales completos de Work, Codex y Claude Code en `evidencias_ia/`, por fase y en orden cronológico, tras ocultar información sensible. [evidencias_ia/README.md](evidencias_ia/README.md) define el registro. La entrega final requiere un comentario en el [Issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201) con enlaces públicos a informe, pruebas, validaciones, evaluación, integración y conversaciones completas. El plazo del enunciado es el **8 de noviembre de 2026 a las 23:59, hora de Perú**. No publicar una entrega con campos de resultados sin ejecutar.
