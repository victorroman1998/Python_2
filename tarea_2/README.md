# Voces y documentos peruanos: del archivo al texto buscable

**Tarea 2 individual · [Enunciado](https://github.com/d2cml-ai/Data-Science-Python/issues/190) · [Repositorio](https://github.com/victorroman1998/Python_2).**

**Estado: trabajo en revisión, todavía no es una entrega final.** Los corpus y las inferencias son reales. Faltan referencias transcritas por el estudiante, auditoría humana, revisión de privacidad, evidencias de conversación y enlace público verificado. CER, WER y acuerdo LLM-humano se mantienen pendientes cuando falta la evidencia humana correspondiente.

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

1. La longitud mediana del OCR fue de **1.552 caracteres en impresos**, frente a **761 en fotos** y **890 en manuscritos**. Describe la cantidad de texto recuperada; la precisión se determina con CER sobre referencias manuales.
2. Las entrevistas naturales representan **14,06 % de la duración**. El resto procede de locuciones leídas de OpenSLR; por tanto, el corpus está dominado por condiciones de voz relativamente limpia y no representa por igual todas las situaciones de entrevista.

Limitaciones técnicas: la muestra de diez casos por modalidad es pequeña y varias páginas impresas proceden de un mismo volumen. Además, Qwen3-ASR se ejecuta en GPU y Whisper `small` en CPU, por lo que la latencia observada combina diferencias de modelo y hardware. La diarización es un agrupamiento automático de voces: no acredita identidad ni exactitud del número de personas sin escucha humana. Los manuscritos históricos, tinta del reverso y reflejos de vitrina son casos difíciles que requieren análisis con las referencias.

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
3. Ejecutar `02_evaluacion.ipynb` para incorporar referencias y calcular CER/WER. La normalización conserva tildes, aplica NFC y minúsculas, sustituye puntuación por espacios y retira etiquetas artificiales de hablante. Se agregan errores y denominadores sobre todos los casos; no se promedian tasas individuales. Antes de puntuar se aplica el mismo diccionario literal de seudonimización a referencias y predicciones. Los originales se conservan privados y el informe público registra los reemplazos sin revelar la correspondencia.
4. Revisar privacidad de OCR, ASR, referencias, alternativas y JSON. Los patrones automáticos de DNI/correo/teléfono no sustituyen la revisión de nombres y direcciones. Los cambios invalidan las revisiones anteriores mediante hashes.
5. Auditar los 20 JSON seleccionados (10 documentos y 10 audios). Cada caso es correcto solo si todos los campos están sustentados y los ausentes son `null`. El porcentaje se calcula después de completar las veinte decisiones humanas.
6. Autorizar un pequeño conjunto de ejemplos multimedia solo después de revisar la licencia y su contenido. El dashboard comprueba `datos/ejemplos/manifest.csv` y el hash del archivo. No muestra originales privados ni enlaces rotos.

El LLM local puede producir borradores antes de revisar privacidad. El envío a Gemini u otro proveedor externo permanece bloqueado hasta la revisión. No publicar CSV, notebooks con contenido sensible ni ejemplos sin completar esa revisión.

## Publicación y entrega

**Dashboard público: pendiente de despliegue.** Debe desplegarse en [Streamlit Community Cloud](https://share.streamlit.io) desde `victorroman1998/Python_2`, rama elegida y ruta `tarea_2/app.py`, y comprobar el enlace público.

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
Estudiante: [nombre completo] (@victorroman1998)
Dashboard público (obligatorio): [enlace público verificado]
Carpeta del trabajo: https://github.com/victorroman1998/Python_2/tree/main/tarea_2
Resultados Test: WER: [real] | CER: [real] | Acuerdo LLM-Humano: [real]/20
```
