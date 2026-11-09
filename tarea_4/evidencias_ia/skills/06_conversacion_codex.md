# Conversación de Codex · implementación de Skills ENAHO

Exportación de los mensajes visibles disponibles en el registro local el 8 de noviembre de 2026. El corte se hizo durante el turno, antes del cierre y la publicación. Los mensajes conservan el texto original y la hora UTC del registro. La exportación excluye metadatos del entorno, contenido interno y binarios de herramientas. Las salidas de terminal se guardan aparte.

- [Pruebas ENAHO](01_pytest_enaho.txt)
- [Pruebas MCP](02_pytest_mcp.txt)
- [Ejecución con fuentes oficiales y comprobaciones](03_ejecucion_enaho.txt)
- [Dependencias y frontmatter](04_dependencias_y_frontmatter.txt)
- [Incidencias de terminal](05_incidencias_terminal.txt)

## Usuario · 2026-11-09T03:05:50.984Z

# TAREA 4 — FASE 2: IMPLEMENTACIÓN Y VALIDACIÓN DE SKILLS ENAHO 2024

Actúa como ingeniero senior de Python, científico de datos especializado en encuestas poblacionales complejas y analista geoespacial.

Tu responsabilidad es implementar, ejecutar y verificar la Parte 2 de la Tarea 4 del Diplomado en Data Science, correspondiente al procesamiento y análisis de ENAHO 2024 (6 puntos).

## 1. CONTEXTO DEL PROYECTO

Repositorio:

https://github.com/victorroman1998/Python_2

Rama de trabajo:

`codex/tarea-4-agente-socioeconomico`

Directorio:

`tarea_4/`

Commit de partida:

`814e9cd7541c07126ac7952070ae444279a1fe13`

La Parte 1 ya implementó el servidor MCP del BCRP y documentó diez pruebas Pytest aprobadas.

Antes de desarrollar, revisa los archivos existentes, especialmente:

- `PLAN_IMPLEMENTACION.md`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `.claude/`
- `mcp/`

No recrees el proyecto ni alteres las tareas anteriores.

## 2. REFERENCIAS OBLIGATORIAS

Enunciado oficial y rúbrica:

https://github.com/d2cml-ai/Data-Science-Python/issues/201

Sesión 16, Skills ENAHO:

https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho

Fuentes:

Módulo 34, Sumaria:
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip

Módulo 02, Miembros:
https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip

GeoJSON:
https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson

Referencia departamental:
https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv

Lee los materiales antes de implementar. Los valores de referencia sirven para validar, nunca para reemplazar cálculos reales.

## 3. OBJETIVO PRINCIPAL

Implementa tres Skills reutilizables:

1. `limpiando-enaho`
2. `graficando-enaho`
3. `mapeando-enaho`

Cada Skill debe contener un archivo `SKILL.md` correctamente estructurado y scripts funcionales en Python.

Aunque Codex será el desarrollador principal, conserva la estructura `.claude/skills/` exigida por el docente. Los scripts también deben poder ejecutarse directamente mediante `uv`, sin depender de un proveedor específico de IA.

Las tres Skills deben compartir una misma base de datos procesada y validada.

## 4. SKILL 1: LIMPIANDO ENAHO

Implementa:

`.claude/skills/limpiando-enaho/`

Incluye:

- `SKILL.md`
- `reference.md`
- `scripts/limpiar.py`

### 4.1. Lectura de microdatos

Descarga los módulos 34 y 02 de ENAHO 2024 cuando el entorno permita acceso de red.

Extrae y lee los archivos Stata correspondientes.

Utiliza Pandas y PyArrow.

Preserva correctamente los identificadores:

- `conglome`
- `vivienda`
- `hogar`
- `codperso`
- `ubigeo`

Evita pérdidas de ceros iniciales y cambios de tipos que alteren las uniones.

Normaliza los nombres de las variables, incluidos caracteres especiales.

