"""Configuración de cachés locales; no modifica HOME ni credenciales."""
from pathlib import Path
import os
BASE=Path(__file__).resolve().parent
CACHE=Path(os.environ.get('TAREA_CACHE',BASE/'modelos/cache'))
TMP=Path(os.environ.get('TAREA_TMP',BASE/'datos/raw/tmp'))
CACHE.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
for k,sub in {'HF_HOME':'huggingface','TORCH_HOME':'torch','PADDLE_HOME':'paddle','PADDLE_PDX_CACHE_HOME':'paddlex'}.items():os.environ.setdefault(k,str(CACHE/sub))
for k in ['TEMP','TMP','TMPDIR']:os.environ[k]=str(TMP)
