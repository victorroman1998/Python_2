# Bitácora para los tres Issues del repositorio

Estos textos corresponden a la ejecución real del 18 de octubre de 2026. Después de publicar los commits en GitHub, crea los Issues 2 y 3; renombra el Issue #1 existente. Copia cada sección como cuerpo y cierra el Issue cuando su punto pendiente esté resuelto.

## Issue #1 — T1 – Parte 1: Recolección y Limpieza

- [x] Revisé `robots.txt` y descargué los RSS y sitemaps oficiales de La República, con pausa de 1,5 segundos y un reintento máximo.
- [x] Guardé fuentes crudas y reporte de procedencia y descartes.
- [x] Formé un corpus final de 399 titulares, siete columnas, cuatro categorías y URL única.
- [x] Comprobé HTTP 200 para las 399 URL finales.
- [x] Ejecuté `01_recoleccion.ipynb` con tabla de mapeo y tres gráficos Plotly.

**Bitácora.** Los RSS y sitemaps de ese día aportaron 53 noticias únicas. Para llegar a la muestra histórica consulté un índice externo solo para descubrir URL y extraje los metadatos del HTML oficial cuando estuvo disponible. Una URL no quedó en el corpus por no tener HTTP 200 comprobado. El corpus final tiene 110 noticias de política, 93 de economía, 100 de deportes y 96 de ciencia/tecnología. Octubre concentra 363 de 399 titulares y la longitud mediana es 103 caracteres. Código y notebook: [`ab0b26c`](https://github.com/victorroman1998/Python_2/commit/ab0b26c).

## Issue #2 — T1 – Parte 2: Modelado y Clasificación

- [x] Etiqueté los 399 titulares con Ollama `qwen2.5:3b` y conservé la salida en CSV.
- [x] Incorporé la auditoría humana independiente de 20 titulares y su acuerdo real.
- [x] Separé 70/15/15 de forma estratificada con semilla 42.
- [x] Medí zero-shot en 40 titulares, ajusté DistilBERT durante tres épocas con lote de 8 y evalué el test reservado.
- [x] Guardé matriz de confusión, comparación y notebook ejecutado.

**Bitácora.** La primera ejecución del LLM se detuvo por etiquetas fuera de las cuatro clases. Se corrigió el formato de salida a un esquema JSON con enumeración y se completaron 399 etiquetas. La línea base zero-shot dio F1 macro 0,698 en 40 noticias de validación. El Transformer obtuvo F1 macro 0,883 en 60 noticias de test; el LLM, 0,935 en las 60. En una comparación adicional sobre las mismas 40 noticias del test, el zero-shot obtuvo 0,826, el Transformer 0,926 y el LLM 0,946. El estudiante revisó independientemente 20 titulares: hubo 16 acuerdos con el LLM (80 %) y cuatro desacuerdos, documentados en `datos/auditoria_humana_respuesta.csv`. Código y notebook: [`37045fb`](https://github.com/victorroman1998/Python_2/commit/37045fb).

## Issue #3 — T1 – Parte 3: Dashboard y Despliegue

- [x] Probé filtros, indicadores, gráfico, tabla, descarga y clasificación de un titular nuevo en la app local.
- [x] Documenté dos hallazgos y dos limitaciones con evidencia.
- [x] Comprobé la app con `streamlit.testing.v1.AppTest`: 399 noticias y clasificación de un titular de fútbol como Deportes.
- [x] Excluí del repositorio los pesos de 541 MB y los secretos.
- [x] Publiqué los commits en GitHub y comprobé la URL del repositorio.

**Bitácora.** La app muestra el corpus y las métricas observadas, permite filtrar por categoría, descargar la selección y probar un titular con el modelo entrenado. La prueba automatizada local no equivale a un despliegue público. Los pesos están disponibles en la carpeta local del proyecto y se regeneran con el notebook; GitHub contiene código, configuración y métricas. Código: [`37045fb`](https://github.com/victorroman1998/Python_2/commit/37045fb).
