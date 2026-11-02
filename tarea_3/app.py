"""Dashboard descriptivo ENDES: exclusivamente filas agregadas preestimadas."""

from html import escape
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent
YEARS = list(range(2021, 2026))
DIMENSIONS = {"nacional": "Nacional", "area": "Área", "riqueza": "Riqueza",
              "educacion": "Educación", "edad": "Edad"}
TEAL, INK, ORANGE = "#146475", "#17313B", "#C06028"
PALETTE = ["#C06028", "#376CB0", "#925987", "#48846A", "#8B721E"]
CHART_CONFIG = {"displaylogo": False, "scrollZoom": False,
                "toImageButtonOptions": {"format": "png", "scale": 2}}
EXPECTED_COLUMNS = (
    "anio indicador escenario dimension categoria_id categoria orden n n_anual_valido "
    "n_anual_15_49 n_faltantes_v217_anio estimacion ic95_inf ic95_sup error_estandar "
    "unidad cv_pct precision publicable codigo_departamento n_upm n_estratos gl_diseno "
    "metodo_ic fuente origen hoja_origen fila_excel_origen"
).split()


def number(value, decimals=2):
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def interval(row, suffix="%"):
    return f"IC95 %: {number(row.ic95_inf)}–{number(row.ic95_sup)} {suffix}"


def validate_data(df):
    """Valida el contrato, sin reestimar porcentajes ni intervalos."""
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(len(df) == 125 and list(df.columns) == EXPECTED_COLUMNS,
            "Se requieren las 125 filas y 28 columnas originales.")
    require(sorted(df.anio.unique()) == YEARS, "Se requieren los cinco años 2021–2025.")
    require(df.indicador.eq("identificacion_correcta").all(), "Indicador inesperado.")
    require(not df.duplicated(["anio", "escenario", "dimension", "categoria_id"]).any(),
            "Hay claves de indicadores duplicadas.")
    require(df.escenario.isin(["principal", "sin_feb_mar"]).all(), "Escenario inesperado.")
    expected = {"nacional": 1, "area": 2, "riqueza": 5, "educacion": 4, "edad": 5, "brecha": 2}
    principal = df[df.escenario.eq("principal")]
    require(set(principal.dimension) == set(expected) | {"departamento"}, "Dimensión inesperada.")
    for year in YEARS:
        for dimension, count in expected.items():
            rows = principal[principal.anio.eq(year) & principal.dimension.eq(dimension)]
            require(len(rows) == count, f"Cobertura incompleta: {year}, {dimension}.")
            require(rows.orden.is_unique, "Orden de categorías duplicado.")
        sensitivity = df[df.escenario.eq("sin_feb_mar") & df.anio.eq(year)]
        require(len(sensitivity) == 1 and sensitivity.dimension.eq("nacional").all()
                and sensitivity.categoria_id.eq("total").all(), "Sensibilidad inválida.")
    for dimension in expected:
        base = principal[principal.dimension.eq(dimension) & principal.anio.eq(2021)]
        contract = base[["categoria_id", "categoria", "orden"]].sort_values("orden").reset_index(drop=True)
        for year in YEARS[1:]:
            rows = principal[principal.dimension.eq(dimension) & principal.anio.eq(year)]
            require(rows[contract.columns].sort_values("orden").reset_index(drop=True).equals(contract),
                    "Las categorías o sus etiquetas cambiaron entre años.")
    dep = principal[principal.dimension.eq("departamento")]
    codes = {f"{i:02}" for i in range(1, 26)}
    require(len(dep) == 25 and dep.anio.eq(2025).all(), "Mapa disponible solo para 25 unidades de 2025.")
    require(set(dep.codigo_departamento) == codes and dep.codigo_departamento.is_unique
            and dep.categoria_id.eq(dep.codigo_departamento).all(), "Códigos departamentales inválidos.")
    require(df.loc[~df.dimension.eq("departamento"), "codigo_departamento"].isna().all(),
            "Código territorial en una fila no territorial.")
    require(df.publicable.isin([0, 1]).all(), "Estado de publicación inválido.")
    require(df.n.notna().all() and df.n.gt(0).all() and df.n.mod(1).eq(0).all(), "n inválido.")
    require(df.loc[df.dimension.eq("brecha"), "unidad"].eq("puntos_porcentuales").all()
            and df.loc[~df.dimension.eq("brecha"), "unidad"].eq("porcentaje").all(),
            "Las unidades no corresponden a la dimensión.")
    published = df[df.publicable.eq(1)]
    require(np.isfinite(published[["estimacion", "ic95_inf", "ic95_sup", "error_estandar"]]).all().all(),
            "Faltan estimaciones, IC o errores estándar publicables.")
    require((published.ic95_inf <= published.estimacion).all()
            and (published.estimacion <= published.ic95_sup).all()
            and published.error_estandar.ge(0).all(), "Estimación o IC incoherente.")
    for unit, lower, upper in [("porcentaje", 0, 100), ("puntos_porcentuales", -100, 100)]:
        rows = published[published.unidad.eq(unit)]
        require(rows.ic95_inf.ge(lower).all() and rows.ic95_sup.le(upper).all(), "IC fuera de rango.")
    national = principal[principal.dimension.eq("nacional")].set_index("anio")
    for year in YEARS:
        rows = df[df.anio.eq(year)]
        r = national.loc[year]
        require(rows.n_anual_valido.eq(r.n).all()
                and rows.n_anual_15_49.eq(r.n_anual_15_49).all()
                and rows.n_faltantes_v217_anio.eq(r.n_faltantes_v217_anio).all()
                and r.n + r.n_faltantes_v217_anio == r.n_anual_15_49,
                "Metadatos de muestra anual incoherentes.")


