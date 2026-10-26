"""Prepara una copia publicable sin originales, correspondencias privadas ni modelos."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,hashlib,json,shutil
import pandas as pd
from pipeline import BASE,DATOS,leer_csv
from validar_publicacion import verificar
from evaluacion import acuerdo_llm,puntuar_predicciones

CSV=['documentos.csv','transcripciones.csv','fuentes.csv','fuentes_audio.csv','seleccion_documentos.csv','descartes.csv','extraccion_llm.csv','resultados_modelos.csv','resumen_modelos.csv','auditoria_llm.csv','resumen_auditoria.csv','revision_privacidad.csv','seudonimizacion_resumen.csv']

def preparar(destino=None):
    verificar();acuerdo_llm();puntuar_predicciones();verificar()
    for name in ['01_extraccion.ipynb','02_evaluacion.ipynb']:
        nb=json.loads((BASE/name).read_text(encoding='utf-8-sig'))
        cells=[c for c in nb['cells'] if c['cell_type']=='code']
        if not cells or any(c.get('execution_count') is None or any(o.get('output_type')=='error' for o in c.get('outputs',[])) for c in cells):raise ValueError('Notebook pendiente: '+name)
    medios=DATOS/'ejemplos_publicos'
    if not medios.exists():medios=DATOS/'ejemplos'
    m=leer_csv(medios/'manifest.csv')
    if set(m.id)!={'doc_002','clip_021'}:raise ValueError('Se requieren los dos ejemplos seleccionados sin nombres.')
    for r in m.itertuples():
        f=medios/r.archivo
        if not str(r.autorizacion).startswith('manual_estudiante') or r.revisado!='si' or hashlib.sha256(f.read_bytes()).hexdigest()!=r.sha256:raise ValueError('Ejemplo sin autorización vigente: '+r.id)
    now=datetime.now(ZoneInfo('America/Lima'))
    out=Path(destino).resolve() if destino else BASE.parent/('tarea_2_publicable_'+now.strftime('%Y%m%d_%H%M%S'))
    if out==BASE or BASE in out.parents:raise ValueError('La copia publicable debe estar fuera del proyecto de trabajo.')
    out.mkdir(parents=True,exist_ok=False)
    def copy(src,rel):
        dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    for f in BASE.glob('*.py'):copy(f,f.name)
    for name in ['README.md','requirements.txt','requirements-inferencia.txt','.gitignore','.gitattributes','01_extraccion.ipynb','02_evaluacion.ipynb']:
        copy(BASE/name,name)
    for f in (BASE/'modelos').glob('*.json'):copy(f,'modelos/'+f.name)
    for name in CSV:copy(DATOS/name,'datos/'+name)
    muestra=leer_csv(DATOS/'muestra_referencias.csv')
    for mod,name in [('documento','documentos.csv'),('audio','transcripciones.csv')]:
        tabla=leer_csv(DATOS/name).set_index('id')
        for i,r in muestra[muestra.modalidad==mod].iterrows():muestra.loc[i,'texto_referencia']=tabla.loc[r.id,'texto_referencia']
    muestra['publicacion']='referencia seudonimizada; distancias en original privado'
    muestra.to_csv(out/'datos/muestra_referencias.csv',index=False,encoding='utf-8-sig')
    copy(medios/'manifest.csv','datos/ejemplos/manifest.csv')
    for r in m.itertuples():copy(medios/r.archivo,'datos/ejemplos/'+r.archivo)
    for f in (DATOS/'graficos').iterdir():
        if f.suffix.lower() in ['.html','.png']:copy(f,'datos/graficos/'+f.name)
    evidencias=BASE/'evidencias_ia'
    for f in evidencias.iterdir():
        if f.is_file() and f.suffix.lower() in ['.png','.jpg','.jpeg','.webp','.txt']:copy(f,'evidencias_ia/'+f.name)
    archivos=[]
    for f in sorted(out.rglob('*')):
        if not f.is_file():continue
        if f.stat().st_size>=100*1024**2:raise ValueError('Archivo mayor de 100 MB: '+f.name)
        archivos.append(dict(archivo=f.relative_to(out).as_posix(),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    (out/'PUBLICACION.json').write_text(json.dumps(dict(fecha=now.isoformat(),archivos=archivos),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Copia publicable:',out)
    print('No confirma despliegue ni cobertura de las capturas; comprobarlos antes de entregar.')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destino');args=p.parse_args();preparar(args.destino)
