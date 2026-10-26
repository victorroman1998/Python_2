"""Herramienta LOCAL: referencias manuales, privacidad y auditoría. No desplegar en Cloud."""
from __future__ import annotations
import hashlib,json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import pandas as pd
import streamlit as st
from pipeline import BASE,DATOS,DOC_CSV,AUDIO_CSV,leer_csv,guardar_csv,normalizar_ruta
from evaluacion import MUESTRA,AUDITORIA,EXTRACCIONES,preparar_auditoria
from validar_publicacion import estado,contenido_revision,huella,RUTA
st.set_page_config(page_title='Revisión manual · Tarea 2',page_icon='✍️',layout='wide')
st.title('Tu revisión manual de la Tarea 2')
st.caption('Aplicación local. Los originales y borradores permanecen en este equipo. No marques una revisión sin haberla realizado.')
modo=st.sidebar.radio('Paso',['1. Transcribir referencias','2. Revisar privacidad','3. Auditar campos LLM'])

def respaldo(path):
    if path.exists():
        folder=DATOS/'_privado/historial_anotacion';folder.mkdir(parents=True,exist_ok=True)
        now=datetime.now(ZoneInfo('America/Lima')).strftime('%Y%m%d_%H%M%S_%f')
        (folder/(now+'_'+path.name)).write_bytes(path.read_bytes())

def original(reg):
    p=normalizar_ruta(reg['archivo'])
    if not p.is_file():st.warning('Original local no encontrado.');return
    if reg['modalidad']=='documento':st.image(str(p),caption=reg['id'],width='stretch')
    else:st.audio(str(p),format='audio/wav')

if modo.startswith('1.'):
    if not MUESTRA.exists():st.info('La muestra se genera al terminar extracción y congelar el corpus.');st.stop()
    m=leer_csv(MUESTRA)
    st.info('Transcribe el contenido que puedas leer u oír, sin copiar salidas de OCR/ASR ni textos de OpenSLR. Registra lo ilegible en notas y avisa para reemplazarlo; no inventes palabras. Las marcas de hablante no son necesarias para WER.')
    n=int(m.texto_referencia.str.strip().ne('').sum());st.progress(n/20,text=f'{n}/20 referencias guardadas')
    key=st.selectbox('Archivo a transcribir',m.id.tolist());r=m[m.id==key].iloc[0]
    left,right=st.columns([1.2,1]);
    with left:original(r)
    with right:
        st.write('Modalidad:',r.modalidad,'· Tipo:',r.tipo)
        with st.form('manual_'+key):
            texto=st.text_area('Tu transcripción manual',r.texto_referencia,height=400)
            realizada=st.checkbox('La transcripción fue realizada por mí, leyendo o escuchando este original.')
            if st.form_submit_button('Guardar referencia'):
                if not realizada or not texto.strip():st.error('Completa una referencia y confirma su procedencia manual.')
                else:
                    respaldo(MUESTRA);m.loc[m.id==key,['texto_referencia','origen_referencia','fecha_anotacion']]=[texto.strip(),'manual_estudiante',datetime.now(ZoneInfo('America/Lima')).isoformat()];guardar_csv(m,MUESTRA);st.success('Referencia manual guardada.');st.rerun()
    st.caption('Las predicciones automáticas se ocultan en esta pantalla para mantener independiente la referencia.')
