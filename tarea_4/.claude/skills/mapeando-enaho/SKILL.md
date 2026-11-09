---
name: mapeando-enaho
description: Elabora un mapa coroplético de pobreza monetaria departamental de ENAHO 2024. Úsala para representar la distribución territorial de las tasas del INEI en los 25 ámbitos del Perú.
---

# Mapear la pobreza departamental de ENAHO 2024

Desde `tarea_4/`, si falta `salidas/personas_2024.parquet`, `salidas/indicadores.csv` o el estado de `salidas/validacion.txt` es distinto de `APROBADO`, ejecuta primero [limpiando-enaho](../limpiando-enaho/SKILL.md). Si el mapeador detecta un lote alterado, repite la limpieza. Continúa solo con la validación aprobada.

```bash
uv run --locked python .claude/skills/mapeando-enaho/scripts/mapear.py
```

El script obtiene el GeoJSON del curso si falta. Añade `--sin-descarga` para trabajar con [los insumos locales](../../../datos/README.md). Se comprueban la referencia departamental y la unión por `ubigeo[:2]` con `FIRST_IDDP`. Si falla un contraste o la geometría, informa el error y detén el mapa.

Entrega `mapas/pobreza_departamento_2024.png` con 25 ámbitos, incluidos Lima y Callao como unidades separadas. Los colores usan el estimador de residentes con `facpob07`.
