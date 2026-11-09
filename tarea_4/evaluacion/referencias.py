"""Reconstruye el patrón desde los JSON oficiales y los Stata originales."""

import argparse
import csv
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{}/json/2020-1/2024-12/esp"
INEI = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/"
SERIES = {"PN09822PM": "IPC Alimentos y Bebidas", "PN01273PM": "IPC"}
MODULOS = ("966-Modulo02.zip", "966-Modulo34.zip")
MESES = "Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic".split()
LLAVE = ["conglome", "vivienda", "hogar"]


def descargar_series(destino):
    from urllib.request import urlopen

    destino.mkdir(parents=True, exist_ok=True)
    for codigo in SERIES:
        with urlopen(BCRP.format(codigo), timeout=30) as respuesta:
            contenido = respuesta.read()
        (destino / f"{codigo}.json").write_bytes(contenido)


def serie(datos, codigo):
    contenido = json.loads((datos / f"{codigo}.json").read_bytes())
    meta = contenido["config"]["series"]
    nombre = f"Índice de precios Lima Metropolitana (var% 12 meses) - {SERIES[codigo]}"
    if len(meta) != 1 or meta[0]["name"] != nombre:
        raise ValueError(f"Metadatos inesperados para {codigo}: {meta}")
    valores = {}
    for fila in contenido["periods"]:
        mes, anio = fila["name"].split(".")
        periodo = f"{anio}-{MESES.index(mes) + 1:02}"
        valores[periodo] = Decimal(fila["values"][0])
    meses = {f"{a}-{m:02}" for a in range(2020, 2025) for m in range(1, 13)}
    if len(contenido["periods"]) != 60 or valores.keys() != meses:
        raise ValueError(f"Se requieren los 60 meses completos de {codigo}")
    return valores, nombre


def leer_stata(archivo, nombre, columnas):
    with ZipFile(archivo) as zip_modulo:
        ruta, = [ruta for ruta in zip_modulo.namelist() if ruta.split("/")[-1] == nombre]
        with zip_modulo.open(ruta) as origen:
            return pd.read_stata(origen, columns=columnas, convert_categoricals=False)


def pobreza(datos):
    personas = leer_stata(datos / MODULOS[0], "enaho01-2024-200.dta",
                          LLAVE + ["ubigeo", "estrato", "p204", "p205", "p206", "p207", "facpob07"])
    hogares = leer_stata(datos / MODULOS[1], "sumaria-2024.dta", LLAVE + ["pobreza"])
    residentes = personas.query("(p204 == 1 and p205 == 2) or (p204 == 2 and p206 == 1)")
    base = residentes.join(hogares.set_index(LLAVE), on=LLAVE, validate="m:1")
    if (len(base) != 108664 or not base.pobreza.isin([1, 2, 3]).all()
            or not base.estrato.isin(range(1, 9)).all() or not base.p207.isin([1, 2]).all()
            or base.facpob07.isna().any() or not base.facpob07.gt(0).all()):
        raise ValueError("Universo, categorías o pesos inesperados en ENAHO")
    base["peso"] = base.facpob07.astype("float64")
    base["peso_pobre"] = base.peso * base.pobreza.isin([1, 2])
    base["rural"] = base.estrato.ge(6)
    base["departamento"] = base.ubigeo.astype(str).str.zfill(6).str[:2]

    def tasas(grupo):
        totales = base.groupby(grupo)[["peso_pobre", "peso"]].sum()
        return 100 * totales.peso_pobre / totales.peso

    departamento = tasas("departamento")
    if len(departamento) != 25:
        raise ValueError("Se requieren 25 ámbitos, incluyendo Callao separado")
    return (100 * base.peso_pobre.sum() / base.peso.sum(),
            tasas("rural"), tasas("p207"), departamento)


def criterio(valor, unidad, tolerancia="0"):
    return {"esperado": str(valor), "unidad": unidad, "tolerancia_absoluta": tolerancia}


