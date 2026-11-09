# Verificación de cifras

Se cotejaron tres frases del [informe](informe_final.md) con cálculos independientes. La diferencia es el valor independiente menos el publicado a dos decimales. El control exige que ambos cálculos sin redondear coincidan con tolerancia absoluta de 0,0000000001 y produzcan el mismo valor publicado.

| Frase exacta | Valor informado | Valor independiente | Diferencia | Resultado |
| --- | ---: | ---: | ---: | --- |
| La inflación interanual de alimentos y bebidas alcanzó su máximo de 13,16 % en febrero de 2023. | 13,16 % | 13,163747366 % | 0,003747366 % | APROBADO |
| La pobreza rural fue 14,71 puntos porcentuales mayor que la urbana. | 14,71 pp | 14,706444512 pp | -0,003555488 pp | APROBADO |
| La incidencia estimada de pobreza monetaria en Cajamarca fue 44,99 %. | 44,99 % | 44,994959870 % | 0,004959870 % | APROBADO |

- **BCRP.** Máximo de 60 valores del CSV oficial. El mes comprobado fue 2023-02. [BCRPData PN09822PM](https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN09822PM/csv/2020-1/2024-12).
- **Área ENAHO.** Tasa de los residentes en estratos 6–8 menos tasa en estratos 1–5, ambas recalculadas desde los Stata.
- **Departamento ENAHO.** Tasa recalculada desde los Stata para residentes con prefijo UBIGEO 06.

El contraste macroeconómico lee el CSV oficial de BCRPData mediante HTTP y compara cada mes con el JSON obtenido por MCP. En ENAHO el verificador vuelve a leer los dos ZIP oficiales, asigna pobreza mediante una tabla de búsqueda de hogares y suma los pesos con `math.fsum`. El cálculo es independiente del Parquet, de la función de estimación de las Skills y del CSV de referencia departamental. El contraste usa los mismos criterios de población y pesos para estimar el mismo indicador. [Módulo 02](https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip) · [Módulo 34](https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip).

Los 120 valores mensuales y las 58 tasas de ENAHO coincidieron antes de redondear. El JSON de contraste conserva los valores, las fuentes y las huellas de los insumos. El script de verificación se ejecuta como parte de `uv run --locked python scripts/investigar.py`. [JSON de contraste](../salidas/contrastes_fase3.json) · [Script de verificación](../scripts/verificar_cifras.py).
