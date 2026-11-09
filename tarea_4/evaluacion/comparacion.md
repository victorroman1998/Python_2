# Fase 4 · Evaluación experimental del agente

El 8 de noviembre de 2026 se ejecutaron **20 sesiones independientes** con Codex CLI 0.167.0-alpha.3.2 y el modelo `gpt-6.1-sol` fijado con `-m`. [Lote ejecutado](../evidencias_ia/evaluacion/lote.json) · [Resultados](resultados.csv)

## Metodología y condiciones

Se emparejaron cuatro preguntas BCRP, cuatro ENAHO y dos mixtas. El patrón se obtuvo de los JSON oficiales y de los Stata originales. Se fijaron las tolerancias, los criterios y el SHA-256 en el commit de prerregistro `20a4312`, antes de enviar las preguntas. Cada sesión recibió la misma instrucción de su par, en una carpeta temporal nueva. El orden se permutó con semilla 20261108, con hasta cuatro sesiones simultáneas y un límite de 360 s por proceso. La medición va desde el lanzamiento de la CLI hasta su salida, incluido el arranque del MCP cuando corresponde. [Protocolo y corrección](README.md) · [Patrón](preguntas.csv) · [Prerregistro](prerregistro.json)

A tuvo PowerShell, Python, las dependencias bloqueadas y los insumos originales. B recibió los mismos insumos y herramientas generales, más el MCP BCRP y las tres Skills. La validación de ENAHO en B requirió además el contraste departamental de Sumaria del curso. En ambos modos se deshabilitaron la búsqueda web, la red de terminal y la configuración personal de Codex. La red del MCP permitió consultar BCRPData en B. Cada sesión arrancó sin salidas previas. El control directo de MXC verificó la denegación de lectura de tres archivos privados en ambos modos y permitió importar pandas. Los controles técnicos precedieron al lote y se excluyeron de los tiempos y aciertos. [Control A](../evidencias_ia/evaluacion/A-aislamiento.json) · [Control B](../evidencias_ia/evaluacion/B-aislamiento.json) · [Conexión B](../evidencias_ia/evaluacion/B-control.jsonl)

Se extrajeron los valores, unidades, fechas, categorías y argumentos de las respuestas completas. Las tolerancias fueron de 0,01 puntos para BCRP y 0,05 puntos para ENAHO, en la escala de las tasas o brechas. Fechas, nombres y conteos exigieron coincidencia exacta tras normalizar el formato. Las mixtas exigieron además traza de las dos fuentes, coberturas e interpretación. Solo una respuesta que cumple todos los componentes aporta un acierto. [Extracción de componentes](revision.json) · [Cálculo de métricas](calificar.py)

## Resultados por condición y pregunta

