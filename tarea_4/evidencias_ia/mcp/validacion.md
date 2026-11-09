# Validación de la Parte 1

Ejecución del 8 de noviembre de 2026, hora de Lima, con Python 3.12.15, uv 0.12.23, FastMCP 4.1.6, Pytest 9.2.0 y Claude Code 2.1.319. Ejecutar los comandos desde `tarea_4/`.

## Pytest

```text
$ uv run --locked pytest -q mcp/
..........                                                               [100%]
10 passed in 6.04s
```

La última ejecución descargó el catálogo oficial con la caché local vacía. El blob Git de `mcp/test_server.py` coincide con el original de la sesión 04 (`1d0316861e999d9484f4306e38d47347bb803958`). Las dos pruebas de `mcp/test_herramienta_propia.py` usan respuestas controladas para reproducir un faltante explícito, un periodo ausente y una mezcla de frecuencias. [Pruebas de la sesión 04](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/04-mcp-claude-code/proyecto/test_server.py)

## Verificación por stdio y contraste independiente

```text
$ uv run --locked python evidencias_ia/mcp/verificar_stdio.py
Herramientas: buscar_series, comparar_series, resumen, serie
Recurso y plantilla: bcrp://catalogo, bcrp://serie/{codigo}
Prompt: informe
Recurso, ficha PN01273PM y prompt leídos por stdio.
PN01271PM marzo 2025: 0.810159321766145 (https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01271PM/json/2025-1/2025-12)
PD04638PD 15/10/2026: 3.42821428571429; 08/10/2026: n.d. (https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04638PD/json/2026-10-01/2026-10-15)
PN01273PM diciembre 2025: 1.50879973918667; septiembre 2026: 4.54865469481509 (https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2025-12/2026-9)
Comparación mensual de 2025: 12 pares verificados (https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2025-1/2025-12)
Normalización trimestral y anual verificada (https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN02538AQ/json/2000-1/2000-2, https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04746FA/json/2019/2020).
```

La verificación terminó con código 0. Arrancó el comando de `.mcp.json` en un subproceso y consultó por separado las URL oficiales para contrastar las salidas de `serie`, `resumen` y `comparar_series`.

## Claude Code

Un perfil temporal aprobó solo el servidor de proyecto `bcrp` mediante un archivo de ajustes con `{"enabledMcpjsonServers":["bcrp"]}`. La CLI confirmó la conexión.

```text
$ claude --settings <ajustes-temporales.json> mcp get bcrp
bcrp:
  Scope: Project config (shared via .mcp.json)
  Status: √ Connected
  Type: stdio
  Command: uv
  Args: run --locked python mcp/server.py
```

El control local `mcp_status` devolvió estado `connected` y las cuatro herramientas `buscar_series`, `comparar_series`, `resumen` y `serie`. El evento `commands_changed` incluyó `bcrp:informe (MCP)`. Una traza local del servidor registró los métodos que envió Claude Code.

```text
server/discover
prompts/list
resources/list
tools/list
```

La negociación del protocolo MCP 2026-07-28 registró `hasTools`, `hasPrompts` y `hasResources` en `true`. El verificador de la sección anterior recuperó el contenido del prompt y de los recursos por stdio.

La prueba conversacional en el perfil temporal terminó con `Not logged in · Please run /login`. Para completar esa comprobación, iniciar sesión en Claude Code, aprobar `bcrp` y ejecutar el ejemplo del README. [Guía MCP de Claude Code](https://code.claude.com/docs/en/mcp)

## Incidencias

- El terminal restringido no resolvía los dominios de GitHub ni BCRPData. El acceso de red autorizado permitió trabajar en el checkout de la rama publicada y ejecutar las pruebas contra las fuentes oficiales.
- El catálogo oficial llegó en Latin-1 pese a declarar UTF-8. El servidor lo decodifica y persiste una copia en UTF-8.
- Las consultas exitosas pueden traer JSON bajo una cabecera `text/html`. Durante la primera verificación directa, el cuerpo de una respuesta con estado 200 tampoco era JSON válido. Se añadieron reintentos acotados y se repitió la verificación hasta obtener una ejecución completa con cifras oficiales.
