# Plan y matriz de cumplimiento

Estado al preparar la rama: solo estructura, configuración y ocho pruebas originales copiadas de la Sesión 04. Las rutas de resultados de esta matriz son **entregables futuros**; ninguna puntuación está acreditada aún. Fuentes: [Issue #201](https://github.com/d2cml-ai/Data-Science-Python/issues/201), [proyecto de Sesión 04](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/04-mcp-claude-code/proyecto) y [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho).

## Matriz de la rúbrica: 20 puntos

| Criterio | Pts | Archivos requeridos | Prueba o evidencia verificable |
|---|---:|---|---|
| MCP: búsqueda, consulta y resumen | 2.0 | `mcp/server.py`, `.mcp.json` | Llamadas reales con código, período, fuente; pruebas originales |
| MCP: herramienta propia | 1.0 | `mcp/server.py`, `mcp/test_herramienta_propia.py` | Función distinta de búsqueda/consulta/resumen y dos pruebas propias |
| MCP: recurso, prompt y Claude Code | 1.0 | `mcp/server.py`, `.mcp.json`, `evidencias_ia/mcp/` | Listado e invocación de recurso y prompt desde el cliente; transcript completo |
| MCP: 10 pruebas | 1.0 | `mcp/test_server.py` (8 originales), `mcp/test_herramienta_propia.py` (2 nuevas) | Salida de `uv run pytest -q mcp/` con 10 pruebas aprobadas; conservar las 8 originales |
| ENAHO: limpieza, ponderación y validación | 2.5 | `.claude/skills/limpiando-enaho/SKILL.md`, `reference.md`, `scripts/limpiar.py`, `salidas/validacion.txt` | 108,664 residentes, pobreza nacional a ≤0.1 pp de 27.6 %, unión m:1 sin duplicados, factores documentados |
| ENAHO: gráficos | 1.5 | `.claude/skills/graficando-enaho/SKILL.md`, `scripts/graficar.py`, `figuras/` | Pobreza ponderada por área, sexo u otro grupo, y departamento; títulos, unidades, período y fuente |
| ENAHO: mapa | 1.5 | `.claude/skills/mapeando-enaho/SKILL.md`, `scripts/mapear.py`, `mapas/` | Unión `ubigeo[:2]` ↔ `FIRST_IDDP`; 25/25, Lima y Callao separados; comparación con CSV de Sesión 16 |
| Skills: activación y coordinación | 0.5 | Tres `SKILL.md`, `evidencias_ia/skills/` | Invocación individual y pedido en lenguaje natural que active limpieza antes de gráfico/mapa |
| Pregunta y plan coherente | 0.5 | `README.md`, `informes/informe_final.md` | Pregunta que exige BCRP y ENAHO; plan registrado antes de ejecutar |
| Orquestación real | 2.0 | `evidencias_ia/integracion/` | Una ejecución de Claude Code con ≥2 herramientas MCP distintas y ≥2 Skills distintas, sin copiar resultados manualmente |
| Informe, tres hallazgos y visualizaciones | 1.5 | `informes/informe_final.md`, `figuras/`, `mapas/` | ≥3 hallazgos sustentados; gráfico BCRP, gráfico ENAHO, mapa; interpretación y limitaciones |
| Verificación de cifras y errores | 1.0 | `informes/verificacion_cifras.md` | ≥3 afirmaciones verificadas manualmente entre ambas fuentes; registrar diferencias y fallos |
| Diez preguntas y verdad verificable | 1.0 | `evaluacion/preguntas.csv` | 4 BCRP + 4 ENAHO + 2 mixtas; fuente/cálculo independiente y tolerancia fijados antes del experimento |
| Experimento A/B | 1.5 | `evaluacion/resultados.csv`, `evidencias_ia/evaluacion/` | Las mismas 10 preguntas en ambos modos, sesiones independientes, modelo/instrucciones y herramientas registrados |
| Análisis de aciertos, errores, herramientas y tiempo | 0.5 | `evaluacion/comparacion.md` | Correctas, incorrectas, no contestadas, promedio de tiempo, mejoras y empeoramientos |
| README, reproducción y evidencias IA | 1.0 | `README.md`, `uv.lock`, `evidencias_ia/` | Descarga, instalación, comandos, ejemplo completo, límites, salidas y conversaciones completas revisadas |

## Arquitectura y contratos

- **BCRP:** adaptar el starter de Sesión 04 en `mcp/server.py` y mantener `mcp/test_server.py` literalmente, salvo ajuste de importación indispensable. Las cuatro herramientas de la Parte 1 son `buscar_series`, `serie`, `resumen` y `comparar_series`. Exponer la ficha `bcrp://serie/{codigo}` y el prompt `informe`. Para la investigación integrada, seleccionar y documentar en el catálogo el código exacto de inflación de alimentos y generar el gráfico desde las observaciones recuperadas.
- **ENAHO:** `limpiar.py` lee Stata sin perder ceros de las llaves, normaliza columnas, filtra residentes habituales con `((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))`, une `conglome/vivienda/hogar` con `validate="m:1"`, aplica el factor correcto según unidad de análisis, emite Parquet, CSV agregados y validación. Una validación esencial fallida detiene el flujo.
- **Gráficos/mapa:** los scripts consumen salidas validadas, no recalculan con reglas distintas. Las Skills describen cuándo usarlos y llaman primero a limpieza si falta el Parquet. GeoPandas une códigos territoriales como texto y exige cobertura completa.
- **Investigación:** Claude Code usa MCP y Skills en la misma sesión, guarda transcript íntegro, comprueba al menos tres cifras, y redacta el informe desde salidas calculadas. Asociación descriptiva no implica causalidad.
- **Evaluación:** fijar verdad, tolerancia y regla de corrección antes de correr A/B. Modo A sin MCP/Skills ni acceso indirecto a salidas; modo B con ambos. Registrar modelo, configuración, herramientas realmente usadas, respuesta, tiempo y error de cada ejecución.

## Secuencia de implementación para Codex

1. Terminar `mcp/server.py` y agregar exactamente dos pruebas de la herramienta propia. Ejecutar las diez pruebas y conservar la salida íntegra.
2. Implementar `limpiando-enaho` y pruebas de llaves, filtro, ponderación y validación. Obtener los dos módulos del INEI por el procedimiento documentado. No sustituir los datos con referencias.
3. Implementar `graficando-enaho` y `mapeando-enaho`; verificar las tres figuras mínimas, mapa 25/25 y comparación territorial.
4. Generar `uv.lock`, completar README con comandos reales y entregar a Claude Code una versión estable mediante commit. Claude Code ejecuta la investigación integrada y se guarda la conversación completa.
5. Verificar el informe con tres cifras; fijar diez preguntas, verdad y tolerancias; ejecutar 10 sesiones A y 10 B, y analizar resultados observados.
6. Revisar trazabilidad, enlaces y redacción sensible; solo entonces preparar el comentario de entrega del Issue. No implementar dashboard ni extras antes de cubrir la rúbrica.

## Coordinación entre Work, Codex y Claude Code

Work mantiene la matriz, el registro de decisiones y el control de evidencias. Codex es el único editor del código, pruebas, configuración y documentación durante la implementación. Tras un commit de relevo, Claude Code es el operador de la investigación y la evaluación; puede generar salidas e informe, pero cualquier corrección de código vuelve a Codex en un turno separado. Cada relevo registra commit, responsable, archivos asignados y estado. Nunca abrir dos agentes con permiso de escritura sobre los mismos archivos al mismo tiempo. Los resultados de cada modo de evaluación se guardan antes de iniciar el siguiente y no se usan para alterar respuestas esperadas.
