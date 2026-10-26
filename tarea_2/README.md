# Voces y documentos peruanos: del archivo al texto buscable

**Tarea 2 individual · [Enunciado](https://github.com/d2cml-ai/Data-Science-Python/issues/190) · [Repositorio](https://github.com/victorroman1998/Python_2).**

**Estado: trabajo en revisión, todavía no es una entrega final.** Los corpus y las inferencias son reales. Las 20 referencias manuales fueron completadas y confirmadas; CER/WER están calculados y la auditoría humana da 14/20 (70 %). Los 47 registros tienen revisión humana de privacidad vigente. Faltan las evidencias de conversación y comprobar el contenido final de la aplicación pública.

## Pregunta y método

¿Podemos transformar documentos peruanos escaneados y español peruano grabado en un archivo de texto estructurado y buscable? El proyecto combina PaddleOCR, transcripción ASR con VAD, diarización, campos JSON de un LLM local y un dashboard Streamlit que lee resultados guardados. La aplicación pública no carga modelos pesados.

## Corpus real y fuentes

Extracción: **25 de octubre de 2026, hora de Perú**.

| Modalidad | Volumen | Origen y licencia |
|---|---:|---|
| Impresos | 8 páginas | Constitución histórica de 1856, BNP/Wikimedia Commons, dominio público |
| Fotos | 8 páginas/imágenes | Documentos en exposiciones, vitrina y carta de restaurante en Chiclayo, Wikimedia Commons, CC BY y CC BY-SA según archivo |
| Manuscritos | 9 páginas/imágenes | Cartas históricas peruanas, BNP/archivos/Wikimedia Commons, dominio público y CC0 |
| Locuciones | 20 clips, 33,15 minutos | [OpenSLR 73](https://www.openslr.org/73/), Google, CC BY-SA 4.0 |
| Entrevistas naturales | 2 clips, 5,42 minutos | El Agustino, Lima, Wikimedia Commons, CC BY-SA 4.0 |
| **Total de audio** | **22 clips, 38,57 minutos** | Procedencia individual registrada |

Las fotos contienen perspectiva, iluminación desigual, sombra o reflejos reales. Algunas fotografían soporte manuscrito o mixto y se clasifican como `foto` por la dificultad de captura; las nueve imágenes de `manuscrito` son registros diferentes. Dos fotografías contienen dos páginas: se recortó cada página por separado, conservando la procedencia y los límites exactos. No se introdujo texto ni degradación sintética.

Los clips OpenSLR son montajes de locuciones auténticas y pueden incluir varias voces. Su correspondencia con cada WAV original, sus tiempos y las transcripciones del proveedor se conserva en `datos/raw/audio/procedencia_segmentos.csv`. Esas transcripciones son metadatos y **no son referencias manuales**.

`datos/seleccion_documentos.csv` contiene URL de origen/descarga, licencia, autor, página, recorte, fecha y hashes del original y de la imagen procesada. `datos/fuentes_audio.csv` conserva el procedimiento de cada clip. `datos/fuentes.csv` reúne atribuciones y recuperación por ID. Los descargadores consultan `robots.txt`, usan User-Agent identificable y pausas de 1,3 segundos. Los candidatos iniciales que eran retratos, estampillas o materiales de categoría inadecuada no se incluyeron en el corpus.

## Resultados observados y limitaciones

Las veinte referencias manuales ya fueron registradas por el estudiante. Los siguientes resultados usan esas referencias y las predicciones originales; **el estudiante confirmó sin cambios las dos entrevistas y completó las 47 revisiones de privacidad**.

| Modalidad | Modelo | Error agregado | Casos | Latencia total sin carga | RTF global |
|---|---|---:|---:|---:|---:|
| OCR | PaddleOCR 3.7 / PP-OCRv6 | CER 21,18 % | 10 | 657,16 s | — |
| OCR | EasyOCR 1.7.2 | CER 40,11 % | 10 | 394,29 s | — |
| ASR | faster-whisper small, CPU/int8 | WER 40,95 % | 10 | 126,49 s | 0,113 |
| ASR | Qwen3-ASR 0.6B, GPU | WER 44,30 % | 10 | 131,91 s | 0,118 |

Se elige la línea base de cada modalidad para el corpus principal: PaddleOCR redujo el error a costa de más tiempo de CPU; Whisper small obtuvo menor WER y funcionó en CPU con RTF inferior a uno. EasyOCR fue más rápido, pero perdió precisión en esta muestra. La latencia ASR no aísla el efecto del hardware, porque Qwen se ejecutó en GPU. No se midió memoria máxima por proceso; la disponibilidad de una GPU de 8 GB no demuestra por sí sola consumo de ese tamaño.

1. La longitud mediana del OCR fue de **1.552 caracteres en impresos**, frente a **761 en fotos** y **890 en manuscritos**, antes de ocultar nombres. Describe la cantidad de texto recuperada; no equivale a precisión.
2. Las entrevistas naturales representan **14,06 % de la duración**. El resto procede de locuciones leídas de OpenSLR; el corpus no representa por igual todos los ambientes de grabación.
3. El CER de PaddleOCR por tipo fue **13,39 % en impresos**, **10,33 % en fotos** y **40,10 % en manuscritos**. Dos de las tres fotos de evaluación contienen texto mecanografiado legible: ese resultado no significa que cualquier fotografía sea más fácil que un impreso. El manuscrito `doc_022` fue un caso difícil para ambos OCR.
4. El WER de `clip_021` superó el 100 % por inserciones frente a su referencia. Esta tasa puede superar uno y no debe recortarse. El estudiante volvió a escuchar y confirmó ambas referencias sin cambios. Se conserva esa decisión y se advierte que las diferencias de abreviación —por ejemplo, una sigla frente a un nombre de institución pronunciado completo— penalizan WER.

La muestra de diez casos por modalidad es pequeña y varias páginas impresas proceden de un mismo volumen. El agrupamiento de voces no acredita identidad ni exactitud del número de personas sin escucha humana. Los manuscritos históricos, la tinta del reverso y los reflejos de vitrina limitan la extracción. La auditoría humana de veinte JSON tuvo **14 correctos y 6 incorrectos (70 %)**. En `doc_010`, el LLM cambió el día 20 por 22. En cinco clips afirmó un número de hablantes sin marcas que lo sustentaran. Las decisiones correctoras de esos seis casos y la revisión de `clip_021` se registraron por confirmación explícita del estudiante en conversación, con fecha y procedencia; las otras decisiones provienen de la aplicación local. No se corrigieron las respuestas del modelo para mejorar este resultado.

La app pública utilizará solo dos medios autorizados: `doc_002.jpg`, una página sin nombres, y un MP3 de 46,55 segundos de `clip_021` (89,55–136,10 s), que omite la presentación con nombres. La licencia CC BY-SA 4.0 del audio se conserva y el recorte está indicado. Los demás originales autorizados se mantienen locales.

## Ejecución

Python 3.12. El entorno probado utilizó Windows, una RTX 4060 Laptop de 8 GB y 16 GB de RAM. Las dependencias ligeras de la aplicación están en `requirements.txt`; las de inferencia, en `requirements-inferencia.txt`. No instalar motores OCR/ASR en Streamlit Cloud.

Desde `tarea_2/`, para la aplicación:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Para anotación y revisión **local**, sin publicar originales:

```powershell
python -m streamlit run anotar.py --server.address 127.0.0.1 --server.port 8502
```

Para reproducir inferencia, instalar primero las versiones fijadas de `requirements-inferencia.txt`, y después:

```powershell
python -m pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
python -m pip install --no-deps easyocr==1.7.2
```

EasyOCR reutiliza OpenCV contrib 4.10.0.84 de PaddleX; se evita instalar una segunda variante de OpenCV sobre la misma carpeta. La diarización carga el audio en memoria; no depende del decodificador de TorchCodec, que emitió una advertencia de compatibilidad en este Windows.

Clonar el [repositorio del curso](https://github.com/d2cml-ai/Data-Science-Python) y establecer `$env:CURSO_ROOT` a su carpeta. `voz.py` se toma de `sessions/13-audio-a-texto/`. Para recuperar corpus y volver a ejecutar:

```powershell
python recuperar_documentos.py
python generar_audio_openslr.py
python agregar_entrevistas.py
```

El generador OpenSLR se detiene si ya hay clips para evitar sobrescribir el corpus. Mantener los originales fuera de Git. Abrir `01_extraccion.ipynb` y ejecutar con las salidas existentes; cambiar `RECALCULAR` solo para repetir los motores. Para LLM, se utilizó Ollama local con `qwen2.5:3b`; no se necesita una clave API. Las configuraciones y versiones están en `modelos/`.

## Evaluación y trabajo humano pendiente

La muestra definitiva contiene 10 documentos, estratificados 3/3/4 y con diversidad de fuentes, y 10 clips, incluyendo ambas entrevistas naturales. Se usa la semilla 20261025, se verifican hashes y se conserva la misma muestra para ambos modelos de cada modalidad. La configuración se fijó antes de consultar CER/WER.

1. En `anotar.py`, **transcribir personalmente** los veinte originales. No copiar las respuestas OCR/ASR ni las referencias OpenSLR. Si un original resulta ilegible, registrar el caso antes de reemplazarlo y volver a congelar la evaluación de manera documentada.
2. Comparar PaddleOCR 3.7.0 con EasyOCR 1.7.2, y faster-whisper `small` CPU con Qwen3-ASR 0.6B GPU. La inferencia puede completarse antes de las referencias; sus borradores están en `datos/_privado/predicciones_modelos.csv`.
3. Ejecutar `02_evaluacion.ipynb` para incorporar referencias y calcular CER/WER. La normalización conserva tildes, aplica NFC y minúsculas, sustituye puntuación por espacios y retira etiquetas artificiales de hablante. Se agregan errores y denominadores sobre todos los casos; no se promedian tasas individuales. Las distancias se calculan sobre referencias y predicciones originales en el equipo local, antes de ocultar nombres, para que la seudonimización no mejore artificialmente el error. Solo después se seudonimizan los textos exportados. Se publican errores y denominadores por caso para reproducir la agregación; los originales y la correspondencia permanecen privados.
4. Revisar privacidad de OCR, ASR, referencias, alternativas y JSON. Los patrones automáticos de DNI/correo/teléfono no sustituyen la revisión de nombres y direcciones. Los cambios invalidan las revisiones anteriores mediante hashes.
5. Auditar los 20 JSON seleccionados (10 documentos y 10 audios). Cada caso es correcto solo si todos los campos están sustentados y los ausentes son `null`. El porcentaje se calcula después de completar las veinte decisiones humanas.
6. Autorizar un pequeño conjunto de ejemplos multimedia solo después de revisar la licencia y su contenido. El dashboard comprueba `datos/ejemplos/manifest.csv` y el hash del archivo. No muestra originales privados ni enlaces rotos.

El `hash_entrada` del LLM identifica el texto local anterior a ocultar nombres; `postprocesamiento` registra el diccionario privado utilizado. Las autorías profesionales de las fuentes se conservan para cumplir las licencias.

El LLM local puede producir borradores antes de revisar privacidad. El envío a Gemini u otro proveedor externo permanece bloqueado hasta la revisión. No publicar CSV, notebooks con contenido sensible ni ejemplos sin completar esa revisión.

## Publicación y entrega

**Dashboard público: [abrir aplicación](https://python2-8gghwjxssgbplo5wveyz8q.streamlit.app/).** Desplegado; verificación del contenido final en curso. Debe desplegarse en [Streamlit Community Cloud](https://share.streamlit.io) desde `victorroman1998/Python_2`, rama elegida y ruta `tarea_2/app.py`, y comprobar el enlace público.

Crear y documentar las tres issues del enunciado y cerrarlas solo cuando cada etapa esté terminada. Las bitácoras están abiertas en [Parte 1 #4](https://github.com/victorroman1998/Python_2/issues/4), [Parte 2 #5](https://github.com/victorroman1998/Python_2/issues/5) y [Parte 3 #6](https://github.com/victorroman1998/Python_2/issues/6). Mantenerlas abiertas hasta completar cada etapa. No se inventan commits de días anteriores.

Guardar capturas auténticas y completas de esta conversación en `evidencias_ia/`, numeradas cronológicamente, ocultando información sensible. La captura de la conversación debe realizarla el estudiante; no se han fabricado capturas.

Ejecutar antes de publicar:

```powershell
python validar_publicacion.py --verificar
python verificar_entrega.py
```

El comentario de entrega solo se completa cuando existan valores reales:

```text
Tarea 2 – Individual
Fuentes: Wikimedia Commons / Biblioteca Nacional del Perú / OpenSLR 73
Identificación indicada por el estudiante: Tarea2-Python-Intermedio (@victorroman1998)
Dashboard público (obligatorio): [enlace público verificado]
Carpeta del trabajo: https://github.com/victorroman1998/Python_2/tree/main/tarea_2
Resultados Test: WER: [real] | CER: [real] | Acuerdo LLM-Humano: [real]/20
```
