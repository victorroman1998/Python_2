# Evidencias de uso de IA: inventario y límites

Este directorio distingue transcripciones de sesiones, bitácoras de herramientas y resúmenes. Una bitácora de ejecución o un resumen no equivale a la conversación completa que solicita la rúbrica. No se ha reconstruido ningún historial faltante.

| Etapa | Evidencia publicada | Alcance comprobable | Historial pendiente |
| --- | --- | --- | --- |
| Preparación con Work | [Plan de implementación](../PLAN_IMPLEMENTACION.md) | Plan y decisiones documentadas; no es una exportación conversacional | Conversación completa de preparación con Work |
| Desarrollo MCP con Codex | [Validación MCP](mcp/validacion.md), [verificador stdio](mcp/verificar_stdio.py) | Pruebas, conexión y resultados técnicos; la prueba conversacional de Claude Code terminó sin iniciar sesión | Conversación completa de desarrollo MCP con Codex y sesión autenticada de Claude Code |
| Construcción de Skills | [Extracto de conversación Codex](skills/06_conversacion_codex.md), [ejecución ENAHO](skills/03_ejecucion_enaho.txt), [pruebas](skills/01_pytest_enaho.txt) | El extracto se cortó durante el turno; los registros técnicos muestran validaciones y pruebas | Cierre y exportación completa de la conversación de Skills |
| Integración del agente | [Extracto de conversación Codex](integracion/conversacion_codex.jsonl), [bitácora de ejecución](integracion/ejecucion_codex.jsonl), [índice de integración](integracion/README.md) | La bitácora registra MCP y tres scripts de Skills en una ejecución desde Codex | Conversación completa de la fase y orquestación nativa autenticada en Claude Code |
| Evaluación experimental | [20 transcripciones Codex CLI](evaluacion/README.md), [resultados](../evaluacion/resultados.csv) | Diez sesiones A y diez B con eventos de CLI, instrucciones, respuestas, herramientas y tiempos | Conversaciones de diseño y revisión del experimento fuera de esas veinte sesiones, si se usaron |
| Correcciones y pruebas | [Pruebas de Skills](skills/), [pruebas de integración](integracion/pytest.txt), [pruebas de evaluación](evaluacion/pytest.txt) | Salidas de terminal y regresión; no constituyen conversaciones completas | Historial conversacional completo de las correcciones |

Las [limitaciones de la demostración Claude Code](integracion/claude_code.md) se documentan por separado. El experimento A/B se realizó con Codex CLI, no con Claude Code. La ausencia de los historiales indicados puede afectar el criterio de evidencias de IA y no se debe presentar como cumplido.

## Protocolo para completar evidencias existentes

Si aún se dispone de una conversación original, exportarla completa a Markdown, TXT, JSON o HTML, o capturar todas sus pantallas legibles en orden. Registrar fecha y hora de Perú, plataforma, fase y commit asociado. Conservar el original privado antes de redactar la copia pública. Ocultar tokens, contraseñas, rutas privadas, identificadores personales y contenido confidencial, señalando cada redacción. No reconstruir mensajes a partir de resúmenes o bitácoras.
