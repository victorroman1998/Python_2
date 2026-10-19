# Respaldo crudo de la recolección

La ejecución local del 18 de octubre de 2026 conservó aquí **383 archivos** (8 XML de RSS/sitemaps, 28 JSON del índice, 346 HTML oficiales y `robots.txt`), unos **59,9 MB**. No se publican las páginas HTML completas en GitHub para evitar redistribuir el contenido del medio y mantener el repositorio ligero. La carpeta del estudiante en OneDrive conserva las copias crudas.

Para generar nuevamente las fuentes, desde `tarea_1/` ejecuta `python recolectar.py --objetivo 400`. La primera pasada descubre candidatos; después ejecuta `python validar_urls.py` y vuelve a ejecutar el recolector o `01_recoleccion.ipynb` para conservar únicamente las URL con HTTP 200 comprobado. Las fuentes pueden cambiar con el tiempo, por lo que un nuevo resultado no tiene por qué ser idéntico al CSV entregado.
