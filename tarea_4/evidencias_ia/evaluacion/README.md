# Evidencias de la evaluación

Los archivos `A-Q01.jsonl` a `A-Q10.jsonl` y `B-Q01.jsonl` a `B-Q10.jsonl` son las trazas de los procesos de Codex CLI. Cada archivo empieza con la instrucción completa, la configuración y el inventario SHA-256 de la carpeta antes de ejecutar. Le siguen los eventos emitidos por la CLI y un registro de cierre con respuesta final, identificador, tiempo, código de salida y stderr. La exportación conserva las salidas que la CLI entrega y sustituye las rutas privadas por marcadores. Los enlaces a rutas de sesión que aparecen dentro de las respuestas documentan cómo se consultaron los insumos o resultados transitorios de esa sesión.

- [Orden, versión y configuración general del lote](lote.json).
- [Prueba directa del aislamiento A](A-aislamiento.json) y [prueba directa del aislamiento B](B-aislamiento.json).
- [Control inicial que el agente declinó ejecutar](A-control-inicial.jsonl), [control de terminal A](A-control.jsonl) y [control de terminal, MCP y Skills B](B-control.jsonl). Estos controles son externos a las veinte preguntas.
- [Reconstrucción de referencias](referencias.txt) y [salida real de Pytest](pytest.txt).
- [Criterios de corrección y patrón](../../evaluacion/) y [resultados con enlaces a cada sesión](../../evaluacion/resultados.csv).

Los ZIP oficiales, el entorno temporal y los Parquet generados se mantienen locales. Las trazas corresponden a Codex. La comprobación nativa con Claude Code permanece pendiente.
