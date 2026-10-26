"""Streamlit público: solo CSV revisados, sin cargar modelos de inferencia."""
from pathlib import Path
import hashlib,json,re
import pandas as pd
import plotly.express as px
import streamlit as st
from validar_publicacion import verificar
BASE=Path(__file__).resolve().parent;DATA=BASE/'datos'
st.set_page_config(page_title='Voces y documentos peruanos',page_icon='📚',layout='wide')
st.markdown('<h1 style="text-align:center">¿Del archivo escaneado y la voz al texto buscable?</h1>',unsafe_allow_html=True)
st.caption('Un archivo de documentos peruanos y español peruano. OCR y ASR calculados previamente, referencias manuales y campos extraídos por un LLM local.')

def leer(nombre):
    try:return pd.read_csv(DATA/nombre,dtype=str,keep_default_na=False)
    except (FileNotFoundError,pd.errors.EmptyDataError):return pd.DataFrame()

def descarga(df):return df.to_csv(index=False).encode('utf-8-sig')

def campos(id_,modalidad):
    if E.empty:return None
    e=E[(E.id==id_)&(E.modalidad==modalidad)]
    if e.empty:return None
    try:return json.loads(e.iloc[0].campos_json)
    except (ValueError,TypeError):return {'aviso':'JSON inválido; revisar extracción.'}

def multimedia(id_,modalidad):
    m=leer('ejemplos/manifest.csv')
    if m.empty or not {'id','modalidad','archivo','revisado','sha256'}.issubset(m):return None
    x=m[(m.id==id_)&(m.modalidad==modalidad)&(m.revisado=='si')]
    if len(x)!=1:return None
    p=(DATA/'ejemplos'/x.iloc[0].archivo).resolve()
    if (DATA/'ejemplos').resolve() not in p.parents or not p.is_file():return None
    if hashlib.sha256(p.read_bytes()).hexdigest()!=x.iloc[0].sha256:return None
    return p

def nota_multimedia(id_,modalidad):
    m=leer('ejemplos/manifest.csv')
    if m.empty or 'descripcion' not in m:return ''
    z=m[(m.id==id_)&(m.modalidad==modalidad)]
    return str(z.iloc[0].descripcion) if not z.empty else ''

def por_modelo(df,modalidad,modelo,col_modelo,col_texto):
    if modelo=='Principal':return df.copy()
    r=P[(P.modalidad==modalidad)&(P.modelo==modelo)][['id','texto_predicho']]
    x=df.merge(r,on='id',how='inner',validate='one_to_one');x[col_texto]=x.pop('texto_predicho');x[col_modelo]=modelo;return x

try:verificar()
except (ValueError,KeyError,FileNotFoundError,AttributeError) as error:
    st.warning('Archivo en preparación: '+str(error))
    d,a=leer('documentos.csv'),leer('transcripciones.csv');c=st.columns(2);c[0].metric('Documentos extraídos',len(d));c[1].metric('Clips transcritos',len(a))
    st.info('Las referencias manuales, revisión de privacidad y auditoría se completan en la herramienta local anotar.py. Los contenidos pendientes no se publican aquí.');st.stop()
D,A,E,R,P,AU=[leer(x) for x in ['documentos.csv','transcripciones.csv','extraccion_llm.csv','resumen_modelos.csv','resultados_modelos.csv','auditoria_llm.csv']]
A['duracion_seg']=pd.to_numeric(A.duracion_seg,errors='raise')
cols=st.columns(5);cols[0].metric('Documentos',len(D));cols[1].metric('Minutos de audio',f'{A.duracion_seg.sum()/60:.1f}')
for met,label,c in [('CER','CER · 10 documentos',cols[2]),('WER','WER · 10 clips',cols[3])]:
    x=R[(R.metrica==met)&(R.n.astype(str)=='10')] if not R.empty else pd.DataFrame();c.metric(label,f'{pd.to_numeric(x.valor).min():.3f}' if not x.empty else 'Pendiente')
try:
    from evaluacion import acuerdo_llm
    n,total,acuerdo=acuerdo_llm();cols[4].metric('Acuerdo LLM-humano',f'{100*acuerdo:.0f} %',help=f'{n}/{total} extracciones completamente correctas.')
except (ValueError,FileNotFoundError,KeyError,AttributeError):cols[4].metric('Acuerdo LLM-humano','Pendiente')
principal,docs,audios,evaluacion=st.tabs(['Panorama','Documentos','Audios','Evaluación'])
with principal:
    st.write('El archivo reúne documentos históricos, fotografías y manuscritos, locuciones de OpenSLR 73 y entrevistas callejeras de Lima. Las fotografías conservan sombras, perspectiva o reflejos reales; algunas muestran soporte manuscrito. Los clips compuestos de OpenSLR se identifican como montajes de locuciones.')
    left,right=st.columns(2);t=D.tipo.value_counts().rename_axis('tipo').reset_index(name='documentos')
    left.plotly_chart(px.bar(t,x='tipo',y='documentos',text='documentos',title=f'Los manuscritos representan {100*D.tipo.eq("manuscrito").mean():.0f} % del corpus'),use_container_width=True)
    right.plotly_chart(px.bar(A,x='id',y='duracion_seg',title=f'{len(A)} clips reúnen {A.duracion_seg.sum()/60:.1f} minutos de voz'),use_container_width=True)
    st.subheader('Fuentes y licencias');st.dataframe(leer('fuentes.csv'),hide_index=True,width='stretch')
