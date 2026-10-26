"""Añade las dos entrevistas naturales del manifiesto de Wikimedia Commons."""
from pathlib import Path
import urllib.parse
import pandas as pd
import soundfile as sf
from bs4 import BeautifulSoup
from faster_whisper import decode_audio
from red import solicitar,descargar
BASE=Path(__file__).resolve().parent

def agregar():
    meta=BASE/'datos/fuentes_audio.csv'
    if not meta.exists():raise FileNotFoundError('Crear primero los 20 clips OpenSLR.')
    d=pd.read_csv(meta,dtype=str,keep_default_na=False)
    for j in [1,2]:
        ident=f'clip_{20+j:03}'
        if ident in set(d.id):continue
        titulo=f'Entrevista {j} en la Av. Rivagüero - El Agustino.ogg'
        pagina='https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(titulo.replace(' ','_'))
        with solicitar(pagina) as rr:s=BeautifulSoup(rr.read().decode(),'html.parser')
        a=s.select_one('.fullMedia a.internal') or s.select_one('.fullImageLink a')
        lic=[x.get_text(' ',strip=True) for x in s.select('.licensetpl_short')]
        if not a or not any(x.startswith('CC BY') or x in ['CC0','Public domain'] for x in lic):raise ValueError('Archivo o licencia no verificados.')
        carpeta=BASE/'datos/raw/audio';carpeta.mkdir(parents=True,exist_ok=True);original=carpeta/(ident+'_original.ogg');descargar(a['href'],original)
        audio=decode_audio(str(original),sampling_rate=16000);sf.write(carpeta/(ident+'.wav'),audio,16000)
        r=dict(id=ident,archivo_audio=f'datos/raw/audio/{ident}.wav',fuente_url=pagina,licencia=' | '.join(lic),multihablante='por_verificar',diarizar='si',procedencia='Entrevista callejera natural de El Agustino, Lima; revisar voz y privacidad antes de publicar',n_voces_fuente='',n_fragmentos='1',duracion_seg=str(round(len(audio)/16000,2)))
        d=pd.concat([d,pd.DataFrame([r])],ignore_index=True);d.to_csv(meta,index=False,encoding='utf-8-sig');print('Añadida:',ident,flush=True)
if __name__=='__main__':agregar()
