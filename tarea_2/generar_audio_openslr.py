"""Genera 20 CLIPS COMPUESTOS con ~31 min de locuciones REALES de OpenSLR 73.

Advertencia metodológica: son fragmentos auténticos concatenados, no entrevistas
naturales. Para una comparación más ecológicamente válida se recomienda sustituir
una parte por entrevistas peruanas genuinas (p. ej. Wikimedia Commons con licencia).
Cada origen individual se conserva en procedencia_segmentos.csv.

Uso: python generar_audio_openslr.py
No descarga los ZIP completos (~2 GB); usa solicitudes HTTP Range.
"""
from __future__ import annotations

import csv
import io
import math
import random
import time
import urllib.request
import zipfile
from red import solicitar
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

BASE = Path(__file__).resolve().parent
CARPETA = BASE / 'datos' / 'raw' / 'audio'
URL = 'https://www.openslr.org/resources/73/es_pe_{sexo}.zip'
UA = 'Tarea2-Diplomado-Python/2026 (https://github.com/d2cml-ai/Data-Science-Python; academic use)'
LICENCIA = 'CC BY-SA 4.0 (Google; OpenSLR 73)'
SR = 16000


class ZipRemoto(io.RawIOBase):
    """Lectura parcial de archivo ZIP remoto. Derivado del concepto usado en
    la sesión 13; cache de bloques y limitación básica de solicitudes.
    """
    def __init__(self, url: str):
        self.url = url
        self.pos = 0
        self.ini = 0
        self.buffer = b''
        self.ultimo = 0.0
        with solicitar(url, method='HEAD', timeout=60) as r:
            self.size = int(r.headers['Content-Length'])
        self.bloque = 1 << 20

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0: return b''
        if not (self.ini <= self.pos and self.pos + n <= self.ini + len(self.buffer)):
            ini = self.pos
            fin = min(self.size, ini + max(n, self.bloque)) - 1
            pausa = 1.15 - (time.monotonic() - self.ultimo)
            if pausa > 0: time.sleep(pausa)
            with solicitar(self.url, headers={'Range': f'bytes={ini}-{fin}'}, timeout=120) as r:
                if getattr(r, 'status', None) != 206:
                    raise RuntimeError('El servidor no admitió HTTP Range (206); usar espejo OpenSLR.')
                self.buffer = r.read()
            self.ultimo = time.monotonic()
            self.ini = ini
        data = self.buffer[self.pos-self.ini : self.pos-self.ini+n]
        self.pos += len(data)
        return data


def decodificar(contenido: bytes):
    x, sr = sf.read(io.BytesIO(contenido), dtype='float32')
    if x.ndim == 2: x = x.mean(axis=1)
    if sr != SR:
        g = math.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g).astype('float32')
    return x


def escribir_csv(path: Path, filas, columnas):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction='ignore')
        w.writeheader(); w.writerows(filas)


def generar(n_clips=20, duracion_voz=95.0):
    CARPETA.mkdir(parents=True, exist_ok=True)
    for x in CARPETA.glob('clip_*.wav'):
        raise FileExistsError(f'Hay clips previos ({x.name}). Elimina los existentes solo si quieres regenerar el corpus.')
    rng = random.Random(20261025)
    zips = {}
    listas = {}
    for sexo in ['female', 'male']:
        z = zipfile.ZipFile(ZipRemoto(URL.format(sexo=sexo)))
        lineas = z.read('line_index.tsv').decode('utf-8').splitlines()
        filas = [l.split('\t', 1) for l in lineas if '\t' in l]
        filas = [(id_, trans) for id_, trans in filas if 6 <= len(trans.split()) <= 24]
        rng.shuffle(filas)
        zips[sexo] = z
        listas[sexo] = iter(filas)
        print(f'{sexo}: {len(filas)} en índice, acceso remoto preparado', flush=True)
    manifest, segmentos, textos = [], [], []
    for n in range(1, n_clips + 1):
        clip = f'clip_{n:03d}'
        audio = []
        segundos_voz = 0.0
        segundos_total = 0.0
        voces = set()
        piezas = 0
        while segundos_voz < duracion_voz:
            # Alternar procedencias para multihablante demostrativo del último clip.
            sexo = ('female' if piezas % 2 == 0 else 'male') if n == n_clips else ('female' if n % 2 else 'male')
            try:
                rid, referencia = next(listas[sexo])
            except StopIteration as exc:
                raise RuntimeError('Se agotó OpenSLR sin llegar a los 30 min') from exc
            try:
                wav = decodificar(zips[sexo].read(f'{rid}.wav'))
            except (KeyError, RuntimeError, ValueError) as exc:
                print('Se omite', rid, type(exc).__name__)
                continue
            if not 0.7 <= len(wav) / SR <= 24 or float(np.max(np.abs(wav))) < 0.008:
                continue
            origen_segundos = len(wav) / SR
            speaker = rid.rsplit('_', 1)[0]
            voces.add(speaker)
            audio.append(wav)
            inicio = segundos_total
            segundos_total += origen_segundos
            segundos_voz += origen_segundos
            segmentos.append({'clip': clip, 'id_openslr': rid, 'hablante_anonimo': speaker,
                              'sexo_en_fuente': sexo, 'inicio_seg': round(inicio, 2),
                              'fin_seg': round(segundos_total, 2), 'texto_proporcionado_por_fuente': referencia,
                              'fuente_url': URL.format(sexo=sexo), 'licencia': LICENCIA})
            textos.append((clip, rid, referencia))
            audio.append(np.zeros(int(.12 * SR), dtype='float32'))
            segundos_total += .12
            piezas += 1
        ruta = CARPETA / (clip + '.wav')
        sf.write(ruta, np.concatenate(audio), SR)
        manifest.append({'id': clip, 'archivo_audio': f'datos/raw/audio/{clip}.wav',
                         'fuente_url': 'https://www.openslr.org/73/', 'licencia': LICENCIA,
                         'multihablante': 'si' if len(voces)>1 else 'no',
                         'diarizar': 'si' if n == n_clips else 'no',
                         'procedencia': 'Locuciones originales de OpenSLR 73 concatenadas; NO es una entrevista natural',
                         'n_voces_fuente': len(voces), 'n_fragmentos': piezas,
                         'duracion_seg': round(segundos_total, 2)})
        print(f'{n}/{n_clips}: {clip} | {segundos_total:.1f}s | {piezas} muestras | {len(voces)} IDs de hablante')
    escribir_csv(BASE / 'datos' / 'fuentes_audio.csv', manifest,
                 ['id','archivo_audio','fuente_url','licencia','multihablante','diarizar','procedencia','n_voces_fuente','n_fragmentos','duracion_seg'])
    escribir_csv(BASE / 'datos' / 'raw' / 'audio' / 'procedencia_segmentos.csv', segmentos,
                 ['clip','id_openslr','hablante_anonimo','sexo_en_fuente','inicio_seg','fin_seg','texto_proporcionado_por_fuente','fuente_url','licencia'])
    print(f'CREADO: {len(manifest)} clips | {sum(float(c["duracion_seg"]) for c in manifest)/60:.1f} minutos de audio')
    print('ATENCIÓN: las transcripciones OpenSLR incluidas en procedencia_segmentos.csv son metadatos de la fuente, NO referencias manuales de evaluación.')
    print('ATENCIÓN: según la rúbrica, transcribir 10 clips de forma MANUAL, sin copiar las referencias del corpus.')


if __name__ == '__main__':
    generar()
