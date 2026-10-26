"""Tarea 2: extracción reproducible. Resultados sin intervención humana = BORRADORES.
Requiere recursos externos instalados para OCR y ASR; app.py es independiente.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
DATOS = BASE / 'datos'
DOC_CSV = DATOS / 'documentos.csv'
AUDIO_CSV = DATOS / 'transcripciones.csv'
SELECCION = DATOS / 'seleccion_documentos.csv'

DOC_COLS = ['id', 'archivo', 'tipo', 'fuente', 'texto_ocr', 'modelo_ocr', 'texto_referencia']
AUDIO_COLS = ['id', 'archivo_audio', 'duracion_seg', 'idioma', 'texto_asr', 'modelo_asr', 'n_hablantes', 'texto_referencia']
FUENTE_COLS = ['id', 'modalidad', 'fuente_url', 'licencia', 'acceso']


def leer_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        if columns is None:
            raise FileNotFoundError(path)
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if columns:
        for col in columns:
            if col not in df:
                df[col] = ''
    return df


def guardar_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def normalizar_ruta(s: str) -> Path:
    p = Path(str(s))
    return p if p.is_absolute() else BASE / p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def seudonimizar_basico(texto: str) -> tuple[str, int]:
    """Marcas preventivas; revisión humana obligatoria para nombres, DNI y terceros."""
    total = 0
    reglas = [
        (r'(?<!\w)\b\d{8}\b(?!\w)', '[IDENTIFICADOR]'),
        (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[CORREO]'),
        (r'(?<!\w)(?:\+?51\s*)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\w)', '[TELEFONO]'),
    ]
    for patron, sustitucion in reglas:
        texto, n = re.subn(patron, sustitucion, texto, flags=re.IGNORECASE)
        total += n
    return texto, total


def extraer_texto_paddle(resultado) -> str:
    lineas = []
    for bloque in resultado:
        if hasattr(bloque, 'json'):
            bloque = bloque.json
        if not isinstance(bloque, dict):
            continue
        datos = bloque.get('res', bloque)
        lineas.extend(str(s).strip() for s in datos.get('rec_texts', []) if str(s).strip())
    return '\n'.join(lineas)


def ocr_paddle(rutas: list[Path], usar_cpu: bool = True) -> list[str]:
    import entorno
    from paddleocr import PaddleOCR
    parametros = {
        'lang': 'es',
        'use_doc_orientation_classify': False,
        'use_doc_unwarping': False,
        'use_textline_orientation': False,
        'device': 'cpu' if usar_cpu else 'gpu',
    }
    if usar_cpu:
        parametros['enable_mkldnn'] = False  # workaround documentado en sesión 10
    motor = PaddleOCR(**parametros)
    salida = []
    for i, ruta in enumerate(rutas, 1):
        texto = extraer_texto_paddle(motor.predict(str(ruta)))
        salida.append(texto)
        print(f'OCR: {i}/{len(rutas)} | {ruta.name} | {len(texto)} caracteres', flush=True)
    return salida


def extraer_documentos(forzar: bool = False) -> pd.DataFrame:
    """Lee 25 originales seleccionados y preserva el texto de referencia si existe."""
    m = leer_csv(SELECCION)
    req = {'id', 'archivo', 'tipo', 'fuente_url', 'licencia'}
    if not req.issubset(m.columns):
        raise ValueError(f'Faltan columnas en seleccion_documentos.csv: {sorted(req - set(m))}')
    m = m[m['id'].astype(str).str.strip().ne('')].copy()
    cantidades = m['tipo'].value_counts().to_dict()
    if any(cantidades.get(t, 0) < n for t, n in [('impreso', 8), ('foto', 8), ('manuscrito', 9)]):
        raise ValueError(f'Se requieren >= 8 impresos, 8 fotos, 9 manuscritos. Actual: {cantidades}')
    campos = ['archivo', 'fuente_url', 'licencia']
    vacias = m[m[campos].apply(lambda c: c.str.strip().eq('')).any(axis=1)]
    if not vacias.empty:
        raise ValueError(f'Faltan archivos o fuentes/licencias verificadas en IDs: {vacias.id.tolist()}')
    if m.id.duplicated().any():
        raise ValueError('IDs duplicados en selección de documentos')
    rutas = [normalizar_ruta(x) for x in m['archivo']]
    faltantes = [str(p) for p in rutas if not p.is_file()]
    if faltantes:
        raise FileNotFoundError('Descargar/colocar documentos primero: ' + ', '.join(faltantes[:6]))
    hashes = [sha256(p) for p in rutas]
    if len(set(hashes)) != len(hashes):
        raise ValueError('Hay archivos documentales duplicados por SHA256; sustituirlos.')
    anteriores = leer_csv(DOC_CSV, DOC_COLS).set_index('id')
    buscar = []
    indices = []
    for i, r in m.reset_index(drop=True).iterrows():
        if forzar or r.id not in anteriores.index or not str(anteriores.loc[r.id, 'texto_ocr']).strip():
            indices.append(i)
            buscar.append(rutas[i])
    textos_nuevos = dict(zip(indices, ocr_paddle(buscar))) if buscar else {}
    filas, fuentes, total_masc = [], [], 0
    for i, r in m.reset_index(drop=True).iterrows():
        texto_original = textos_nuevos.get(i, str(anteriores.loc[r.id, 'texto_ocr']) if r.id in anteriores.index else '')
        texto, n = seudonimizar_basico(texto_original)
        total_masc += n
        if len(texto.strip()) < 20:
            print(f'AVISO: OCR corto/ilegible {r.id}; revisar y reemplazar si corresponde')
        referencia = str(anteriores.loc[r.id, 'texto_referencia']) if r.id in anteriores.index else ''
        filas.append({'id': r.id, 'archivo': r.archivo, 'tipo': r.tipo,
                      'fuente': f"{r.fuente_url} ({r.licencia})", 'texto_ocr': texto,
                      'modelo_ocr': 'PaddleOCR 3.7.0; PP-OCRv6 medium; lang=es; CPU; orientación=off',
                      'texto_referencia': referencia})
        fuentes.append({'id': r.id, 'modalidad': 'documento', 'fuente_url': r.fuente_url,
                        'licencia': r.licencia, 'acceso': 'Consultar URL; copia local: ' + r.archivo})
    df = pd.DataFrame(filas, columns=DOC_COLS)
    guardar_csv(df, DOC_CSV)
    actualizar_fuentes(fuentes, modalidad='documento')
    print(f'Documentos: {df.shape}; patrones sensibles sustituidos: {total_masc}; REVISAR NOMBRES MANUALMENTE')
    return df


def actualizar_fuentes(nuevas: list[dict], modalidad: str) -> None:
    ruta = DATOS / 'fuentes.csv'
    a = leer_csv(ruta, FUENTE_COLS)
    a = a[a['modalidad'] != modalidad]
    guardar_csv(pd.concat([a, pd.DataFrame(nuevas, columns=FUENTE_COLS)], ignore_index=True), ruta)


def _seg_a_srt(segs) -> str:
    def tc(s: float) -> str:
        ms = round(s * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        sec, ms = divmod(ms, 1000)
        return f'{h:02}:{m:02}:{sec:02},{ms:03}'
    return '\n\n'.join(f'{i}\n{tc(a)} --> {tc(b)}\n{(f"[{h}] " if h else "")}{t}'
                      for i, (a, b, t, h) in enumerate(segs, 1)) + '\n'


def diarizar_un_clip(ruta: Path, segments: list[tuple], n_hablantes=None) -> list[tuple]:
    """Diarización de al menos un clip mediante el módulo oficial del curso.
    CURSO_ROOT debe señalar al checkout d2cml-ai/Data-Science-Python.
    """
    import os
    import sys
    curso_root = Path(os.environ.get('CURSO_ROOT', BASE.parent / 'Data-Science-Python'))
    sesion = curso_root / 'sessions' / '13-audio-a-texto'
    if not (sesion / 'voz.py').exists():
        raise FileNotFoundError(f'Para diarización, clonar repositorio del curso y establecer CURSO_ROOT: {sesion}')
    if str(sesion) not in sys.path:
        sys.path.insert(0, str(sesion))
    from voz import Segmento, cargar_audio, diarizar
    array = cargar_audio(str(ruta))
    objetos = [Segmento(a, b, txt) for a, b, txt, _ in segments]
    etiquetados = diarizar(array, objetos, n_hablantes=n_hablantes, device='cpu')
    return [(s.inicio, s.fin, s.texto, s.hablante) for s in etiquetados]


def transcribir_audios(forzar: bool = False, diarizacion: bool = True) -> pd.DataFrame:
    origen = DATOS / 'fuentes_audio.csv'
    meta = leer_csv(origen)
    oblig = {'id', 'archivo_audio', 'fuente_url', 'licencia'}
    if not oblig.issubset(meta.columns):
        raise ValueError('Primero crear fuentes_audio.csv con generar_audio_openslr.py')
    if len(meta) < 20:
        raise ValueError(f'Hay {len(meta)} clips: mínimo 20')
    rutas = [normalizar_ruta(s) for s in meta.archivo_audio]
    if any(not p.is_file() for p in rutas):
        raise FileNotFoundError('Uno o más audios locales aún no existen')
    import soundfile as sf
    duraciones = [float(sf.info(p).duration) for p in rutas]
    if sum(duraciones) < 1800:
        raise ValueError(f'Audio total: {sum(duraciones)/60:.1f} min; mínimo 30')
    import entorno
    from faster_whisper import WhisperModel
    modelo = WhisperModel('small', device='cpu', compute_type='int8')
    prev = leer_csv(AUDIO_CSV, AUDIO_COLS).set_index('id')
    filas, fuentes, mascaras = [], [], 0
    out = DATOS / 'raw' / 'audio' / 'salidas'
    out.mkdir(parents=True, exist_ok=True)
    for j, (r, ruta, segundos) in enumerate(zip(meta.itertuples(index=False), rutas, duraciones), 1):
        old = prev.loc[r.id] if r.id in prev.index else None
        if old is not None and not forzar and str(old['texto_asr']).strip():
            texto = str(old['texto_asr'])
            n_h = str(old['n_hablantes'])
        else:
            raw, _ = modelo.transcribe(str(ruta), language='es', beam_size=5,
                                      vad_filter=True, vad_parameters={'min_silence_duration_ms': 500})
            seg = [(round(s.start, 2), round(s.end, 2), s.text.strip(), None) for s in raw if s.text.strip()]
            n_h = ''
            if diarizacion and (str(getattr(r, 'diarizar', getattr(r, 'multihablante', 'no'))) == 'si'):
                try:
                    seg = diarizar_un_clip(ruta, seg, n_hablantes=None)
                    n_h = len(set(s[3] for s in seg if s[3]))
                except Exception as exc:
                    raise RuntimeError(f'Diarización pendiente en {r.id}: {exc}') from exc
            texto_original = ' '.join(f'[{h}] {txt}' if h else txt for a, b, txt, h in seg)
            texto, n = seudonimizar_basico(texto_original)
            mascaras += n
            (out / f'{r.id}.srt').write_text(_seg_a_srt(seg), encoding='utf-8')
            (out / f'{r.id}.txt').write_text(texto, encoding='utf-8')
            (out / f'{r.id}.json').write_text(json.dumps(seg, ensure_ascii=False, indent=2), encoding='utf-8')
        ref = str(old['texto_referencia']) if old is not None else ''
        filas.append({'id': r.id, 'archivo_audio': r.archivo_audio,
                      'duracion_seg': round(segundos, 2), 'idioma': 'es', 'texto_asr': texto,
                      'modelo_asr': 'faster-whisper small; CPU; int8; VAD',
                      'n_hablantes': n_h, 'texto_referencia': ref})
        fuentes.append({'id': r.id, 'modalidad': 'audio', 'fuente_url': r.fuente_url,
                        'licencia': r.licencia, 'acceso': str(getattr(r,'procedencia','Audio real'))+'; recuperar con los scripts y consultar fuentes_audio.csv; local: '+r.archivo_audio})
        # Punto de restauración: conservar resultados parciales si un modelo falla más adelante.
        guardar_csv(pd.DataFrame(filas, columns=AUDIO_COLS), AUDIO_CSV)
        print(f'ASR: {j}/{len(meta)} | {r.id} | {segundos:.1f}s')
    df = pd.DataFrame(filas, columns=AUDIO_COLS)
    guardar_csv(df, AUDIO_CSV)
    actualizar_fuentes(fuentes, 'audio')
    print(f'Audio: {df.shape}; {sum(duraciones)/60:.2f} minutos; patrones sustituidos: {mascaras}; revisar nombres manualmente')
    return df


def analisis_exploratorio():
    import plotly.express as px
    d, a = leer_csv(DOC_CSV), leer_csv(AUDIO_CSV)
    if d.empty or a.empty:
        raise ValueError('Primero procesar ambas modalidades')
    conteo = d.tipo.value_counts().rename_axis('tipo').reset_index(name='n')
    mas = conteo.loc[conteo.n.idxmax()]
    fig1 = px.bar(conteo, x='tipo', y='n', title=f'El tipo más representado es {mas.tipo} ({mas.n}/{len(d)} documentos)', text='n')
    a['duracion_seg'] = pd.to_numeric(a.duracion_seg, errors='coerce')
    fig2 = px.bar(a, x='id', y='duracion_seg', title=f'El corpus de voz contiene {a.duracion_seg.sum()/60:.1f} minutos distribuidos en {len(a)} clips')
    v = pd.concat([
        pd.DataFrame({'id': d.id, 'longitud': d.texto_ocr.astype(str).str.len(), 'indicador': 'OCR: caracteres'}),
        pd.DataFrame({'id': a.id, 'longitud': a.texto_asr.astype(str).str.split().str.len(), 'indicador': 'ASR: palabras'})
    ], ignore_index=True)
    fig3 = px.histogram(v, x='longitud', color='indicador', facet_col='indicador', title=f'Medianas observadas: {d.texto_ocr.str.len().median():.0f} caracteres OCR y {a.texto_asr.str.split().str.len().median():.0f} palabras ASR', nbins=12)
    fig3.update_xaxes(matches=None)
    print('Tres documentos más largos:')
    print(d.assign(n=d.texto_ocr.astype(str).str.len()).nlargest(3,'n')[['id','tipo','n']].to_string(index=False))
    print('Tres documentos más cortos:')
    print(d.assign(n=d.texto_ocr.astype(str).str.len()).nsmallest(3,'n')[['id','tipo','n']].to_string(index=False))
    print('Tres clips más largos y cortos:')
    print(a.nlargest(3, 'duracion_seg')[['id','duracion_seg']].to_string(index=False))
    print(a.nsmallest(3, 'duracion_seg')[['id','duracion_seg']].to_string(index=False))
    print('df.shape', d.shape, a.shape, '| primeras cinco filas:')
    display(d.head(5)) if 'display' in globals() else print(d.head(5))
    display(a.head(5)) if 'display' in globals() else print(a.head(5))
    return fig1, fig2, fig3