def preguntas(macro, datos):
    alimentos, _ = serie(macro, "PN09822PM")
    ipc, _ = serie(macro, "PN01273PM")
    mes_pico = max(alimentos, key=alimentos.get)
    pico = alimentos[mes_pico]
    alimentos_dic = alimentos["2024-12"]
    ipc_dic = ipc["2024-12"]
    nacional, area, sexo, departamento = pobreza(datos)
    rural, urbana = area[True], area[False]
    hombres, mujeres = sexo[1], sexo[2]
    alto, bajo = departamento.idxmax(), departamento.idxmin()
    nombres = {"06": "Cajamarca", "11": "Ica", "21": "Puno"}
    if alto not in nombres or bajo not in nombres:
        raise ValueError("Verifica los nombres de los ámbitos extremos en el diccionario INEI")
    bcrp = BCRP.format("PN09822PM")
    inei = " | ".join(INEI + archivo for archivo in MODULOS)
    fuente_mixta = bcrp + " | " + inei

    def macro_pct(valor):
        return criterio(valor, "%", "0.01")

    def enaho(valor, unidad="%"):
        return criterio(f"{valor:.8f}", unidad, "0.05")

    return [
        ("Q01", "BCRP", "¿Cuál fue la inflación interanual de alimentos y bebidas de Lima Metropolitana en enero de 2020?",
         bcrp, "Selección de 2020-01 en PN09822PM.",
         {"inflacion": macro_pct(alimentos["2020-01"])}),
        ("Q02", "BCRP", "¿En qué mes se alcanzó el máximo de inflación interanual de alimentos y bebidas de Lima Metropolitana entre enero de 2020 y diciembre de 2024, y cuál fue ese valor?",
         bcrp, "Máximo de 60 observaciones mensuales inclusive.",
         {"mes": criterio(mes_pico, "AAAA-MM"), "maximo": macro_pct(pico)}),
        ("Q03", "BCRP", "¿Cuáles fueron las tasas de inflación interanual de alimentos y bebidas y del IPC general de Lima Metropolitana en diciembre de 2024, y cuál fue la diferencia alimentos menos IPC general en puntos porcentuales?",
         bcrp + " | " + BCRP.format("PN01273PM"), "Selección de 2024-12 en ambas series y resta con signo.",
         {"alimentos": macro_pct(alimentos_dic), "ipc": macro_pct(ipc_dic),
          "diferencia": criterio(alimentos_dic - ipc_dic, "pp", "0.01")}),
        ("Q04", "BCRP", "¿Cuántos meses registraron inflación interanual de alimentos y bebidas de Lima Metropolitana estrictamente superior al 8 % entre enero de 2020 y diciembre de 2024?",
         bcrp, "Conteo de meses con PN09822PM > 8, sin redondeo previo.",
         {"meses": criterio(sum(valor > 8 for valor in alimentos.values()), "meses")}),
        ("Q05", "ENAHO", "¿Cuál fue la tasa nacional de pobreza monetaria de residentes habituales en ENAHO 2024, ponderada con facpob07?",
         inei, "Suma de facpob07 de pobres dividida por suma de facpob07 de residentes.",
         {"nacional": enaho(nacional)}),
        ("Q06", "ENAHO", "¿Cuáles fueron las tasas de pobreza monetaria rural y urbana de residentes habituales en ENAHO 2024 ponderadas con facpob07, y cuál fue su diferencia absoluta en puntos porcentuales?",
         inei, "Estratos 6–8 rural y 1–5 urbano. Resta de tasas sin redondear.",
         {"rural": enaho(rural), "urbana": enaho(urbana), "brecha": enaho(abs(rural - urbana), "pp")}),
        ("Q07", "ENAHO", "¿Cuáles fueron las tasas de pobreza monetaria de residentes habituales en ENAHO 2024 por sexo, ponderadas con facpob07, y cuál fue la diferencia mujeres menos hombres en puntos porcentuales?",
         inei, "p207=2 mujeres y p207=1 hombres. Resta con signo.",
         {"mujeres": enaho(mujeres), "hombres": enaho(hombres), "brecha": enaho(mujeres - hombres, "pp")}),
        ("Q08", "ENAHO", "¿Qué ámbitos departamentales presentaron las tasas puntuales más alta y más baja de pobreza monetaria entre residentes habituales en ENAHO 2024 con facpob07? Incluye ambas tasas y su diferencia en puntos porcentuales. Considera Callao separado de Lima.",
         inei, "Primeros dos caracteres del UBIGEO. Extremos de las 25 tasas puntuales y resta.",
         {"ambito_alto": criterio(nombres[alto], "nombre"), "tasa_alta": enaho(departamento[alto]),
          "ambito_bajo": criterio(nombres[bajo], "nombre"), "tasa_baja": enaho(departamento[bajo]),
          "brecha": enaho(departamento[alto] - departamento[bajo], "pp")}),
        ("Q09", "mixta", "¿Cuál fue la inflación interanual de alimentos y bebidas de Lima Metropolitana en diciembre de 2024 y cuál fue la tasa de pobreza monetaria rural de residentes habituales de ENAHO 2024, con facpob07? Interpreta ambos indicadores considerando sus coberturas geográficas y temporales.",
         fuente_mixta, "PN09822PM en 2024-12 y estimación rural ponderada desde ENAHO.",
         {"inflacion": macro_pct(alimentos_dic), "pobreza_rural": enaho(rural),
          "fuentes": criterio("BCRP e INEI usados y trazables", "texto"),
          "coberturas": criterio("Lima Metropolitana, mes frente a mismo mes del año previo; Perú rural, encuesta anual 2024", "texto"),
          "interpretacion": criterio("Variación de precios frente a incidencia de pobreza, sin inferir causalidad", "texto")}),
        ("Q10", "mixta", "¿En qué mes y con qué valor se alcanzó el máximo de inflación interanual de alimentos y bebidas de Lima Metropolitana entre enero de 2020 y diciembre de 2024, y cuál fue la brecha rural menos urbana en pobreza monetaria de residentes habituales de ENAHO 2024 con facpob07? Identifica las coberturas geográficas y temporales y explica por qué los resultados no permiten demostrar causalidad.",
         fuente_mixta, "Máximo de PN09822PM y resta rural menos urbana con facpob07.",
         {"mes": criterio(mes_pico, "AAAA-MM"), "maximo": macro_pct(pico), "brecha": enaho(rural - urbana, "pp"),
          "fuentes": criterio("BCRP e INEI usados y trazables", "texto"),
          "coberturas": criterio("Lima Metropolitana, máximo mensual interanual 2020–2024; áreas del Perú, encuesta anual 2024", "texto"),
          "interpretacion": criterio("Ausencia de identificación causal y al menos una razón concreta", "texto")}),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bcrp", type=Path, required=True)
    parser.add_argument("--datos", type=Path, default=RAIZ / "datos")
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--descargar-bcrp", action="store_true")
    args = parser.parse_args()
    if args.descargar_bcrp:
        descargar_series(args.bcrp)
    filas = preguntas(args.bcrp, args.datos)
    with args.salida.open("x", encoding="utf-8", newline="") as salida:
        writer = csv.writer(salida, lineterminator="\n")
        writer.writerow(["id", "categoria", "pregunta", "fuentes", "procedimiento", "referencia_y_criterios"])
        for *campos, criterios in filas:
            writer.writerow([*campos, json.dumps(criterios, ensure_ascii=False)])
    for ruta in [*(args.bcrp / f"{c}.json" for c in SERIES),
                 *(args.datos / nombre for nombre in MODULOS), args.salida]:
        print(sha256(ruta.read_bytes()).hexdigest(), ruta.name)
    for codigo in SERIES:
        print(codigo, serie(args.bcrp, codigo)[1])


if __name__ == "__main__":
    main()
