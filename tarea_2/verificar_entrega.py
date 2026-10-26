"""Comprueba requisitos medibles; no acredita por sí solo la calidad de la revisión humana."""
from pathlib import Path
import json
from pipeline import BASE,DATOS,leer_csv
from validar_publicacion import verificar
from evaluacion import acuerdo_llm

def comprobar():
    checks=[]
    def add(nombre,ok):checks.append((nombre,bool(ok)))
    d,a=leer_csv(DATOS/'documentos.csv'),leer_csv(DATOS/'transcripciones.csv')
    add('25 documentos y tipos 8/8/9',len(d)>=25 and all(d.tipo.value_counts().get(t,0)>=n for t,n in [('impreso',8),('foto',8),('manuscrito',9)]))
    import pandas as pd
    add('20 clips y 30 minutos',len(a)>=20 and pd.to_numeric(a.duracion_seg).sum()>=1800)
    m=leer_csv(DATOS/'muestra_referencias.csv',['texto_referencia','origen_referencia']);add('20 referencias de procedencia manual',len(m)==20 and m.texto_referencia.str.strip().ne('').all() and m.origen_referencia.eq('manual_estudiante').all())
    r=leer_csv(DATOS/'resumen_modelos.csv',['modalidad','modelo','n']);add('2 modelos por modalidad, 10 casos cada uno',len(r)==4 and set(r.n.astype(str))=={'10'} and r.groupby('modalidad').modelo.nunique().to_dict()=={'audio':2,'documento':2})
    e=leer_csv(DATOS/'extraccion_llm.csv');add('JSON LLM por registro',len(e)==len(d)+len(a) and not e.duplicated(['id','modalidad']).any())
    try:acuerdo_llm();ok=True
    except (ValueError,FileNotFoundError,KeyError):ok=False
    add('Auditoría humana vigente de 20 casos',ok)
    try:verificar();ok=True
    except (ValueError,FileNotFoundError,KeyError):ok=False
    add('Revisión humana vigente de privacidad',ok)
    for file in ['01_extraccion.ipynb','02_evaluacion.ipynb']:
        nb=json.loads((BASE/file).read_text(encoding='utf-8-sig'));cells=[c for c in nb['cells'] if c['cell_type']=='code'];add(file+' ejecutado sin errores',all(c.get('execution_count') is not None and not any(o.get('output_type')=='error' for o in c.get('outputs',[])) for c in cells))
    add('Hay capturas de conversación (revisar cobertura completa)',bool(list((BASE/'evidencias_ia').glob('*.png'))))
    for name,ok in checks:print(('OK       ' if ok else 'PENDIENTE')+' | '+name)
    print('Verificación manual adicional: 3 issues documentadas/cerradas, commits reales y URL de Streamlit pública funcional.')
    return all(x[1] for x in checks)
if __name__=='__main__':raise SystemExit(0 if comprobar() else 1)