Comprueba los nombres, categorías y tipos reales de las variables antes de aplicar transformaciones.

### 4.2. Selección de residentes habituales

Aplica la condición de la sesión:

```python
((p204 == 1) & (p205 == 2)) | ((p204 == 2) & (p206 == 1))
```

Verifica que el número resultante sea 108,664 residentes habituales.

Documenta el conteo antes y después del filtrado.

### 4.3. Unión de datos

Integra personas con la base de hogares utilizando:

`conglome`, `vivienda` y `hogar`.

Utiliza `merge(..., validate="m:1")`.

Verifica:

- Unicidad de hogares en la base de la derecha.
- Unicidad de personas mediante la llave completa.
- Cantidad de registros antes y después.
- Ausencia de multiplicaciones inesperadas.
- Ausencia de registros sin correspondencia, o explicación documentada si existen.

No permitas uniones silenciosamente incorrectas.

### 4.4. Indicadores y ponderación

Construye las variables necesarias para calcular:

- Pobreza monetaria nacional.
- Pobreza urbana y rural.
- Pobreza por sexo.
- Pobreza por departamento.
- Identificación territorial de los 25 ámbitos.

Utiliza la clasificación oficial de pobreza de ENAHO y las reglas de la sesión 16.

Identifica correctamente los códigos de sexo y área de residencia mediante la documentación.

Para estimaciones individuales, utiliza `facpob07` según la metodología de la sesión.

Cuando corresponda trabajar con hogares, distingue `factor07` y la multiplicación por miembros del hogar para estimaciones poblacionales. No mezcles unidades de análisis ni factores incompatibles.

Calcula proporciones mediante:

`sum(peso * indicador) / sum(peso)`

Documenta el denominador y la población de referencia de cada estimador.

No utilices promedios simples cuando corresponda ponderación.

### 4.5. Validación estadística

Contrasta los resultados con:

- Pobreza nacional: aproximadamente 27.6 %.
- Tolerancia máxima nacional: 0.1 puntos porcentuales.
- Residentes habituales: 108,664.
- Pobreza urbana: aproximadamente 24.8 %.
- Pobreza rural: aproximadamente 39.3 %.
- Unidades territoriales: 25.

Compara también las tasas departamentales con el archivo oficial de referencia proporcionado en la sesión 16.

Reporta diferencias absolutas, tolerancias y resultados de cada validación.

Si alguna validación crítica falla, investiga la causa.

No corrijas artificialmente estimaciones, factores o registros para obtener coincidencias.

Implementa una política de errores que impida utilizar salidas inválidas en las otras Skills.

### 4.6. Productos

Genera:

- `salidas/personas_2024.parquet`
- `salidas/indicadores.csv`
- `salidas/validacion.txt`

El archivo de validación debe indicar las comprobaciones realizadas, resultados y estado de aprobación.

Los indicadores deben obtenerse desde los microdatos reales.

## 5. SKILL 2: GRAFICANDO ENAHO

Implementa:

`.claude/skills/graficando-enaho/`

Incluye:

- `SKILL.md`
- `scripts/graficar.py`

La Skill debe consumir la base validada que produce la Skill de limpieza.

Genera tres gráficos como mínimo:

1. Pobreza monetaria según residencia urbana y rural.
2. Pobreza monetaria por sexo.
3. Pobreza monetaria por departamento.

Requisitos:

- Utilizar estimaciones ponderadas.
- Mostrar valores calculados, no constantes.
- Incluir título analítico y período.
- Mostrar porcentaje y fuente.
- Emplear ejes apropiados y escalas legibles.
- Preferir barras ordenadas para las comparaciones territoriales.
- Evitar efectos tridimensionales o elementos decorativos innecesarios.
- Exportar figuras con resolución mínima de 200 dpi.
- Mantener consistencia de fuentes y estilo entre gráficos.

Utiliza Matplotlib.

Almacena los archivos en `figuras/`, utilizando nombres descriptivos y consistentes.

