from pathlib import Path
from runpy import run_path
from zipfile import ZipFile

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Polygon, box

import enaho


@pytest.fixture
def modulo_02_y_34():
    hogares = pd.DataFrame({
        "conglome": list(range(1, 26)), "vivienda": "001", "hogar": "11",
        "ano": "2024", "ubigeo": [f"{i:02}0101" for i in range(1, 26)],
        "estrato": [5, 6] * 12 + [5], "dominio": 1,
        "pobreza": [1, 2, 3, 3, 3] * 5, "factor07": 2.0, "mieperho": 3,
    })
    miembros = hogares[enaho.LLAVE_HOGAR + enaho.GEOGRAFIA].assign(
        codperso="01", p204=1, p205=2, p206=np.nan, p207=2, facpob07=3.0,
    )
    return miembros, hogares


def test_leer_stata_por_nombre_y_preservar_ceros(tmp_path):
    dta = tmp_path / "base.dta"
    original = pd.DataFrame({"aÑo": ["2024"], "UBIGEO": ["070101"], "pobreza": [2]})
    original.to_stata(dta, write_index=False, version=118,
                      value_labels={"pobreza": {2: "pobre no extremo"}})
    ruta = tmp_path / "modulo.zip"
    with ZipFile(ruta, "w") as zip_modulo:
        zip_modulo.writestr("directorio/otro.dta", "no es el archivo solicitado")
        zip_modulo.write(dta, "directorio/base.dta")
    datos = enaho.leer_modulo(ruta, "base.dta", ["ano", "ubigeo", "pobreza"], [])
    assert datos.iloc[0].tolist() == ["2024", "070101", 2]


def test_residentes_incluye_ambas_ramas_y_excluye_ausentes_y_faltantes():
    miembros = pd.DataFrame({
        "p204": [1, 1, 2, 2, np.nan],
        "p205": [2, 1, np.nan, np.nan, np.nan],
        "p206": [np.nan, np.nan, 1, 2, np.nan],
    })
    assert enaho.residentes(miembros).index.tolist() == [0, 2]


def test_residencia_rechaza_respuesta_obligatoria_faltante():
    miembros = pd.DataFrame({"p204": [2], "p205": [np.nan], "p206": [np.nan]})
    with pytest.raises(ValueError, match="p206"):
        enaho.residentes(miembros)


@pytest.mark.parametrize("tabla", ["miembros", "hogares"])
def test_rechaza_llaves_duplicadas_despues_de_normalizar(modulo_02_y_34, tabla):
    miembros, hogares = modulo_02_y_34
    if tabla == "miembros":
        duplicado = miembros.iloc[[0]].assign(conglome="000001", codperso=1)
        miembros = pd.concat([miembros, duplicado])
    else:
        hogares = pd.concat([hogares, hogares.iloc[[0]].assign(conglome="000001")])
    with pytest.raises(ValueError, match="llave duplicada"):
        enaho.preparar_bases(miembros, hogares, [])


def test_unir_acepta_varias_personas_del_mismo_hogar(modulo_02_y_34):
    miembros, hogares = modulo_02_y_34
    miembros = pd.concat([miembros, miembros.iloc[[0]].assign(codperso="02")])
    personas, _ = enaho.preparar_bases(miembros, hogares, [])
    assert len(personas) == 26
    assert personas.loc[personas.conglome.eq("000001"), "codperso"].tolist() == ["01", "02"]
    assert personas.loc[personas.conglome.eq("000001"), "pobreza"].tolist() == [1, 1]


def test_unir_rechaza_residente_sin_hogar(modulo_02_y_34):
    miembros, hogares = modulo_02_y_34
    with pytest.raises(ValueError, match="1 residentes sin hogar"):
        enaho.preparar_bases(miembros, hogares.iloc[1:].copy(), [])


def test_unir_rechaza_geografia_discordante(modulo_02_y_34):
    miembros, hogares = modulo_02_y_34
    miembros.loc[0, "ubigeo"] = "020101"
    with pytest.raises(ValueError, match="discrepancias en ubigeo"):
        enaho.preparar_bases(miembros, hogares, [])


def test_indicadores_aplican_categorias_y_denominador_correctos(modulo_02_y_34):
    miembros, hogares = modulo_02_y_34
    miembros.loc[0, "facpob07"] = 30.0
    hogares.loc[0, "mieperho"] = 6
    personas, sumaria = enaho.preparar_bases(miembros, hogares, [])
    assert personas.pobre.iloc[:3].tolist() == [True, True, False]
    assert personas.area.iloc[:2].tolist() == ["U", "R"]
    assert personas.departamento.iloc[[6, 14]].tolist() == ["07", "15"]
    assert personas.sexo.unique().tolist() == ["2"]

    directa = enaho.estimar(personas, personas.facpob07, "personas").query("grupo == 'nacional'").iloc[0]
    control = enaho.estimar(sumaria, sumaria.factor07 * sumaria.mieperho, "sumaria")
    assert directa.n_observaciones == 25
    assert directa.poblacion_expandida == 102
    assert directa.poblacion_pobre_expandida == 57
    assert directa.pobreza_pct == pytest.approx(100 * 57 / 102)
    assert "sexo" not in set(control.grupo)
    assert control.query("grupo == 'nacional'").iloc[0].pobreza_pct == pytest.approx(100 * 66 / 156)