def validate_geo(df, geo):
    features = geo.get("features", [])
    codes = [f["properties"]["CD_DEPA"] for f in features]
    expected = set(df.loc[df.dimension.eq("departamento"), "codigo_departamento"])
    if len(features) != 25 or len(set(codes)) != 25 or set(codes) != expected:
        raise ValueError("La cartografía no coincide uno a uno con los 25 códigos ENDES.")
    for feature in features:
        geometry = shape(feature["geometry"])
        if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError("La cartografía tiene un polígono vacío o inválido.")


@st.cache_data(show_spinner=False)
def load_inputs():
    df = pd.read_csv(ROOT / "data/indicadores_dashboard.csv", encoding="utf-8-sig",
                     dtype={"codigo_departamento": "string", "categoria_id": "string"})
    geo = json.loads((ROOT / "data/peru_departamentos.geojson").read_text(encoding="utf-8"))
    validate_data(df)
    validate_geo(df, geo)
    return df, geo


def select_rows(df, dimension, year=None):
    mask = df.escenario.eq("principal") & df.dimension.eq(dimension)
    if year is not None:
        mask &= df.anio.eq(year)
    return df.loc[mask].sort_values(["orden", "anio"]).copy()


def publishable(rows):
    """Supresión editorial: ausencia de dato nunca se transforma en cero."""
    valid = rows.publicable.eq(1) & rows.n.ge(30)
    valid &= rows[["estimacion", "ic95_inf", "ic95_sup", "error_estandar"]].notna().all(axis=1)
    valid &= rows.precision.isin(["adecuada", "referencial", "contraste_con_ic"])
    valid &= rows.unidad.eq("puntos_porcentuales") | rows.cv_pct.le(30)
    return rows.loc[valid].copy()


def tooltip_rows(rows):
    return [f"<b>{escape(r.categoria)}</b> · {r.anio}<br>"
            f"{number(r.estimacion)} %<br>{interval(r)}<br>"
            f"n = {number(r.n, 0)} (sin ponderar)"
            + (f"<br>CV: {number(r.cv_pct)} % · {escape(r.precision)}" if pd.notna(r.cv_pct) else "")
            for r in rows.itertuples()]