Comprueba que las cifras de los gráficos coincidan con `salidas/indicadores.csv`.

## 6. SKILL 3: MAPEANDO ENAHO

Implementa:

`.claude/skills/mapeando-enaho/`

Incluye:

- `SKILL.md`
- `scripts/mapear.py`

Construye un mapa coroplético de pobreza monetaria departamental en 2024.

Requisitos:

- Utilizar GeoPandas.
- Leer el GeoJSON proporcionado por el curso.
- Unir indicadores mediante `ubigeo[:2]` y `FIRST_IDDP`.
- Normalizar identificadores a dos caracteres.
- Verificar exactamente 25 unidades territoriales.
- Conservar Lima y Callao separados.
- Detectar duplicaciones, geometrías inválidas y datos faltantes.
- Rechazar uniones exclusivamente por nombres.
- Comparar tasas departamentales con la referencia oficial de la sesión 16.

Diseño:

- Mapa legible, de alta resolución.
- Escala cromática secuencial apropiada para porcentajes.
- Leyenda clara con unidad de medida.
- Límites territoriales finos.
- Fondo limpio.
- Fuente identificada.
- Sin distorsionar los valores ni la distribución territorial.

Exporta:

`mapas/pobreza_departamento_2024.png`

El mapa debe representar tasas ponderadas obtenidas de los datos reales.

## 7. COORDINACIÓN ENTRE SKILLS

Configura correctamente los archivos `SKILL.md` con frontmatter YAML válido.

Las descripciones deben permitir que un agente identifique qué Skill utilizar ante solicitudes como:

- "Limpia la ENAHO 2024 y calcula la pobreza nacional".
- "Grafica la pobreza urbana y rural".
- "Elabora un mapa de pobreza por departamento".

Implementa dependencias explícitas:

Si `salidas/personas_2024.parquet` no existe o la validación no es satisfactoria, las Skills de gráficos y mapas deben ejecutar primero el procesamiento o indicar claramente la dependencia pendiente.

No deben continuar sobre datos inválidos.

Comprueba que los scripts puedan ejecutarse desde `tarea_4/` mediante comandos de `uv`.

No sustituyas las Skills por simples documentos explicativos.

## 8. PRUEBAS AUTOMATIZADAS Y CONTROL DE CALIDAD

Implementa pruebas para:

- Unicidad de identificadores.
- Integridad de las uniones.
- Filtrado de residentes habituales.
- Ponderación correcta.
- Cálculo de pobreza.
- Normalización territorial.
- Integración de datos geográficos.
- Detección de datos faltantes.
- Comportamiento ante entradas inválidas.

Puedes utilizar datos sintéticos controlados únicamente en pruebas unitarias.

Los resultados definitivos de ENAHO deben proceder exclusivamente de los microdatos oficiales.

Ejecuta las pruebas nuevas y vuelve a ejecutar las diez pruebas MCP anteriores para detectar regresiones.

Registra todas las verificaciones reales.

## 9. DEPENDENCIAS Y VERSIONAMIENTO

Conserva la configuración existente de `uv`.

Actualiza `pyproject.toml` únicamente si resulta necesario.

Regenera `uv.lock` cuando cambien las dependencias.

No modifiques innecesariamente `mcp/server.py` ni las pruebas aprobadas de la Parte 1.

No publiques los archivos originales de microdatos, cachés pesadas, credenciales ni información sensible.

Actualiza `.gitignore` según corresponda.

Utiliza nombres de archivos y rutas portables.

## 10. EVIDENCIAS Y DOCUMENTACIÓN

Documenta en el README:

- Cómo descargar los datos oficiales.
- Cómo preparar el entorno.
- Cómo ejecutar las tres Skills.
- Cómo reproducir los indicadores.
- Cómo generar gráficos y mapa.
- Cómo ejecutar las pruebas.
- Cómo interpretar los resultados de validación.

Conserva en `evidencias_ia/skills/` los registros completos disponibles de desarrollo, ejecución, errores y correcciones, con información sensible depurada.

