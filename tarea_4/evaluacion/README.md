# Protocolo de evaluación pendiente

Crear `preguntas.csv` con 10 preguntas verificables (4 BCRP, 4 ENAHO y 2 mixtas), respuesta esperada, unidad, fuente/procedimiento y tolerancia. Validar y fijar ese archivo en un commit **antes** de observar respuestas del agente. Para las mixtas, fijar criterios separados de exactitud e interpretación.

Ejecutar cada pregunta en una sesión independiente: A sin MCP ni Skills ni archivos de respuestas calculadas; B con MCP y Skills. Mantener modelo e instrucciones equivalentes y documentar otras herramientas disponibles. En `resultados.csv` registrar pregunta, modo, respuesta generada, fuente, herramientas efectivamente usadas, corrección, tiempo y errores. Exportar transcripciones completas a `evidencias_ia/evaluacion/`. Resumir aciertos, errores, tiempo promedio y cambios por pregunta en `comparacion.md`. No hay resultados de este experimento todavía.