def style_chart(fig, height=400):
    fig.update_layout(template="plotly_white", height=height, font=dict(family="Arial, sans-serif", size=14, color=INK),
                      paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=12, r=20, t=20, b=30),
                      separators=", ", hoverlabel=dict(font_size=14),
                      legend=dict(orientation="h", y=-0.22, x=0, title=None))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#E5ECEE", zeroline=False)
    return fig


def temporal_chart(df, dimension, year):
    fig = go.Figure()
    national = publishable(select_rows(df, "nacional"))
    # Banda nacional: límites originales; las distancias de barras no son IC nuevos.
    fig.add_trace(go.Scatter(x=national.anio.tolist() + national.anio.tolist()[::-1],
                            y=national.ic95_sup.tolist() + national.ic95_inf.tolist()[::-1],
                            fill="toself", fillcolor="rgba(20,100,117,0.10)", line=dict(width=0),
                            hoverinfo="skip", showlegend=False, name="IC95 % nacional"))
    fig.add_trace(go.Scatter(x=national.anio.tolist(), y=national.estimacion.tolist(), mode="lines+markers",
                            name="Nacional", line=dict(color=TEAL, width=3), marker=dict(size=8),
                            text=tooltip_rows(national), hovertemplate="%{text}<extra></extra>"))
    if dimension != "nacional":
        rows = publishable(select_rows(df, dimension))
        for index, (_, group) in enumerate(rows.groupby("categoria_id", sort=False)):
            fig.add_trace(go.Scatter(
                x=group.anio.tolist(), y=group.estimacion.tolist(), mode="lines+markers", name=group.categoria.iloc[0],
                line=dict(color=PALETTE[index], width=2), marker=dict(size=6),
                error_y=dict(type="data", symmetric=False, array=(group.ic95_sup-group.estimacion).tolist(),
                             arrayminus=(group.estimacion-group.ic95_inf).tolist(), thickness=1, width=3),
                text=tooltip_rows(group), hovertemplate="%{text}<extra></extra>"))
    fig.add_vrect(x0=year-0.07, x1=year+0.07, fillcolor=ORANGE, opacity=0.07, line_width=0, layer="below")
    fig.update_xaxes(tickmode="array", tickvals=YEARS, range=[2020.8, 2025.2], title=None)
    fig.update_yaxes(title="Identificación correcta (%)", range=[0, 60], ticksuffix=" %")
    return style_chart(fig, 430)


def bar_chart(df, dimension, year):
    rows = publishable(select_rows(df, dimension, year))
    horizontal = dimension == "educacion"
    labels = rows.categoria.tolist()
    if horizontal:
        # Solo se insertan saltos de línea; se conserva el texto completo de las etiquetas.
        labels = [label.replace("/", "/<br>").replace(" primaria", "<br>primaria") for label in labels]
    else:
        labels = [label.replace(" más ", "<br>más ") for label in labels]
    fig = go.Figure(go.Bar(
        x=rows.estimacion.tolist() if horizontal else labels,
        y=labels if horizontal else rows.estimacion.tolist(), orientation="h" if horizontal else "v",
        marker_color=TEAL, width=0.55,
        cliponaxis=False,
        hovertext=tooltip_rows(rows), hovertemplate="%{hovertext}<extra></extra>",
        **{("error_x" if horizontal else "error_y"): dict(
            type="data", symmetric=False, array=(rows.ic95_sup-rows.estimacion).tolist(),
            arrayminus=(rows.estimacion-rows.ic95_inf).tolist(), color=INK, thickness=1.2, width=4)}))
    for label, row in zip(labels, rows.itertuples()):
        fig.add_annotation(x=row.ic95_sup+1 if horizontal else label,
                           y=label if horizontal else row.ic95_sup+1.7,
                           text=number(row.estimacion) + " %", showarrow=False,
                           xanchor="left" if horizontal else "center", font=dict(size=13, color=INK))
    if horizontal:
        fig.update_xaxes(title="Identificación correcta (%)", range=[0, 65], ticksuffix=" %", showgrid=True)
        fig.update_yaxes(autorange="reversed", title=None, showgrid=False)
    else:
        fig.update_yaxes(title="Identificación correcta (%)", range=[0, 60], ticksuffix=" %")
    return style_chart(fig, 390)