elif modo.startswith('2.'):
    rev=estado();d,a=leer_csv(DOC_CSV),leer_csv(AUDIO_CSV)
    if rev.empty:st.info('Primero terminar la extracción.');st.stop()
    st.info('Revisa nombres, DNI, correos, teléfonos y direcciones. Edita los textos para seudonimizar antes de marcarlos. Si hay predicciones alternativas o JSON, también forman parte de la revisión. Cambiar el contenido vuelve a dejar la revisión pendiente.')
    st.progress(float(rev.revisado.str.lower().isin(['si','sí']).mean()),text='Avance de privacidad')
    ident=st.selectbox('Registro',rev.id.tolist());rr=rev[rev.id==ident].iloc[0];tabla=d if rr.modalidad=='documento' else a;col='texto_ocr' if rr.modalidad=='documento' else 'texto_asr';reg=tabla[tabla.id==ident].iloc[0]
    with st.form('privacidad_'+ident):
        texto=st.text_area('Texto publicable',reg[col],height=260);referencia=st.text_area('Referencia manual publicable',reg.texto_referencia,height=180)
        obs=st.text_input('Observaciones',rr.observaciones)
        if st.form_submit_button('Guardar correcciones de texto'):
            path=DOC_CSV if rr.modalidad=='documento' else AUDIO_CSV;respaldo(path);tabla.loc[tabla.id==ident,[col,'texto_referencia']]=[texto,referencia];guardar_csv(tabla,path)
            if MUESTRA.exists():
                m=leer_csv(MUESTRA);sel=(m.id==ident)&(m.modalidad==rr.modalidad)
                if sel.any():m.loc[sel,'texto_referencia']=referencia;respaldo(MUESTRA);guardar_csv(m,MUESTRA)
            estado();st.success('Correcciones guardadas. Regenerar LLM/métricas si cambió su entrada.');st.rerun()
    payload=json.loads(contenido_revision(rr.modalidad,reg.to_dict()))
    with st.expander('Revisar también JSON y predicciones publicables',expanded=True):st.json(payload)
    with st.form('confirmar_'+ident):
        revisado=st.checkbox('He revisado todos estos textos y su licencia; no contienen datos personales sin seudonimizar.')
        if st.form_submit_button('Marcar revisión humana'):
            if not revisado:st.error('Falta la revisión humana.')
            else:
                rev=estado();mask=(rev.id==ident)&(rev.modalidad==rr.modalidad);rev.loc[mask,['revisado','observaciones']]=['si',obs];respaldo(RUTA);guardar_csv(rev,RUTA);st.success('Revisión guardada para el contenido exacto mostrado.');st.rerun()
    with st.expander('Autorizar un ejemplo multimedia para la aplicación pública'):
        path=normalizar_ruta(reg['archivo'] if rr.modalidad=='documento' else reg['archivo_audio'])
        if path.is_file():
            if rr.modalidad=='documento': st.image(str(path),caption='Revisar también el contenido de la imagen, no solo su OCR.',width='stretch')
            else: st.audio(str(path),format='audio/wav')
            with st.form('medio_'+ident):
                permiso=st.checkbox('He revisado el archivo completo; su licencia permite redistribuirlo y no revela datos personales sin protección.')
                if st.form_submit_button('Guardar ejemplo autorizado'):
                    if not permiso: st.error('La publicación del ejemplo requiere tu revisión.')
                    else:
                        import shutil
                        folder=DATOS/'ejemplos';folder.mkdir(exist_ok=True)
                        dest=folder/(ident+('.jpg' if rr.modalidad=='documento' else '.wav'));shutil.copy2(path,dest)
                        manifest=folder/'manifest.csv';cols=['id','modalidad','archivo','licencia','revisado','sha256','autorizacion']
                        old=leer_csv(manifest,cols);old=old[~((old.id==ident)&(old.modalidad==rr.modalidad))]
                        f=leer_csv(DATOS/'fuentes.csv');lic=f[(f.id==ident)&(f.modalidad==rr.modalidad)].iloc[0].licencia
                        nuevo=dict(id=ident,modalidad=rr.modalidad,archivo=dest.name,licencia=lic,revisado='si',sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),autorizacion='manual_estudiante')
                        guardar_csv(pd.concat([old,pd.DataFrame([nuevo])],ignore_index=True),manifest);st.success('Ejemplo guardado para el dashboard. No se ha subido a ningún servidor.')
else:
    if not EXTRACCIONES.exists() or leer_csv(EXTRACCIONES).empty:st.info('Faltan extracciones LLM reales.');st.stop()
    audit=preparar_auditoria();n=int(audit.completamente_correcto.isin(['si','no']).sum());st.progress(n/20,text=f'{n}/20 auditorías guardadas')
    ident=st.selectbox('Extracción a auditar',audit.id.tolist());r=audit[audit.id==ident].iloc[0]
    tabla=leer_csv(DOC_CSV if r.modalidad=='documento' else AUDIO_CSV);col='texto_ocr' if r.modalidad=='documento' else 'texto_asr'
    st.write('Texto fuente');st.write(tabla[tabla.id==ident].iloc[0][col]);st.write('Campos del LLM');st.json(json.loads(r.campos_json))
    st.info('Una extracción es completamente correcta si modalidad, tema, resumen y cada campo están sustentados en el texto. Los ausentes deben ser null; las citas deben ser literales. Un solo campo inventado o incorrecto hace que el caso sea «no».')
    with st.form('auditoria_'+ident):
        correcto=st.radio('¿La extracción es completamente correcta?',['Sin revisar','Sí','No'],index=0)
        nota=st.text_area('Error encontrado o comprobación realizada',r.observacion_auditor)
        if st.form_submit_button('Guardar auditoría humana'):
            if correcto=='Sin revisar':st.error('Selecciona un resultado después de revisar.')
            else:
                respaldo(AUDITORIA);audit.loc[audit.id==ident,['completamente_correcto','observacion_auditor']]=['si' if correcto=='Sí' else 'no',nota];guardar_csv(audit,AUDITORIA);st.success('Auditoría guardada.');st.rerun()
