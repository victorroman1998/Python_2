# Reproducir la integración nativa con Claude Code

La demostración nativa está pendiente. Este procedimiento requiere Claude Code instalado y autenticado, `uv` y acceso HTTPS a BCRPData, INEI y el repositorio del curso.

1. Clona la rama en un directorio nuevo para comenzar sin el Parquet. Entra en `tarea_4/`, donde se encuentran `.mcp.json` y `.claude/skills/`.

   ```bash
   git clone --single-branch --branch codex/tarea-4-agente-socioeconomico https://github.com/victorroman1998/Python_2.git Python_2-claude
   cd Python_2-claude/tarea_4
   uv sync --locked --python 3.12
   claude auth status --text
   claude
   ```

2. Si la cuenta requiere acceso, usa `claude auth login`. Acepta el servidor de proyecto `bcrp` y comprueba en `/mcp` que se conectó y expone las herramientas. Comprueba que Claude reconoce `/limpiando-enaho`, `/graficando-enaho` y `/mapeando-enaho` al escribir sus nombres en el menú. [MCP de Claude Code](https://code.claude.com/docs/en/mcp) · [Skills de Claude Code](https://code.claude.com/docs/en/skills).

3. Envía el siguiente pedido como un solo mensaje. Autoriza los comandos de los scripts cuando el cliente los solicite.

   > Responde esta pregunta en una sola investigación. ¿Cómo evolucionó la inflación de alimentos y bebidas en Lima Metropolitana entre 2020 y 2024, y qué diferencias por área de residencia, sexo y departamento presentó la pobreza monetaria en el Perú en 2024? Registra el plan primero. Usa las herramientas nativas del MCP `bcrp`: `buscar_series` para identificar el par de IPC interanual, `serie` y `resumen` de 2020-01 a 2024-12 y `comparar_series` para comprobar los 60 pares. Guarda los argumentos, las fichas y los resultados en archivos de la investigación. Activa las Skills del proyecto: detecta el Parquet ausente, usa `limpiando-enaho` y, si aprueba, usa `graficando-enaho` y `mapeando-enaho` con el mismo lote. Usa las respuestas obtenidas en esta sesión y los agregados ENAHO para generar una figura temporal, un informe descriptivo y tres contrastes de cifras. Usa los scripts y el plan de la Fase 3 como referencias. La traza debe mostrar las invocaciones MCP nativas y la activación de las Skills. Si falla un componente, deja constancia del error.

4. Revisa que el historial de esa misma sesión muestre al menos dos nombres de herramienta `mcp__bcrp__...` con sus resultados y al menos dos Skills utilizadas con sus comandos y salidas. Conserva la conversación completa y la traza de herramientas que acompaña la ejecución. Si la exportación de texto no muestra el detalle de herramientas, adjunta el JSONL de la sesión o capturas de los resultados expandidos en orden. Guarda la copia revisada en `evidencias_ia/integracion/`. Oculta credenciales, datos individuales y rutas privadas antes de publicar. [Modo interactivo](https://code.claude.com/docs/en/interactive-mode) · [Referencia de CLI](https://code.claude.com/docs/en/cli-reference).

El comando `scripts/investigar.py` reproduce el cálculo de referencia con FastMCP. Para acreditar la ejecución nativa, la conversación debe mostrar las llamadas y las Skills gestionadas por Claude Code en el flujo que genera su informe.