def map_chart(df, geo, code="todos"):
    rows = publishable(select_rows(df, "departamento", 2025))
    colors = [[0, "#ECF4F4"], [0.5, "#62A8B0"], [1, "#124D61"]]
    fig = go.Figure(go.Choroplethmap(
        geojson=geo, featureidkey="properties.CD_DEPA", locations=rows.codigo_departamento.tolist(),
        z=rows.estimacion.tolist(), zmin=0, zmax=60, colorscale=colors,
        marker=dict(line=dict(color="white", width=0.8), opacity=1 if code == "todos" else 0.45),
        text=tooltip_rows(rows), hovertemplate="%{text}<extra></extra>",
        colorbar=dict(title=dict(text="Correcta (%)"), ticksuffix=" %", thickness=12, len=0.75)))
    center, zoom = dict(lon=-75.2, lat=-9.2), 3.65
    if code != "todos":
        selected = rows[rows.codigo_departamento.eq(code)]
        feature = next(f for f in geo["features"] if f["properties"]["CD_DEPA"] == code)
        west, south, east, north = shape(feature["geometry"]).bounds
        center = dict(lon=(west+east)/2, lat=(south+north)/2)
        span = max(east-west, north-south, 0.12)
        zoom = min(9.5, math.log2(180/span))
        if not selected.empty:
            fig.add_trace(go.Choroplethmap(
                geojson={"type": "FeatureCollection", "features": [feature]},
                featureidkey="properties.CD_DEPA", locations=[code], z=selected.estimacion.tolist(),
                zmin=0, zmax=60, colorscale=colors, showscale=False,
                marker=dict(line=dict(color=ORANGE, width=3)), text=tooltip_rows(selected),
                hovertemplate="%{text}<extra></extra>"))
    # Sin teselas, token, topografía remota ni servicios geográficos en ejecución.
    fig.update_layout(map=dict(style="white-bg", center=center, zoom=zoom), height=540,
                      margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="white",
                      font=dict(family="Arial, sans-serif", color=INK), separators=", ")
    return fig


def show_kpi(column, title, row, unit="%"):
    with column, st.container(border=True):
        if publishable(row.to_frame().T).empty:
            st.metric(title, "No publicable")
        else:
            st.metric(title, f"{number(row.estimacion)} {unit}")
            st.caption(interval(row, unit))