| Modo | Intentos | Correctas | Incorrectas | Parciales | No contestadas | Media (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 10 | 10 | 0 | 0 | 0 | 81.12 (n=10) |
| B | 10 | 10 | 0 | 0 | 0 | 44.30 (n=10) |

| Pregunta | A | B | Cambio |
| --- | --- | --- | --- |
| Q01 | [correcta](../evidencias_ia/evaluacion/A-Q01.jsonl) (29.98 s). Leyó enero de 2020 en la serie interanual oficial. | [correcta](../evidencias_ia/evaluacion/B-Q01.jsonl) (31.76 s). Consulta nativa y contraste con el índice base. | igual |
| Q02 | [correcta](../evidencias_ia/evaluacion/A-Q02.jsonl) (36.48 s). Máximo y mes verificados sobre los 60 registros. | [correcta](../evidencias_ia/evaluacion/B-Q02.jsonl) (33.71 s). Resumen MCP contrastado con los 60 registros. | igual |
| Q03 | [correcta](../evidencias_ia/evaluacion/A-Q03.jsonl) (30.09 s). Ambas series y resta con signo verificadas. | [correcta](../evidencias_ia/evaluacion/B-Q03.jsonl) (36.06 s). Dos consultas de serie y resta con signo. | igual |
| Q04 | [correcta](../evidencias_ia/evaluacion/A-Q04.jsonl) (41.32 s). Contó 19 meses por encima del umbral estricto. | [correcta](../evidencias_ia/evaluacion/B-Q04.jsonl) (44.01 s). Contó las tasas > 8 y confirmó el resultado con el JSON. | igual |
| Q05 | [correcta](../evidencias_ia/evaluacion/A-Q05.jsonl) (88.84 s). Reconstruyó el universo de residentes y la tasa ponderada. | [correcta](../evidencias_ia/evaluacion/B-Q05.jsonl) (39.88 s). Reprodujo la tasa con los módulos unidos y el peso indicado. | igual |
| Q06 | [correcta](../evidencias_ia/evaluacion/A-Q06.jsonl) (126.42 s). Recalculó ambas áreas y la diferencia desde las sumas ponderadas. | [correcta](../evidencias_ia/evaluacion/B-Q06.jsonl) (39.47 s). Calculó ambas tasas y la brecha desde indicadores nuevos. | igual |
| Q07 | [correcta](../evidencias_ia/evaluacion/A-Q07.jsonl) (125.14 s). Recalculó por sexo y verificó etiquetas, pesos y brecha. | [correcta](../evidencias_ia/evaluacion/B-Q07.jsonl) (53.80 s). Separó sexos por p207 y verificó las sumas de pesos. | igual |
| Q08 | [correcta](../evidencias_ia/evaluacion/A-Q08.jsonl) (93.73 s). Ordenó 25 ámbitos por incidencia ponderada. Identificó los extremos 06 y 11. | [correcta](../evidencias_ia/evaluacion/B-Q08.jsonl) (47.09 s). Calculó los extremos sobre 25 ámbitos y separó Callao. | igual |
| Q09 | [correcta](../evidencias_ia/evaluacion/A-Q09.jsonl) (100.82 s). Calculó ambas cifras desde los insumos. Distinguió geografías, períodos y objeto de medición. | [correcta](../evidencias_ia/evaluacion/B-Q09.jsonl) (58.36 s). Usó ambas fuentes y distinguió coberturas. Corrigió la lectura de la línea de validación. | igual |
| Q10 | [correcta](../evidencias_ia/evaluacion/A-Q10.jsonl) (138.38 s). Calculó ambas cifras y explicó el desajuste de coberturas y la falta de identificación causal. | [correcta](../evidencias_ia/evaluacion/B-Q10.jsonl) (58.91 s). Consultó el pico y calculó la brecha. Explicó la falta de vínculo entre hogares y precios y de control de confusores. | igual |

B redujo el tiempo medio en 36,82 s por pregunta, un 45,4 % respecto de A. B fue más rápido en Q02 y Q05–Q10. A fue más rápido en Q01, Q03 y Q04. En las cuatro preguntas BCRP, el promedio pasó de 34,47 s en A a 36,38 s en B. En las cuatro preguntas ENAHO pasó de 108,53 a 45,06 s. En las dos mixtas pasó de 119,60 a 58,64 s.

## Herramientas y problemas técnicos

- A registró 94 comandos de terminal. Leyó los JSON del BCRP con PowerShell o Python y reconstruyó las tasas desde los Stata del INEI con pandas. El cálculo requirió identificar el universo de residencia, la clave de hogar y los grupos a partir de los archivos y su documentación.
- B registró 69 comandos de terminal y **15 llamadas MCP completadas** en seis sesiones. Invocó `buscar_series` siete veces, `serie` cinco y `resumen` tres. Ejecutó `limpiando-enaho` y comprobó su validación en Q05–Q10. Las Skills de gráficos y mapa se abrieron en el control de B. Las preguntas puntuadas pedían cifras e interpretación, por lo que las ejecuciones de sus scripts se circunscriben a la fase de integración previa. [Ejecución integrada](../evidencias_ia/integracion/README.md)
- Hubo 22 comandos con salida distinta de cero en A y 16 en B. Los errores recurrentes fueron la ausencia de `rg` en la terminal aislada y la búsqueda inicial de `FUENTES.md` fuera de `datos/`. En el control B, `uv` por nombre falló y la ruta absoluta funcionó. En el lote, B usó el Python del entorno bloqueado para ejecutar la Skill. Q09 en B generó las salidas de limpieza, pero el primer comando buscó el estado en la primera línea del archivo. Una segunda lectura confirmó `Estado: APROBADO`. Todas las preguntas produjeron respuesta final. [Control B](../evidencias_ia/evaluacion/B-control.jsonl) · [B-Q09](../evidencias_ia/evaluacion/B-Q09.jsonl)
- El perfil restrictivo requirió MXC en Windows. Un control preliminar de agente se abstuvo de probar la apertura de rutas privadas. Se conservó su traza y la verificación de denegación se ejecutó directamente con `codex sandbox`. [Control preliminar](../evidencias_ia/evaluacion/A-control-inicial.jsonl)

## Alcance de la conclusión

Los dos modos alcanzaron el máximo de exactitud bajo estas condiciones. El paquete MCP y Skills aportó un proceso común de limpieza y validación y un contraste de series en vivo. La reducción de tiempo observada se concentró en ENAHO y en las preguntas mixtas. A también produjo respuestas rastreables porque recibió los mismos archivos originales. La ventaja observada de B se refiere al tiempo y al uso de procedimientos repetibles en este lote.

Se ejecutó una repetición por pregunta y condición. La comparación es descriptiva y no estima la variación entre repeticiones, la mejora en preguntas más difíciles ni los efectos separados del MCP y las Skills. La latencia puede variar por red, concurrencia y cachés. La revisión de componentes textuales se hizo por un único evaluador con las trazas a la vista. La cobertura del experimento se limita a Codex. La evaluación nativa con Claude Code quedó pendiente por falta de un cliente autenticado disponible.

[Evidencias de las sesiones](../evidencias_ia/evaluacion/) · [Regresión y archivos protegidos](../evidencias_ia/evaluacion/pytest.txt)
