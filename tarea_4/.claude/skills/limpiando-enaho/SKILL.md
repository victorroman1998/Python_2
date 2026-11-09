---
name: limpiando-enaho
description: Procesa los módulos oficiales 02 y 34 de ENAHO 2024 y valida las tasas ponderadas. Úsala para limpiar, unir o verificar los microdatos del INEI o calcular la pobreza nacional, urbana, rural, por sexo o departamento.
---

# Limpiar y validar ENAHO 2024

Desde `tarea_4/`, ejecuta

```bash
uv run --locked python .claude/skills/limpiando-enaho/scripts/limpiar.py
```

El script descarga las entradas que falten en `datos/`. Si no hay acceso HTTPS, sigue [las instrucciones de descarga manual](../../../datos/README.md) y añade `--sin-descarga`.

Lee `salidas/validacion.txt` antes de usar cualquier resultado. Si el comando falla o el estado es distinto de `APROBADO`, informa qué comprobación falló y detén el análisis. Conserva los insumos oficiales para poder reproducir la incidencia.

Usa `salidas/indicadores.csv` con `metodo=personas` para responder sobre residentes habituales. La serie `sumaria` es el contraste poblacional desde hogares. El Parquet es local y contiene llaves muestrales. Para interpretar variables, pesos y tolerancias, consulta [reference.md](reference.md).