def main():
    st.set_page_config(page_title="Período fértil | ENDES 2021–2025", page_icon="📊", layout="wide")
    st.markdown("""<style>
    .stApp { background: #fff; color: #17313B; }
    .block-container { max-width: 1350px; padding-top: 2.6rem; }
    h1 { font-size: clamp(1.8rem, 3.4vw, 2.9rem) !important; letter-spacing: -.035em; }
    h2 { font-size: 1.5rem !important; letter-spacing: -.02em; }
    h3 { font-size: 1.15rem !important; }
    [data-testid="stMetricValue"] { color: #146475; font-size: clamp(1.5rem, 2.3vw, 2rem); }
    .st-key-sample [data-testid="stMetricValue"] { color: #5C6471; }
    .eyebrow { color:#146475; font-size:.8rem; font-weight:700; letter-spacing:.14em; }
    .sample-note { color:#5C6471; font-size:.85rem; }
    @media (max-width: 640px) {
      .block-container { padding: 1.2rem .9rem; }
      [data-testid="stMetricValue"] { font-size: 1.8rem; }
    }
    </style>""", unsafe_allow_html=True)
    st.markdown('<p class="eyebrow">PERÚ · ENDES 2021–2025 · SALUD Y CONOCIMIENTO</p>', unsafe_allow_html=True)
    st.title("¿Quiénes identifican el período fértil en Perú?")
    st.markdown("Identificación correcta del período fértil y diferencias sociodemográficas entre mujeres de **15–49 años**.")
    st.caption("¿Qué proporción identifica correctamente el período fértil y cómo varía según características "
               "sociodemográficas, económicas y territoriales? Encuestas nacionales de hogares particulares; respuestas válidas.")
    st.markdown("**Fuente: INEI, ENDES.** Análisis descriptivo de datos públicos realizado por Víctor Román. "
                "Porcentajes ponderados e intervalos de confianza al 95 % (IC95 %) de un diseño de muestreo complejo.")
    try:
        df, geo = load_inputs()
    except (OSError, ValueError, KeyError) as error:
        st.error(f"No se pueden cargar los datos verificados: {error}")
        st.stop()

    year = st.selectbox("Año de comparación", YEARS, index=4, key="year",
                        help="Actualiza los cuatro KPI, riqueza y educación; resalta el año en la serie. El mapa permanece en 2025.")
    st.caption("El año actualiza los KPI y las barras. El mapa es exclusivamente de 2025.")
    national = select_rows(df, "nacional", year).iloc[0]
    gaps = select_rows(df, "brecha", year).set_index("categoria_id")
    cols = st.columns(4)
    show_kpi(cols[0], f"Identificación correcta · {year}", national)
    with cols[1], st.container(border=True, key="sample"):
        st.metric("Mujeres analizadas", number(national.n, 0))
        st.markdown('<span class="sample-note">Muestra sin ponderar · no es un total poblacional</span>', unsafe_allow_html=True)
    show_kpi(cols[2], "Brecha Q5–Q1", gaps.loc["q5_menos_q1"], "pp")
    show_kpi(cols[3], "Brecha urbana–rural", gaps.loc["urbana_menos_rural"], "pp")
    st.caption("% = porcentaje ponderado. pp = puntos porcentuales. Las brechas y sus IC95 % son contrastes precalculados.")

    st.divider()
    st.subheader("01 · Evolución temporal")
    dimension = st.selectbox("Comparar en la serie", list(DIMENSIONS), index=1, key="dimension",
                             format_func=DIMENSIONS.get,
                             help="Cambia las categorías de la serie; conserva la referencia nacional. No filtra otros gráficos.")
    st.caption("La línea nacional permanece como referencia. La banda nacional y las barras verticales muestran IC95 %. "
               "La franja cálida destaca el año seleccionado.")
    st.plotly_chart(temporal_chart(df, dimension, year), width="stretch", config=CHART_CONFIG, key="temporal")
    st.caption("2021: 2 208 respuestas V217 faltantes (6,65 % sin ponderar), excluidas del denominador. "
               "Serie descriptiva: no se realizan pruebas de cambio entre años.")

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader(f"02 · Quintiles de riqueza · {year}")
        st.caption("De Q1 (más pobre) a Q5 (más rico). Barras con IC95 %.")
        st.plotly_chart(bar_chart(df, "riqueza", year), width="stretch", config=CHART_CONFIG, key="riqueza")
    with right:
        st.subheader(f"03 · Nivel educativo · {year}")
        st.caption("Categorías originales. «Alguna superior» no implica estudios completos.")
        st.plotly_chart(bar_chart(df, "educacion", year), width="stretch", config=CHART_CONFIG, key="educacion")

    st.divider()
    st.subheader("04 · Distribución departamental · 2025")
    st.info("Mapa disponible únicamente para 2025. Seleccionar un departamento amplía y resalta su geometría y "
            "actualiza su ficha. Los KPI, las brechas y las barras conservan su alcance nacional: no existen cruces "
            "departamento × características sociodemográficas en estos datos.")
    departments = select_rows(df, "departamento", 2025)
    labels = dict(zip(departments.codigo_departamento, departments.categoria))
    code = st.selectbox("Departamento del mapa 2025", ["todos"] + list(labels), key="department",
                        format_func=lambda value: "Todas las unidades" if value == "todos" else labels[value])
    map_column, card_column = st.columns([2, 1], gap="large")
    with map_column:
        st.plotly_chart(map_chart(df, geo, code), width="stretch", config=CHART_CONFIG, key="mapa")
        st.caption("Cartografía: [INGEMMET / GEOCATMIN](https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/"
                   "SERV_CARTOGRAFIA_DEMARCACION_WGS84/MapServer/0). Límites referenciales; copia local verificada, "
                   "01/11/2026. Escala fija: 0–60 %. Acerca el mapa para explorar Callao.")
    with card_column, st.container(border=True):
        if code == "todos":
            st.markdown("### 25 unidades administrativas")
            st.markdown("Selecciona una unidad para consultar su estimación de **2025**, IC95 %, muestra y precisión.")
            st.caption("Lima (15) incluye Lima Metropolitana y el resto del departamento. Callao (07) se representa por separado.")
        else:
            row = departments[departments.codigo_departamento.eq(code)].iloc[0]
            st.markdown(f"### {row.categoria} · 2025")
            if publishable(row.to_frame().T).empty:
                st.warning("Estimación no publicable; no se reemplaza por cero.")
            else:
                st.metric("Identificación correcta", number(row.estimacion) + " %")
                st.write(interval(row))
                st.write(f"**n = {number(row.n, 0)}** mujeres · muestra sin ponderar")
                st.write(f"CV: **{number(row.cv_pct)} %** · precisión {row.precision}")
            st.caption(f"Código departamental: {code}. La ficha usa la fila territorial exacta del CSV.")
        st.caption("El color describe la estimación; no demuestra diferencias estadísticamente significativas entre departamentos.")

    st.subheader("Tres resultados de 2025")
    st.markdown("- **33,63 %** identificó correctamente el período fértil (IC95 %: 32,29–34,96 %).\n"
                "- **26,24 pp** de diferencia entre Q5 y Q1: 45,48 % frente a 19,24 % (IC95 % de la brecha: 22,43–30,06 pp).\n"
                "- **15,37 pp** de diferencia urbana–rural: 36,32 % frente a 20,95 % (IC95 % de la brecha: 13,32–17,41 pp).")
    st.markdown("El conocimiento declarado del período fértil **no equivale a identificar individualmente el momento "
                "fisiológico de la ovulación**. Estos resultados describen diferencias entre grupos; no establecen causas.")

    with st.expander("Metodología, fuentes y limitaciones", expanded=False):
        st.markdown("""
**Definición.** Indicador `1(V217=3)`: respuesta recodificada «en medio del ciclo». La opción 04 del
cuestionario corresponde a V217=3. Las otras respuestas válidas (1, 2, 4, 5, 6 y 8) no se clasifican
como correctas; solo 8 significa «no sabe». El complemento del porcentaje correcto no equivale a desconocimiento.

**Población.** Entrevistas individuales completas de mujeres de 15–49 años en hogares particulares,
con V217 y variables de diseño válidas. Se excluyen las mujeres de 12–14 años. No se restringe
por unión, actividad sexual, anticoncepción o embarazo. Los faltantes se excluyen; no se convierten en cero.

**Diseño de encuesta.** Estimaciones del análisis original: pesos V005/1 000 000, UPM V021 y estratos V022,
anidados por año. IC95 % por linealización de Taylor y cuantiles t con grados de libertad del diseño;
ajustes `survey.lonely.psu='adjust'` y `survey.adjust.domain.lonely=TRUE`. Las brechas conservan los
contrastes lineales y sus IC originales. No se promedian porcentajes agregados ni se restan extremos de IC.
El tamaño n cuenta mujeres entrevistadas, sin ponderar; no representa población expandida.

**Categorías.** Riqueza: V190 (Q1–Q5); área: V025; edad: cinco grupos precalculados.
Educación V149: 0–1 sin primaria completa, 2–3 primaria completa/secundaria incompleta,
4 secundaria completa, 5 alguna superior. Departamento V024: 01–25, Lima completa y Callao separado.

**Faltantes en 2021.** De 33 179 mujeres elegibles de 15–49 años, 2 208 no respondieron V217
(6,65 % sin ponderar; 7,31 % ponderado): 601 en febrero y 1 567 en marzo. La muestra principal
es 30 971. El CSV incluye cinco resultados nacionales de sensibilidad `sin_feb_mar`, que excluyen
ambos meses en cada año; no se mezclan con el escenario principal ni resuelven el posible sesgo.

**Límites.** Se reutilizan resultados agregados auditados; esta aplicación no reproduce el procesamiento
completo de microdatos. Los IC heredan el ajuste de 17–21 estratos con una sola UPM por año
(18 en 2025) tras seleccionar la muestra principal. ENDES rota conglomerados y retiene parcialmente
UPM entre años: no se supone independencia entre ediciones ni se prueban cambios temporales.
El mapa se limita a 2025. No hay estimaciones conjuntas por departamento y otros dominios.

**Precisión.** Regla editorial del proyecto, no umbrales atribuidos al INEI: CV ≤15 % adecuada;
15–30 % referencial; CV >30 %, n <30 o varianza no estimable: suprimir. Las brechas tienen IC propios
y CV no aplicable. Las 125 filas originales son publicables. Los datos ausentes no se muestran como cero.

**Fuentes públicas.** [INEI: microdatos y documentación ENDES](https://proyectos.inei.gob.pe/microdatos/Consulta_por_Encuesta.asp),
[ENDES 2025](https://www.gob.pe/institucion/inei/informes-publicaciones/8284085-peru-encuesta-demografica-y-de-salud-familiar-endes-2025),
[ficha técnica 2025](https://cdn.www.gob.pe/uploads/document/file/3041581/8604-ficha-tecnica-2025.pdf),
[cuestionario individual 2023](https://proyectos.inei.gob.pe/iinei/srienaho/Descarga/DocumentosMetodologicos/2023-5/CuestionarioIndividual.pdf).
Acceso documental: 1 de noviembre de 2026. Son resultados de elaboración propia con datos del INEI;
no son estimaciones oficiales del INEI ni resultados publicados en una revista.
""")
    with st.expander("Consultar y descargar los datos agregados"):
        st.caption("Tabla principal del año seleccionado. Excluye sensibilidad y departamentos. Descarga original: "
                   "125 filas con metadatos; incluye la sensibilidad identificada por escenario.")
        visible = df[df.escenario.eq("principal") & df.anio.eq(year) & ~df.dimension.eq("departamento")].copy()
        table = visible[["dimension", "categoria", "n", "estimacion", "ic95_inf", "ic95_sup", "unidad"]].copy()
        for col in ("estimacion", "ic95_inf", "ic95_sup"):
            table[col] = table[col].map(number)
        st.dataframe(table.rename(columns={"estimacion": "Estimación", "ic95_inf": "IC95 % inferior",
                                          "ic95_sup": "IC95 % superior", "n": "n sin ponderar"}), hide_index=True)
        st.download_button("Descargar CSV original completo", (ROOT / "data/indicadores_dashboard.csv").read_bytes(),
                           file_name="indicadores_dashboard.csv", mime="text/csv")
    st.divider()
    st.caption("Fuente: INEI, ENDES. Análisis y visualizaciones: elaboración propia · Víctor Román · "
               "Diplomado de ciencias de la salud, PUCP · Tarea 3. "
               "Implementación asistida por IA; responsabilidad y revisión del autor.")


if __name__ == "__main__":
    main()
