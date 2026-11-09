---
name: graficando-enaho
description: Grafica la pobreza monetaria ponderada de ENAHO 2024 por residencia urbana y rural, sexo o departamento. Úsala para visualizar o comparar tasas con gráficos de barras.
---

# Graficar la pobreza de ENAHO 2024

Trabaja desde `tarea_4/`. Si falta `salidas/personas_2024.parquet`, `salidas/indicadores.csv` o el estado de `salidas/validacion.txt` es distinto de `APROBADO`, ejecuta primero [limpiando-enaho](../limpiando-enaho/SKILL.md). Continúa solo si aprueba. Si el graficador detecta que un archivo cambió, vuelve a generar el lote con la misma Skill.

```bash
uv run --locked python .claude/skills/graficando-enaho/scripts/graficar.py
```

Para un pedido específico, añade `--grupo area`, `--grupo sexo` o `--grupo departamento`. Presenta el PNG correspondiente de `figuras/` y, si citas un valor, léelo de `salidas/indicadores.csv` con `metodo=personas`. Los porcentajes son estimaciones ponderadas para residentes habituales de 2024.
