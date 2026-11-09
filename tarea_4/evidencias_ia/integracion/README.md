# Evidencia de integración · Parte 3

**Demostración realizada.** Codex interpretó la pregunta, dejó el plan antes de ejecutar, leyó los tres contratos de las Skills, implementó la coordinación y lanzó la ejecución integrada. El proceso Python abrió el servidor de proyecto definido en `.mcp.json` con el cliente FastMCP por stdio. Las herramientas viajaron por `tools/list` y `tools/call`. Los scripts de ENAHO se ejecutaron por CLI según sus respectivos `SKILL.md`. Codex revisó el informe, las figuras y el resultado de las comprobaciones.

```bash
uv run --locked python scripts/investigar.py --desde-cero --sin-descarga --bitacora evidencias_ia/integracion/ejecucion_codex.jsonl
```

La ejecución del 8 de noviembre de 2026, en hora de Lima, está registrada de inicio a fin en [ejecucion_codex.jsonl](ejecucion_codex.jsonl). La bitácora se escribe al ocurrir cada evento. Para seguir la demostración:

1. `plan` y `skill_disponible` registran el plan previo y las huellas de los contratos.
2. `mcp_tools/list` registra las cuatro herramientas anunciadas por el servidor. `mcp_tools/call` y `mcp_respuesta` vinculan ocho llamadas exitosas a sus argumentos y respuestas en [bcrp_mcp.json](../../salidas/bcrp_mcp.json). La búsqueda nacional no devolvió una serie pertinente de IPC. Se eligieron `PN09822PM` y `PN01273PM` por su etiqueta exacta, frecuencia y fuente de origen. `comparar_series` alineó 60 pares completos.
3. El primer `enaho_lote` señala que el directorio aislado estaba vacío. `skill_inicio` y `skill_fin` registran los comandos y salidas reales. Tras aprobar `limpiando-enaho`, el graficador y el mapeador recibieron la misma ruta de lote. La unión entregó 25 geometrías con tasa.
4. `contrastes` registra la comparación con 120 datos obtenidos por otro formato oficial del BCRP y 58 tasas recalculadas desde los Stata. Los eventos `archivo` contienen el SHA-256 de cada producto. Para archivos de texto, sha256_lf permite contrastar el contenido aun si Git convierte los finales de línea. El agregado, la validación y las cuatro imágenes de ENAHO coincidieron byte por byte con los archivos existentes. Se reutilizaron. El Parquet sigue siendo un archivo local excluido por Git.
5. `fin` registra el resultado de la ejecución. El informe y las tres frases comprobadas se pueden abrir en [informe_final.md](../../informes/informe_final.md) y [verificacion_cifras.md](../../informes/verificacion_cifras.md).

## Contraste con la fase anterior

| Indicador | Fase anterior | Recalculado |
| --- | ---: | ---: |
| Residentes habituales | 108 664 | 108 664 |
| Pobreza nacional con `facpob07` | 27,528733 % | 27,528733 % |
| Pobreza nacional con Sumaria | 27,579468 % | 27,579468 % |
| Pobreza urbana con Sumaria | 24,806989 % | 24,806989 % |
| Pobreza rural con Sumaria | 39,302794 % | 39,302794 % |
| Ámbitos territoriales del mapa | 25 | 25 |

[Validación ENAHO](../../salidas/validacion.txt) · [Indicadores](../../salidas/indicadores.csv) · [Ejecución de la fase anterior](../skills/03_ejecucion_enaho.txt).

## Fallos, correcciones y regresión

- Se provocó un fallo de entrada con un directorio de datos vacío y `--sin-descarga`. El script real de limpieza retornó 1 y escribió `Estado: RECHAZADO`. El coordinador bloqueó el gráfico y el mapa. La regresión `test_limpieza_real_fallida_bloquea_grafico_y_mapa` repite el caso. [Traza del fallo controlado](limpieza_fallida.jsonl) · [Pruebas de integración](../../tests/test_integracion.py).
- En la primera ejecución el intérprete avisó de escapes innecesarios en el Markdown generado. Se corrigió el generador y se repitió el flujo con un lote vacío. Para reproducir el fallo controlado en la terminal restringida se usó la caché de `uv` del proyecto tras un error de permisos en la caché predeterminada.
- Pytest pasó 40 casos. Incluye las 8 pruebas originales del docente, las 2 pruebas MCP propias, las 27 pruebas ENAHO y 3 pruebas nuevas de coordinación. [Salida real de Pytest](pytest.txt).
- El archivo de [conversación de Codex](conversacion_codex.jsonl) es un extracto literal del intercambio visible de esta fase hasta el momento de la exportación. La bitácora y las respuestas MCP guardan la evidencia de herramientas por separado.

## Claude Code

En este entorno `claude` no estaba disponible en el PATH y no se dispuso de una sesión autenticada. La evidencia anterior acredita el flujo Codex + FastMCP y las Skills por CLI. Queda pendiente la demostración de orquestación en el cliente Claude Code exigida en la Parte 3. [Procedimiento para reproducir y exportar la sesión nativa](claude_code.md) · [Rúbrica](https://github.com/d2cml-ai/Data-Science-Python/issues/201).