with docs:
    l,r=st.columns(2);q=l.text_input('Buscar en texto OCR');tipo=r.selectbox('Tipo de documento',['Todos']+sorted(D.tipo.unique()))
    disponibles=sorted(P[P.modalidad=='documento'].modelo.unique()) if not P.empty else []
    modelo=st.selectbox('Modelo OCR',['Principal']+disponibles);x=por_modelo(D,'documento',modelo,'modelo_ocr','texto_ocr')
    if tipo!='Todos':x=x[x.tipo==tipo]
    if q:x=x[x.texto_ocr.str.contains(q,case=False,regex=False)]
    st.caption(f'{len(x)} documentos encontrados. Los modelos alternativos solo tienen los casos de la muestra evaluada.')
    if not x.empty:
        t=x.tipo.value_counts().rename_axis('tipo').reset_index(name='documentos');st.plotly_chart(px.bar(t,x='tipo',y='documentos',title=f'La selección contiene {len(x)} documentos'),use_container_width=True)
    st.dataframe(x,hide_index=True,width='stretch');st.download_button('Descargar documentos filtrados',descarga(x),'documentos_filtrados.csv','text/csv')
    if not x.empty:
        ident=st.selectbox('Explorar documento',x.id.tolist());reg=x[x.id==ident].iloc[0]
        l,r=st.columns([1.3,1]);l.subheader('Texto OCR');l.text(reg.texto_ocr)
        j=campos(ident,'documento');r.subheader('Campos del LLM');r.json(j) if j is not None else r.info('Extracción pendiente.')
        if reg.texto_referencia:
            with st.expander('Referencia manual'):st.text(reg.texto_referencia)
        if not P.empty:st.dataframe(P[(P.id==ident)&(P.modalidad=='documento')][['modelo','cer','latencia_seg']],hide_index=True)
        image=multimedia(ident,'documento')
        if image:st.image(str(image),caption='Ejemplo revisado con permiso de publicación.',width='stretch')
        else:st.caption('Original disponible solo en el corpus local; consulta pública mediante texto y metadatos.')
with audios:
    q=st.text_input('Buscar en transcripción ASR');disponibles=sorted(P[P.modalidad=='audio'].modelo.unique()) if not P.empty else []
    modelo=st.selectbox('Modelo ASR',['Principal']+disponibles);x=por_modelo(A,'audio',modelo,'modelo_asr','texto_asr')
    limite=float(A.duracion_seg.max());rango=st.slider('Duración (segundos)',0.,limite,(0.,limite))
    x=x[x.duracion_seg.between(*rango)]
    if q:x=x[x.texto_asr.str.contains(q,case=False,regex=False)]
    st.caption(f'{len(x)} clips, {x.duracion_seg.sum()/60:.1f} minutos en la selección.')
    if not x.empty:st.plotly_chart(px.bar(x,x='id',y='duracion_seg',title=f'La selección reúne {x.duracion_seg.sum()/60:.1f} minutos'),use_container_width=True)
    st.dataframe(x,hide_index=True,width='stretch');st.download_button('Descargar audios filtrados',descarga(x),'transcripciones_filtradas.csv','text/csv')
    if not x.empty:
        ident=st.selectbox('Explorar audio',x.id.tolist());reg=x[x.id==ident].iloc[0];st.subheader('Transcripción y hablantes');st.text(reg.texto_asr)
        j=campos(ident,'audio');st.json(j) if j is not None else st.info('Extracción pendiente.')
        audio=multimedia(ident,'audio')
        if audio:
            st.audio(str(audio),format={'.ogg':'audio/ogg','.mp3':'audio/mpeg'}.get(audio.suffix.lower(),'audio/wav'))
            st.caption(nota_multimedia(reg.id,'audio'))
        else:st.caption('Sin copia pública de audio autorizada; se conserva el texto y los metadatos.')
        if reg.texto_referencia:
            with st.expander('Referencia manual'):st.text(reg.texto_referencia)
        if not P.empty:
            z=P[(P.id==ident)&(P.modalidad=='audio')];st.dataframe(z[['modelo','wer','latencia_seg','rtf']],hide_index=True)
            with st.expander('Comparar transcripciones'):
                for row in z.itertuples():st.markdown('**'+row.modelo+'**');st.text(row.texto_predicho)
with evaluacion:
    if R.empty:st.info('CER/WER pendientes de referencias manuales completas.')
    else:
        st.dataframe(R,hide_index=True,width='stretch')
        for met in ['CER','WER']:
            z=R[R.metrica==met].copy();z['valor']=pd.to_numeric(z.valor)
            if not z.empty:st.plotly_chart(px.bar(z,x='modelo',y='valor',text='valor',title=f'{met}: menor error en las mismas 10 referencias'),use_container_width=True)
    st.caption('CER/WER calculados en los originales antes de ocultar nombres y agregados por caracteres/palabras de referencia. Las marcas de hablante no se cuentan como palabras. La latencia excluye la carga del modelo; Qwen usa GPU y la línea base ASR usa CPU. La comparación no aísla el efecto del hardware.')
