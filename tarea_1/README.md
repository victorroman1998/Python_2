# Noticias peruanas: del titular al clasificador

**Pregunta:** ¿Pueden los titulares peruanos convertirse en un clasificador de noticias?

Proyecto individual de la [Tarea 1 del diplomado](https://github.com/d2cml-ai/Data-Science-Python/issues/188). Se eligió la **opción A, La República**. Las cuatro clases fijas son `politica`, `economia`, `deportes` y `ciencia_tecnologia`. El conjunto de datos se construye desde los [RSS oficiales enumerados en robots.txt](https://larepublica.pe/robots.txt), sitemaps y páginas HTML del medio. Los RSS y sitemaps observados el 18 de octubre solo aportaron 53 noticias únicas del día; para descubrir URLs anteriores se usa [Free News API](https://freenewsapi.ai/docs/search) como índice externo. La etiqueta siempre sale de la ruta editorial de `larepublica.pe`, no de la categoría asignada por el índice. Se respetan `robots.txt`, pausa de 1,5 segundos y un reintento máximo.

## Estado y procedencia

La descarga se efectuó el 18 de octubre de 2026 (hora de Perú) y abarca publicaciones del 26 de septiembre al 18 de octubre, con las fechas convertidas a hora peruana cuando la fuente incluye zona horaria. La fecha de extracción, las fuentes, el número de filas y los descartes se generan en `datos/reporte_recoleccion.json`. Este archivo no debe completarse a mano. El CSV final contiene 399 noticias reales: 52 de RSS, 346 con HTML oficial y 1 con solo metadatos del índice. En `datos/raw/` se conservan los XML, JSON del índice y HTML obtenido. `validar_urls.py` comprobó 399 respuestas HTTP 200; un enlace RSS devolvió 404 y fue descartado. El detalle de esa comprobación permanece en `datos/validacion_urls.csv`. La columna `etiqueta` es la etiqueta de sección editorial normalizada; es una referencia imperfecta, no una validación humana.

| Sección original | Categoría |
|---|---|
| politica | politica |
| economia | economia |
| deportes | deportes |
| ciencia | ciencia_tecnologia |
| tecnologia | ciencia_tecnologia |

## Instalación y ejecución local

Desde `tarea_1/`, con Python 3.11 recomendado:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python recolectar.py --objetivo 400
python -m ipykernel install --user --name tarea1-noticias --display-name "Tarea 1 noticias"
jupyter lab 01_recoleccion.ipynb
```

Para el LLM local se requiere [Ollama](https://ollama.com/) y suficiente RAM. En otra terminal:

```powershell
ollama pull qwen2.5:3b
python etiquetar_llm.py --modelo qwen2.5:3b
jupyter lab 02_clasificacion.ipynb
```

En el segundo notebook, revisa manualmente los 20 titulares seleccionados en `datos/auditoria_humana_plantilla.csv`. Escribe la categoría correcta en `datos/auditoria_humana_respuesta.csv` y vuelve a ejecutar la celda de auditoría. El acuerdo es una medición humana real. Entrena el modelo y guarda los pesos en `modelo/` localmente. Luego:

```powershell
streamlit run app.py
```

Antes de entregar, ejecuta `python verificar_entrega.py`. El programa revisa el número y la estructura de las noticias, las etiquetas LLM, ambos notebooks guardados con salidas, las métricas y el modelo local. La verificación de enlaces HTTP se registra por separado en `datos/validacion_urls.csv`.

La primera vez, los modelos zero-shot y DistilBERT se descargan de Hugging Face. Para adelantar esa descarga se puede ejecutar `python precargar_modelos.py` antes del segundo notebook. En CPU el entrenamiento puede tardar; con GPU de Colab, descarga los artefactos a `modelo/`. Los pesos se excluyen de Git por su tamaño. Por ello, quien clone el repositorio debe ejecutar el notebook de entrenamiento antes de usar el probador de la app. Los gráficos y tabla sí pueden abrirse con el CSV.

Si publicas tu modelo entrenado en un repositorio de Hugging Face, define `NEWS_MODEL_REPO=usuario/repositorio` en el entorno de Streamlit para que la aplicación pueda cargarlo sin guardar pesos en GitHub. Esto requiere una publicación real bajo tu cuenta; no hay repositorio preconfigurado.

## Método y evaluación

`01_recoleccion.ipynb` registra procedencia, limpieza, descartes, tabla de mapeo, tres gráficos Plotly y extremos de longitud. La verificación de enlaces reutiliza respuestas HTTP 200 de los HTML descargados y consulta por red las URLs sin copia. `02_clasificacion.ipynb` separa 70/15/15 de forma estratificada con semilla 42. El test queda reservado hasta la evaluación final. La línea base zero-shot se mide primero en 40 titulares de validación y, para la comparación final, en 40 titulares del test reservado. El LLM etiqueta el conjunto completo, pero el Transformer se ajusta exclusivamente con las etiquetas débiles del tramo de entrenamiento. Se elige el mejor checkpoint por F1 macro en validación y se calculan accuracy, F1 macro y matriz de confusión en test. La comparación especifica el número de observaciones de cada método.

## Hallazgos

1. La muestra quedó cercana al equilibrio buscado: política tiene 110 titulares (27,6 %) y economía 93 (23,3 %), con 100 de deportes y 96 de ciencia/tecnología. Octubre aporta 363 de las 399 noticias (91 %); el resto procede de septiembre.
2. La longitud mediana de los titulares es 103 caracteres, con extremos de 54 y 164. Esta variación hace útil mostrar los casos más cortos y más largos junto al histograma del notebook; un límite fijo muy bajo truncaría ejemplos reales.

## Limitaciones

1. La categoría editorial es una referencia imperfecta: una noticia puede cruzar política y economía. La auditoría de 20 casos ayuda a detectar desacuerdos, pero no sustituye un test anotado independientemente por humanos.
2. RSS y HTML pueden cambiar o bloquear consultas. La recolección guarda XML/HTML crudo y documenta fallos; la probabilidad del clasificador tampoco está calibrada.

## Entrega en GitHub

Coloca esta carpeta `tarea_1/` dentro de [tu repositorio del curso](https://github.com/victorroman1998/Python_2). Ejecuta ambos notebooks y guarda sus salidas visibles. El Issue #1, titulado `A_1`, puede renombrarse y completarse como `T1 – Parte 1: Recolección y Limpieza`; crea además `T1 – Parte 2: Modelado y Clasificación` y `T1 – Parte 3: Dashboard y Despliegue`. Documenta y cierra cada uno al completar su etapa. Registra commits descriptivos conforme avances; no modifiques fechas de commits. No subas secretos ni pesos pesados.

El comentario final en el [Issue de entrega](https://github.com/d2cml-ai/Data-Science-Python/issues/188) requiere tu nombre, usuario, URL de tu carpeta GitHub, enlace del dashboard o ejecución local verificada, F1 macro de test, F1 zero-shot y acuerdo humano/LLM. Estos valores se copian de resultados reales, nunca de ejemplos.
