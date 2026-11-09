"""Contrasta resultados con BCRP CSV y los dos Stata originales, y redacta los informes."""

import csv
import json
import re
from collections import defaultdict
from math import fsum, isclose
from string import Template
from time import sleep
from zipfile import ZipFile

import httpx
import pandas as pd

from enaho import FUENTES, RAIZ, exigir, huella

MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
CLAVE_HOGAR = ["conglome", "vivienda", "hogar"]
MODULOS = ("966-Modulo02.zip", "966-Modulo34.zip")


def numero(valor, decimales=2):
    return f"{valor:.{decimales}f}".replace(".", ",")


def mes(periodo):
    return f"{MESES[int(periodo[5:]) - 1]} de {periodo[:4]}"


def verificar_bcrp(bcrp, tabla):
    """Lee la variante CSV oficial sin usar el servidor ni su normalizador JSON."""
    fuentes = {}
    verificadas = {}
    meses = {nombre[:3].capitalize(): f"{n:02d}" for n, nombre in enumerate(MESES, 1)}
    meses["Set"] = "09"
    for tipo in ("alimentos", "general"):
        serie = bcrp[f"serie_{tipo}"]
        codigo = serie["codigo"]
        url = serie["fuente"].replace("/json/", "/csv/")
        for intento in range(3):
            try:
                respuesta = httpx.get(url, follow_redirects=True, timeout=30)
                respuesta.raise_for_status()
                lineas = re.split(r"<br\s*/?>|\r?\n", respuesta.text, flags=re.I)
                cabecera, *filas = csv.reader(linea for linea in lineas if linea.strip())
                exigir(cabecera[1].strip() == serie["nombre"], f"Cabecera CSV inesperada para {codigo}.")
                valores = {}
                for periodo, valor in filas:
                    nombre, anio = periodo.strip().split(".")
                    valores[f"{anio}-{meses[nombre]}"] = float(valor)
                exigir(len(filas) == len(valores) == len(tabla)
                       and valores.keys() == set(tabla.periodo),
                       f"Cobertura CSV inesperada para {codigo}.")
                break
            except (httpx.HTTPError, ValueError, KeyError, IndexError):
                if intento == 2:
                    raise
                sleep(2 ** intento)
        exigir(all(isclose(valores[periodo], valor, abs_tol=1e-10, rel_tol=0)
                   for periodo, valor in zip(tabla.periodo, tabla[codigo], strict=True)),
               f"El CSV oficial difiere de la serie MCP {codigo}.")
        fuentes[codigo] = url
        verificadas[tipo] = valores
    return verificadas, fuentes


def leer_stata(datos, archivo, nombre, columnas):
    with ZipFile(datos / archivo) as zip_modulo:
        rutas = [ruta for ruta in zip_modulo.namelist() if ruta.rsplit("/", 1)[-1] == nombre]
        exigir(len(rutas) == 1, f"No se pudo identificar {nombre} en {archivo}.")
        with zip_modulo.open(rutas[0]) as dta:
            return pd.read_stata(dta, columns=columnas, convert_categoricals=False)


def verificar_enaho(datos, indicadores):
    """Reconstruye tasas desde Stata con un índice de hogares y sumas de precisión alta."""
    sumaria = leer_stata(datos, "966-Modulo34.zip", "sumaria-2024.dta",
                         CLAVE_HOGAR + ["ubigeo", "estrato", "pobreza", "factor07", "mieperho"])
    miembros = leer_stata(datos, "966-Modulo02.zip", "enaho01-2024-200.dta",
                          CLAVE_HOGAR + ["ubigeo", "estrato", "p204", "p205", "p206", "p207", "facpob07"])
    pobreza_hogar = {}
    totales = defaultdict(list)
    pobres = defaultdict(list)

    def acumular(metodo, fila, peso, pobre, sexo=None):
        grupos = [("nacional", "PE"), ("area", "U" if fila.estrato < 6 else "R"),
                  ("departamento", str(fila.ubigeo).zfill(6)[:2])]
        if sexo is not None:
            grupos.append(("sexo", str(int(sexo))))
        for grupo, codigo in grupos:
            clave = (metodo, grupo, codigo)
            totales[clave].append(peso)
            if pobre:
                pobres[clave].append(peso)

    for hogar in sumaria.itertuples(index=False):
        pobre = hogar.pobreza in (1, 2)
        pobreza_hogar[(hogar.conglome, hogar.vivienda, hogar.hogar)] = pobre
        acumular("sumaria", hogar, float(hogar.factor07) * hogar.mieperho, pobre)
    exigir(len(pobreza_hogar) == len(sumaria), "Sumaria contiene llaves duplicadas en el contraste.")
    for persona in miembros.itertuples(index=False):
        residente = ((persona.p204, persona.p205) == (1, 2)
                     or (persona.p204, persona.p206) == (2, 1))
        if residente:
            pobre = pobreza_hogar[(persona.conglome, persona.vivienda, persona.hogar)]
            acumular("personas", persona, float(persona.facpob07), pobre, persona.p207)

    tasas = {clave: 100 * fsum(pobres[clave]) / fsum(pesos) for clave, pesos in totales.items()}
    claves = list(zip(indicadores.metodo, indicadores.grupo, indicadores.codigo, strict=True))
    exigir(len(claves) == len(tasas) and set(claves) == tasas.keys(),
           "El contraste ENAHO no reproduce los ámbitos de los indicadores.")
    for fila, clave in zip(indicadores.itertuples(), claves, strict=True):
        exigir(fila.n_observaciones == len(totales[clave])
               and isclose(fila.pobreza_pct, tasas[clave], abs_tol=1e-10, rel_tol=0),
               f"El contraste ENAHO difiere en {clave}.")
    return tasas


