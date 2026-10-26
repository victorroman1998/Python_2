"""Comprobación inicial y preparación de candidatos. No crea datos ni métricas falsos.
Uso: python iniciar_casa.py --preparar
"""
from __future__ import annotations
import argparse
import csv
import importlib.metadata as metadata
import shutil
import subprocess
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parent


def estado():
    print('\nTAREA 2 | DIAGNÓSTICO DEL ENTORNO')
    print('Python:',sys.version.split()[0])
    print('Proyecto:', BASE)
    for paquete in ['pandas','plotly','paddleocr','paddlepaddle','faster-whisper',
                    'pyannote.audio','transformers','jiwer','pytesseract','google-genai','streamlit']:
        try: v=metadata.version(paquete)
        except metadata.PackageNotFoundError: v='FALTA'
        print(f'  {paquete:20} {v}')
    print('Git:',shutil.which('git') or 'No identificado')
    print('Tesseract:',shutil.which('tesseract') or 'No identificado en PATH')
    for archivo in ['datos/seleccion_documentos.csv','datos/fuentes_audio.csv','datos/documentos.csv','datos/transcripciones.csv']:
        path=BASE/archivo
        if path.exists():
            with path.open(encoding='utf-8-sig',newline='') as f:n=max(sum(1 for _ in csv.reader(f))-1,0)
        else:n=0
        print(f'{archivo:45} {n} registros')
    total, used, free=shutil.disk_usage(BASE)
    print('Disco libre:',round(free/1024**3,1),'GB')


def correr(script):
    print('\n>>>',script,'\n',flush=True)
    proc=subprocess.run([sys.executable,str(BASE/script)],cwd=BASE,check=False)
    if proc.returncode:
        print('AVISO: script falló con código',proc.returncode,'; resolver incidencia y reintentar si corresponde.')
    return proc.returncode


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--preparar',action='store_true',help='Buscar candidatos y preparar audio OpenSLR')
    a=p.parse_args()
    estado()
    if a.preparar:
        correr('buscar_documentos.py')
        with (BASE/'datos'/'fuentes_audio.csv').open(encoding='utf-8-sig',newline='') as f:
            cantidad=max(sum(1 for _ in csv.reader(f))-1,0)
        if cantidad<20:
            correr('generar_audio_openslr.py')
        correr('agregar_entrevistas.py')
        print('\nSiguiente acción humana: abrir datos/candidatos_documentos.html; completar datos/seleccion_documentos.csv (25 imágenes genuinas, fuentes/licencias) y ejecutar python buscar_documentos.py --descargar.')
        print('Después ejecutar 01_extraccion.ipynb, 02_evaluacion.ipynb, auditoría de privacidad, app.py y despliegue.')