No presentes resúmenes creados por IA como sustitutos de transcripciones reales.

## 11. RESTRICCIONES

- No alteres las entregas anteriores del repositorio.
- No modifiques resultados para coincidir con las referencias.
- No inventes registros, cifras o pruebas.
- No afirmes que se activaron Skills mediante Claude Code si la ejecución se realizó exclusivamente con Codex.
- No declares completada una validación sin haber ejecutado los scripts.
- No construyas un dashboard ni funcionalidades opcionales en esta etapa.
- No desarrolles todavía el informe final ni el experimento comparativo de diez preguntas.

Prioriza que los tres componentes funcionen y produzcan resultados consistentes.

## 12. CRITERIOS DE ACEPTACIÓN

La fase estará técnicamente terminada cuando:

1. Existan las tres Skills con sus scripts funcionales.
2. Se hayan procesado los módulos oficiales 34 y 02.
3. La base de residentes habituales esté validada.
4. Las estimaciones de pobreza estén correctamente ponderadas.
5. La pobreza nacional cumpla la tolerancia de la rúbrica.
6. Los tres gráficos solicitados estén generados.
7. El mapa contenga las 25 unidades territoriales.
8. Lima y Callao se representen separadamente.
9. Las pruebas automatizadas nuevas y las anteriores se ejecuten satisfactoriamente.
10. Los resultados puedan reproducirse con instrucciones documentadas.

## 13. ENTREGA DE CODEX

Trabaja directamente sobre la rama de desarrollo existente.

Completa la implementación, ejecuta el procesamiento y publica los cambios mediante commits descriptivos.

Al finalizar, proporciona:

- Commit SHA.
- Archivos creados y modificados.
- Cantidad de pruebas aprobadas y fallidas.
- Pobreza nacional calculada.
- Pobreza urbana y rural.
- Número de residentes habituales.
- Número de unidades territoriales procesadas.
- Gráficos y mapa generados.
- Comparación con las referencias oficiales.
- Incidencias encontradas y correcciones realizadas.
- Requisitos pendientes para la integración del agente.

Distingue claramente entre resultados efectivamente comprobados y verificaciones pendientes.

No solicites confirmaciones intermedias para decisiones técnicas ordinarias. Aplica las soluciones más sencillas, documentadas y compatibles con la rúbrica.

Nuestro objetivo es una implementación reproducible, metodológicamente válida y lista para la fase de integración.

## Codex · 2026-11-09T03:05:53.660Z

Voy a revisar la rama, la rúbrica y los materiales de la sesión 16 antes de implementar. Aplicaré la guía de creación de Skills para estructurar los tres `SKILL.md` en `.claude/skills/` y verificaré los scripts con los microdatos oficiales.

## Codex · 2026-11-09T03:07:27.445Z

Los ZIP oficiales ya están disponibles. La inspección encontró 108 664 residentes habituales y ninguna persona sin hogar correspondiente. También confirmé que el CSV departamental coincide al redondear con la estimación de Sumaria. Los gráficos y el mapa usarán `facpob07` y la validación mostrará ambas estimaciones por separado. [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho)

## Codex · 2026-11-09T03:12:02.089Z

La limpieza aprobó el contraste nacional con 27,5287 %, a 0,0713 puntos porcentuales del 27,6 % de referencia. Ya se generaron los tres gráficos y el mapa, y las diez pruebas MCP volvieron a pasar. Estoy verificando que las visualizaciones usen las cifras del CSV y que los scripts rechacen salidas incompletas o alteradas.

## Codex · 2026-11-09T03:17:04.518Z

Recalculé las 30 tasas del CSV desde el Parquet y comprobé que coinciden con las barras y los colores del mapa. Los cuatro PNG quedaron a 250 dpi. La diferencia entre estimadores se explica por los conteos de miembros y residentes, que difieren en 1 846 hogares aun con la unión completa.