@pytest.mark.parametrize(("columna", "valor", "mensaje"), [
    ("ubigeo", None, "ubigeo"),
    ("estrato", 9, "estrato inválido"),
    ("ano", "2023", "año distinto"),
    ("facpob07", 0, "pesos"),
    ("facpob07", np.inf, "pesos"),
    ("p207", np.nan, "sexo inválido"),
])
def test_rechaza_entradas_invalidas(modulo_02_y_34, columna, valor, mensaje):
    miembros, hogares = modulo_02_y_34
    miembros.loc[0, columna] = valor
    with pytest.raises(ValueError, match=mensaje):
        enaho.preparar_bases(miembros, hogares, [])


def test_pobreza_faltante_o_fuera_de_catalogo(modulo_02_y_34):
    miembros, hogares = modulo_02_y_34
    hogares.loc[0, "pobreza"] = 4
    with pytest.raises(ValueError, match="pobreza inválido"):
        enaho.preparar_bases(miembros, hogares, [])


def test_normaliza_codigos_de_geojson_sin_confundir_ambitos():
    codigos = pd.Series([7, "07", 15.0, " 01 "])
    assert enaho.normalizar_codigo(codigos, 2, "departamento").tolist() == ["07", "07", "15", "01"]
    with pytest.raises(ValueError, match="inválidos"):
        enaho.normalizar_codigo(pd.Series(["101", "01A", None]), 2, "departamento")


@pytest.fixture(scope="module")
def unir_geografia():
    ruta = enaho.RAIZ / ".claude/skills/mapeando-enaho/scripts/mapear.py"
    return run_path(str(ruta))["unir_geografia"]


@pytest.fixture
def geografia_y_tasas():
    geografia = gpd.GeoDataFrame(
        {"FIRST_IDDP": range(1, 26), "NOMBDEP": "Nombre irrelevante"},
        geometry=[box(i, 0, i + 0.5, 1) for i in range(25)], crs=4326,
    )
    tasas = pd.DataFrame({"codigo": list(enaho.DEPARTAMENTOS), "pobreza_pct": range(1, 26)})
    return geografia, tasas.iloc[::-1]


def test_mapa_integra_por_codigo_y_conserva_lima_callao(unir_geografia, geografia_y_tasas):
    mapa = unir_geografia(*geografia_y_tasas)
    assert isinstance(mapa, gpd.GeoDataFrame)
    assert len(mapa) == 25 and mapa.geometry.is_valid.all()
    assert mapa.set_index("codigo").loc[["07", "15"], "pobreza_pct"].tolist() == [7, 15]


@pytest.mark.parametrize("problema", ["codigo", "duplicado", "sin_tasa", "invalida", "vacia"])
def test_mapa_rechaza_faltantes_duplicados_y_geometrias_invalidas(unir_geografia, geografia_y_tasas, problema):
    geografia, tasas = geografia_y_tasas
    if problema == "codigo":
        geografia = geografia.drop(columns="FIRST_IDDP")
    elif problema == "duplicado":
        geografia.loc[0, "FIRST_IDDP"] = 2
    elif problema == "sin_tasa":
        tasas = tasas.assign(pobreza_pct=np.nan)
    elif problema == "invalida":
        geografia.loc[0, "geometry"] = Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)])
    else:
        geografia.loc[0, "geometry"] = None
    with pytest.raises(ValueError):
        unir_geografia(geografia, tasas)


def test_validacion_nacional_acepta_limite_y_detecta_desvio():
    indicadores = pd.DataFrame({
        "metodo": ["personas", "sumaria"], "grupo": "nacional", "codigo": "PE",
        "ambito": "Perú", "pobreza_pct": [27.5, 27.58],
    })
    assert all(pasa for pasa, _ in enaho.contrastar(indicadores, {}, ["nacional"]))
    indicadores.loc[0, "pobreza_pct"] = 27.499
    assert not enaho.contrastar(indicadores, {}, ["nacional"])[0][0]


def test_validacion_fallida_bloquea_ambos_consumidores(tmp_path):
    salidas = tmp_path / "salidas"
    with pytest.raises(FileNotFoundError, match="966-Modulo34.zip"):
        enaho.limpiar(tmp_path / "datos", salidas, descargar=False)
    assert "Estado: RECHAZADO" in (salidas / enaho.VALIDACION).read_text(encoding="utf-8")
    assert not (salidas / enaho.PARQUET).exists()
    with pytest.raises(ValueError, match="Ejecuta primero limpiando-enaho"):
        enaho.cargar_indicadores_validados(salidas)


@pytest.mark.parametrize("archivo", [enaho.PARQUET, enaho.INDICADORES])
def test_consumidores_rechazan_archivo_distinto_del_lote_aprobado(tmp_path, archivo):
    parquet = tmp_path / enaho.PARQUET
    csv = tmp_path / enaho.INDICADORES
    pd.DataFrame({"codigo": ["07"]}).to_parquet(parquet)
    csv.write_text("codigo,pobreza_pct\n07,33.7\n", encoding="utf-8")
    informe = tmp_path / enaho.VALIDACION
    registro = [f"SHA-256 {enaho.huella(ruta)} {ruta.name}" for ruta in (parquet, csv)]
    enaho.escribir_validacion(informe, "APROBADO", registro)
    assert enaho.cargar_indicadores_validados(tmp_path).codigo.tolist() == ["07"]
    (tmp_path / archivo).write_text("contenido alterado", encoding="utf-8")
    with pytest.raises(ValueError, match="no corresponde al lote aprobado"):
        enaho.cargar_indicadores_validados(tmp_path)
