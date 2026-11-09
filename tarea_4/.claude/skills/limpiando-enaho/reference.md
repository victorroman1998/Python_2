# ENAHO 2024 · Variables y estimadores

La lectura selecciona exactamente `sumaria-2024.dta` del ZIP 34 y `enaho01-2024-200.dta` del ZIP 02. Los archivos incluyen tablas auxiliares y otra versión de Sumaria. Pandas lee los códigos sin convertir etiquetas a categorías y registra los tipos y las etiquetas originales. La normalización de nombres convierte `aÑo` en `ano`.

| Campo | Regla |
| --- | --- |
| `conglome`, `vivienda`, `hogar` | Llave de hogar. Texto de 6, 3 y 2 caracteres |
| `codperso` | Texto de 2 caracteres. Completa la llave de persona |
| `ubigeo` | Texto de 6 caracteres. Los primeros dos identifican el departamento |
| `p204`, `p205`, `p206` | 1 = sí, 2 = no. Residente si es miembro y no se ausentó 30 días o más, o si no es miembro y estuvo presente 30 días o más. Se comprueban las respuestas obligatorias de cada rama |
| `p207` | 1 = hombre, 2 = mujer |
| `pobreza` | 1 = pobre extremo, 2 = pobre no extremo, 3 = no pobre |
| `estrato` | Urbana 1 a 5, rural 6 a 8, según la Sesión 16 |
| `departamento` | Códigos 01 a 25. Callao (07) y Lima (15) son ámbitos distintos |

El porcentaje es `100 × suma(peso × pobre) / suma(peso)`. Cada suma corresponde al ámbito de la fila. El indicador `pobre` vale 1 para las categorías 1 y 2.

| Método | Observación | Peso | Denominador |
| --- | --- | --- | --- |
| `personas` | Residente habitual del módulo 02 vinculado a Sumaria | `facpob07` | Suma de factores de los residentes del ámbito, incluido sexo |
| `sumaria` | Hogar del módulo 34 que representa a sus miembros | `factor07 × mieperho` | Suma de miembros expandidos de los hogares del ámbito |

Para estimar hogares, se usaría `factor07` una sola vez por hogar. Las tasas de este proyecto describen personas. Las columnas `poblacion_expandida` y `poblacion_pobre_expandida` conservan denominador y numerador. `n_observaciones` cuenta filas muestrales del método. Se publican estimaciones puntuales ponderadas.

## Contrastes

Las referencias de área son 24,8 % urbana y 39,3 % rural. La referencia nacional es 27,6 %. Para `personas`, la tolerancia nacional de la rúbrica es 0,10 pp. Se usa 0,20 pp por área y 0,60 pp por departamento para contrastar el estimador directo con referencias reproducidas desde Sumaria. Para `sumaria`, el margen de redondeo es 0,05 pp en cada ámbito. Se registran todos los desvíos absolutos y ambos estimadores deben pasar sus respectivos controles.

El CSV de referencia solo interviene en la comparación posterior al cálculo. La diferencia entre los dos estimadores se observa aun con unión completa. `mieperho` cuenta 109 842 miembros en Sumaria y el filtro de la sesión selecciona 108 664 residentes en el módulo 02. El conteo por hogar difiere en 1 846 hogares. En el conjunto unido, el `facpob07` individual coincide con el `factor07` del hogar correspondiente. Los pesos suman 34 147 765,79 y 34 482 699,31 personas expandidas, respectivamente.

[Enunciado](https://github.com/d2cml-ai/Data-Science-Python/issues/201) · [Sesión 16](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/16-skills-enaho) · [Referencia departamental](https://github.com/d2cml-ai/Data-Science-Python/blob/main/sessions/16-skills-enaho/referencias/pobreza_departamento_2024.csv)
