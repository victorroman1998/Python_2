"""Dashboard local: streamlit run app.py"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
CATEGORIAS = ["politica", "economia", "deportes", "ciencia_tecnologia"]
NOMBRES = {
    "politica": "Política", "economia": "Economía", "deportes": "Deportes",
    "ciencia_tecnologia": "Ciencia y tecnología",
}

st.set_page_config(page_title="Noticias peruanas", page_icon="🗞️", layout="wide")
st.markdown("<h1 style='text-align:center'>¿Pueden los titulares peruanos convertirse en un clasificador de noticias?</h1>",
            unsafe_allow_html=True)
st.caption("RSS de La República → limpieza y cuatro categorías → etiquetado asistido → "
           "ajuste de DistilBERT → evaluación en un test reservado.")


@st.cache_data
def cargar_datos() -> pd.DataFrame:
    return pd.read_csv(ROOT / "datos" / "noticias.csv", encoding="utf-8-sig")


@st.cache_resource
def cargar_modelo():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    carpeta = ROOT / "modelo"
    modelo_remoto = os.getenv("NEWS_MODEL_REPO", "").strip()
    tiene_local = (carpeta / "config.json").exists() and any(
        (carpeta / nombre).exists() for nombre in ("model.safetensors", "pytorch_model.bin")
    )
    if not tiene_local and not modelo_remoto:
        raise FileNotFoundError("Faltan los pesos locales. Ejecuta 02_clasificacion.ipynb para entrenar el modelo.")
    origen = carpeta if tiene_local else modelo_remoto
    tokenizador = AutoTokenizer.from_pretrained(origen)
    modelo = AutoModelForSequenceClassification.from_pretrained(origen)
    modelo.eval()
    return tokenizador, modelo, torch


archivo = ROOT / "datos" / "noticias.csv"
if not archivo.exists():
    st.error("Falta datos/noticias.csv. Ejecuta primero `python recolectar.py`.")
    st.stop()

df = cargar_datos()
if not set(["titular", "medio", "etiqueta"]).issubset(df):
    st.error("El CSV no contiene las columnas necesarias.")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    medios = st.multiselect("Medio", sorted(df["medio"].dropna().unique()),
                            default=sorted(df["medio"].dropna().unique()))
    categorias = st.multiselect("Categoría", CATEGORIAS, default=CATEGORIAS,
                                format_func=lambda x: NOMBRES[x])

filtrado = df[df["medio"].isin(medios) & df["etiqueta"].isin(categorias)].copy()
metricas = ROOT / "modelo" / "metrics.json"
resultados = json.loads(metricas.read_text(encoding="utf-8")) if metricas.exists() else {}
f1 = resultados.get("test", {}).get("f1_macro")
acuerdo = resultados.get("auditoria", {}).get("acuerdo")
c1, c2, c3 = st.columns(3)
c1.metric("Noticias recolectadas", len(df))
c2.metric("F1 macro en test", f"{f1:.3f}" if f1 is not None else "Pendiente")
c3.metric("Acuerdo LLM / humano", f"{acuerdo:.0%}" if acuerdo is not None else "Pendiente")

st.subheader("Exploración de noticias")
conteo = filtrado["etiqueta"].value_counts().reindex(CATEGORIAS, fill_value=0).reset_index()
conteo.columns = ["categoria", "noticias"]
conteo["categoria"] = conteo["categoria"].map(NOMBRES)
fig = px.bar(conteo, x="categoria", y="noticias", color="categoria",
             title="Cantidad de noticias por categoría con los filtros actuales")
st.plotly_chart(fig, width="stretch")
st.dataframe(filtrado, width="stretch", hide_index=True)
st.download_button("Descargar selección CSV", filtrado.to_csv(index=False).encode("utf-8-sig"),
                   "noticias_filtradas.csv", "text/csv")

st.subheader("Prueba un titular nuevo")
titular = st.text_input("Escribe o pega un titular", max_chars=300)
if st.button("Clasificar", type="primary"):
    if not titular.strip():
        st.warning("Escribe un titular para clasificarlo.")
    else:
        try:
            tokenizador, modelo, torch = cargar_modelo()
            entrada = tokenizador(titular.strip(), return_tensors="pt", truncation=True, max_length=128)
            with torch.inference_mode():
                probabilidades = torch.softmax(modelo(**entrada).logits, dim=-1)[0]
            indice = int(torch.argmax(probabilidades))
            etiqueta = modelo.config.id2label[indice]
            st.success(f"Categoría: {NOMBRES.get(etiqueta, etiqueta)}")
            st.metric("Probabilidad estimada", f"{float(probabilidades[indice]):.1%}")
            st.caption("La puntuación del modelo no está calibrada como certeza estadística.")
        except (FileNotFoundError, OSError) as exc:
            st.error(str(exc))
