"""Revisión humana ligada al contenido exacto que mostraría el dashboard."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
from pipeline import DATOS, DOC_CSV, AUDIO_CSV, guardar_csv, leer_csv
RUTA=DATOS/'revision_privacidad.csv'
COLS=['id','modalidad','hash_texto','revisado','observaciones']

def huella(texto):return hashlib.sha256(str(texto).encode('utf-8')).hexdigest()

def contenido_revision(modalidad, registro):
    """Incluye referencias, predicciones alternativas y LLM: cambiar cualquiera invalida revisión."""
    col='texto_ocr' if modalidad=='documento' else 'texto_asr'
    payload={'texto':str(registro.get(col,'')),'referencia':str(registro.get('texto_referencia',''))}
    for nombre,campos in [('resultados_modelos.csv',['modelo','texto_predicho']),('extraccion_llm.csv',['campos_json','modelo_llm'])]:
        t=leer_csv(DATOS/nombre,["id","modalidad"]+campos)
        if nombre=="resultados_modelos.csv" and t.empty:
            t=leer_csv(DATOS/"_privado/predicciones_modelos.csv",["id","modalidad"]+campos)
        if not t.empty and {'id','modalidad'}.issubset(t):
            t=t[(t.id==registro['id'])&(t.modalidad==modalidad)].copy()
            if nombre=='resultados_modelos.csv' and 'texto_predicho' in t:
                from seudonimizar import aplicar_texto
                t['texto_predicho']=t.texto_predicho.map(aplicar_texto)
            payload[nombre]=sorted(t.reindex(columns=campos,fill_value='').to_dict('records'),key=lambda x:json.dumps(x,sort_keys=True))
    # Git puede cambiar LF por CRLF en Windows sin modificar el texto.
    def lineas(obj):
        if isinstance(obj,str):return obj.replace('\r\n','\n').replace('\r','\n')
        if isinstance(obj,list):return [lineas(v) for v in obj]
        if isinstance(obj,dict):return {k:lineas(v) for k,v in obj.items()}
        return obj
    return json.dumps(lineas(payload),ensure_ascii=False,sort_keys=True)

def estado(guardar=True):
    actual=leer_csv(RUTA,COLS);objetivo=[]
    for clase,ruta in [('documento',DOC_CSV),('audio',AUDIO_CSV)]:
        for r in leer_csv(ruta).to_dict('records'):
            h=huella(contenido_revision(clase,r))
            match=actual[(actual.id==r['id'])&(actual.modalidad==clase)&(actual.hash_texto==h)]
            revision,obs=('pendiente','') if match.empty else match.iloc[0][['revisado','observaciones']]
            objetivo.append(dict(id=r['id'],modalidad=clase,hash_texto=h,revisado=revision,observaciones=obs))
    result=pd.DataFrame(objetivo,columns=COLS)
    if guardar:guardar_csv(result,RUTA)
    return result

def verificar():
    d,a=leer_csv(DOC_CSV),leer_csv(AUDIO_CSV)
    if d.empty or a.empty:raise ValueError('Faltan corpus procesados.')
    if d.id.duplicated().any() or a.id.duplicated().any():raise ValueError('IDs duplicados en el corpus.')
    conteos=d.tipo.value_counts()
    if any(conteos.get(t,0)<n for t,n in [('impreso',8),('foto',8),('manuscrito',9)]):raise ValueError('Se necesitan 8 impresos, 8 fotos y 9 manuscritos.')
    dur=pd.to_numeric(a.duracion_seg,errors='coerce')
    if len(a)<20 or dur.isna().any() or (dur<=0).any() or dur.sum()<1800:raise ValueError('Faltan 20 clips válidos y 30 minutos.')
    if not (pd.to_numeric(a.n_hablantes,errors='coerce')>=2).any():raise ValueError('Falta diarización de un audio multihablante.')
    if d.texto_ocr.str.strip().eq('').any() or a.texto_asr.str.strip().eq('').any():raise ValueError('Hay textos vacíos: revisar el original y sustituir casos ilegibles o sin voz.')
    rev=estado(guardar=False)
    faltan=rev[~rev.revisado.str.lower().isin(['si','sí'])]
    if not faltan.empty:raise ValueError('Revisión humana pendiente o desactualizada: '+', '.join(faltan.id.head(10)))
    f=leer_csv(DATOS/'fuentes.csv',['id','modalidad','fuente_url','licencia','acceso'])
    if f.duplicated(['id','modalidad']).any():raise ValueError('Fuentes duplicadas.')
    esperados={('documento',i) for i in d.id}|{('audio',i) for i in a.id}
    presentes={(r.modalidad,r.id) for r in f.itertuples() if r.fuente_url.strip() and r.licencia.strip() and r.acceso.strip()}
    if not esperados.issubset(presentes):raise ValueError('Fuentes/licencias/instrucciones de acceso incompletas por ID.')
    return True

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verificar',action='store_true');args=p.parse_args()
    if args.verificar:verificar();print('Revisión humana vigente para todos los textos publicables.')
    else:
        r=estado();print(f'{len(r)} registros; {r.revisado.str.lower().isin(["si","sí"]).sum()} revisados. Archivo: {RUTA}')