def verificar_y_redactar(bcrp, tabla, indicadores, datos, trabajo):
    macro, fuentes = verificar_bcrp(bcrp, tabla)
    enaho = verificar_enaho(datos, indicadores)
    resumen = bcrp["resumen_alimentos"]
    inicio, fin, pico, piso = (resumen[campo] for campo in ("primero", "ultimo", "maximo", "minimo"))
    codigo_a, codigo_b = tabla.columns[1:3]
    mayor = tabla.loc[tabla[codigo_a].ge(10), "periodo"].tolist()
    cierres = "\n".join(
        f"| {fila.periodo[:4]} | {numero(a)} | {numero(b)} | {numero(fila.brecha_pp)} |"
        for fila, a, b in zip(tabla.itertuples(), tabla[codigo_a], tabla[codigo_b], strict=True)
        if fila.periodo.endswith("-12")
    )

    def tasa(grupo, codigo, metodo="personas"):
        return indicadores.loc[indicadores.grupo.eq(grupo) & indicadores.codigo.eq(codigo)
                               & indicadores.metodo.eq(metodo), "pobreza_pct"].item()

    rural, urbana = tasa("area", "R"), tasa("area", "U")
    mujeres, hombres = tasa("sexo", "2"), tasa("sexo", "1")
    nacional, sumaria = tasa("nacional", "PE"), tasa("nacional", "PE", "sumaria")
    brecha_area = rural - urbana
    departamentos = indicadores.query("metodo == 'personas' and grupo == 'departamento'").sort_values(
        "pobreza_pct", ascending=False)
    alto, bajo = departamentos.iloc[0], departamentos.iloc[-1]
    extremos = "\n".join(
        f"| {fila.ambito} | {numero(fila.pobreza_pct)} |"
        for fila in pd.concat([departamentos.head(3), departamentos.tail(3)]).itertuples()
    )
    residentes = indicadores.query("metodo == 'personas' and grupo == 'nacional'").iloc[0].n_observaciones
    frase_pico = (f"La inflación interanual de alimentos y bebidas alcanzó su máximo de "
                  f"{numero(pico['valor'])} % en {mes(pico['periodo'])}.")
    frase_area = (f"La pobreza rural fue {numero(brecha_area)} puntos porcentuales mayor que la urbana.")
    frase_depto = f"La incidencia estimada de pobreza monetaria en {alto.ambito} fue {numero(alto.pobreza_pct)} %."

    pico_csv = max(macro["alimentos"], key=macro["alimentos"].get)
    exigir(pico_csv == pico["periodo"], "La fecha del máximo BCRP difiere en el CSV oficial.")
    controles = [
        ("BCRP", frase_pico, pico["valor"], macro["alimentos"][pico_csv], "%",
         f"Máximo de 60 valores del CSV oficial. El mes comprobado fue {pico_csv}. "
         f"[BCRPData {codigo_a}]({fuentes[codigo_a]})."),
        ("Área ENAHO", frase_area, brecha_area,
         enaho["personas", "area", "R"] - enaho["personas", "area", "U"], "pp",
         "Tasa de los residentes en estratos 6–8 menos tasa en estratos 1–5, ambas recalculadas desde los Stata."),
        ("Departamento ENAHO", frase_depto, alto.pobreza_pct,
         enaho["personas", "departamento", alto.codigo], "%",
         f"Tasa recalculada desde los Stata para residentes con prefijo UBIGEO {alto.codigo}."),
    ]
    contrastes = []
    for tema, frase, valor, independiente, unidad, procedimiento in controles:
        informado = float(f"{valor:.2f}")
        diferencia = independiente - informado
        exigir(numero(valor) == numero(independiente) and abs(independiente - valor) < 1e-10,
               f"Falló el contraste de la afirmación {tema}.")
        contrastes.append({"tema": tema, "afirmacion": frase, "valor_informado": informado,
                           "valor_sin_redondear": valor, "valor_independiente": independiente,
                           "diferencia_frente_al_informe": diferencia, "unidad": unidad,
                           "procedimiento": procedimiento, "estado": "APROBADO"})

    contexto = dict(
        codigo_a=codigo_a, codigo_b=codigo_b, cierres=cierres, extremos=extremos,
        frase_pico=frase_pico, frase_area=frase_area, frase_depto=frase_depto,
        inicial=numero(inicio["valor"]), final=numero(fin["valor"]), minimo=numero(piso["valor"]),
        mes_minimo=mes(piso["periodo"]), n_mayor=len(mayor), desde_mayor=mes(mayor[0]),
        hasta_mayor=mes(mayor[-1]), final_general=numero(tabla[codigo_b].iloc[-1]),
        brecha_final=numero(tabla.brecha_pp.iloc[-1]), media_a=numero(resumen["promedio"]),
        media_b=numero(bcrp["resumen_general"]["promedio"]),
        nacional=numero(nacional), sumaria=numero(sumaria), delta_estimadores=numero(sumaria - nacional, 6),
        residentes=f"{residentes:,}".replace(",", " "), rural=numero(rural), urbana=numero(urbana),
        mujeres=numero(mujeres), hombres=numero(hombres), brecha_sexo=numero(mujeres - hombres),
        ambitos=len(departamentos), bajo=bajo.ambito, tasa_baja=numero(bajo.pobreza_pct),
        rango=numero(alto.pobreza_pct - bajo.pobreza_pct),
        sumaria_u=numero(tasa("area", "U", "sumaria"), 6),
        sumaria_r=numero(tasa("area", "R", "sumaria"), 6),
    )
    plantilla = Template((RAIZ / "scripts/informe_base.md").read_text(encoding="utf-8"))
    (trabajo / "informe_final.md").write_text(plantilla.substitute(contexto), encoding="utf-8")
    evidencia = {
        "series_csv": fuentes, "valores_bcrp_contrastados": 2 * len(tabla),
        "entradas_enaho": {archivo: {"url": FUENTES[archivo], "sha256": huella(datos / archivo)}
                           for archivo in MODULOS},
        "tasas_enaho_recalculadas": len(enaho), "controles": contrastes,
    }
    (trabajo / "contrastes_fase3.json").write_text(
        json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tabla_verificacion = "\n".join(
        f"| {c['afirmacion']} | {numero(c['valor_informado'])} {c['unidad']} | "
        f"{numero(c['valor_independiente'], 9)} {c['unidad']} | "
        f"{numero(c['diferencia_frente_al_informe'], 9)} {c['unidad']} | {c['estado']} |"
        for c in contrastes
    )
    procedimientos = "\n".join(f"- **{tema}.** {procedimiento}" for tema, _, _, _, _, procedimiento in controles)
    (trabajo / "verificacion_cifras.md").write_text(
        f"""# Verificación de cifras

Se cotejaron tres frases del [informe](informe_final.md) con cálculos independientes. La diferencia es el valor independiente menos el publicado a dos decimales. El control exige que ambos cálculos sin redondear coincidan con tolerancia absoluta de 0,0000000001 y produzcan el mismo valor publicado.

| Frase exacta | Valor informado | Valor independiente | Diferencia | Resultado |
| --- | ---: | ---: | ---: | --- |
{tabla_verificacion}

{procedimientos}

El contraste macroeconómico lee el CSV oficial de BCRPData mediante HTTP y compara cada mes con el JSON obtenido por MCP. En ENAHO el verificador vuelve a leer los dos ZIP oficiales, asigna pobreza mediante una tabla de búsqueda de hogares y suma los pesos con `math.fsum`. El cálculo es independiente del Parquet, de la función de estimación de las Skills y del CSV de referencia departamental. El contraste usa los mismos criterios de población y pesos para estimar el mismo indicador. [Módulo 02]({FUENTES["966-Modulo02.zip"]}) · [Módulo 34]({FUENTES["966-Modulo34.zip"]}).

Los {2 * len(tabla)} valores mensuales y las {len(enaho)} tasas de ENAHO coincidieron antes de redondear. El JSON de contraste conserva los valores, las fuentes y las huellas de los insumos. El script de verificación se ejecuta como parte de `uv run --locked python scripts/investigar.py`. [JSON de contraste](../salidas/contrastes_fase3.json) · [Script de verificación](../scripts/verificar_cifras.py).
""", encoding="utf-8")
    return evidencia
