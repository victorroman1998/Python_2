"""Procesamiento, estimación y contrato de salidas de ENAHO 2024."""

from hashlib import file_digest, sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory
import unicodedata
from zipfile import BadZipFile, ZipFile, is_zipfile

import httpx
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
INEI = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/"
CURSO = "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
REFERENCIA = "pobreza_departamento_2024.csv"
GEOJSON = "peru_departamental_simple.geojson"
FUENTES = {
    "966-Modulo34.zip": INEI + "966-Modulo34.zip",
    "966-Modulo02.zip": INEI + "966-Modulo02.zip",
    REFERENCIA: CURSO + "sessions/16-skills-enaho/referencias/" + REFERENCIA,
    GEOJSON: CURSO + "sessions/06-geoespacial/lab/Data/" + GEOJSON,
}
PARQUET = "personas_2024.parquet"
INDICADORES = "indicadores.csv"
VALIDACION = "validacion.txt"
APROBADO = "Estado: APROBADO"
COMANDO_LIMPIAR = "uv run --locked python .claude/skills/limpiando-enaho/scripts/limpiar.py"

LLAVE_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVE_PERSONA = LLAVE_HOGAR + ["codperso"]
ANCHOS = dict(conglome=6, vivienda=3, hogar=2, codperso=2, ubigeo=6)
GEOGRAFIA = ["ano", "ubigeo", "estrato", "dominio"]
COLUMNAS_HOGARES = LLAVE_HOGAR + GEOGRAFIA + ["pobreza", "factor07", "mieperho"]
COLUMNAS_MIEMBROS = LLAVE_PERSONA + GEOGRAFIA + ["p204", "p205", "p206", "p207", "facpob07"]
NOMBRES = dict(enumerate(
    (
        "Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca", "Callao",
        "Cusco", "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad", "Lambayeque",
        "Lima", "Loreto", "Madre de Dios", "Moquegua", "Pasco", "Piura", "Puno",
        "San Martín", "Tacna", "Tumbes", "Ucayali",
    ), start=1,
))
DEPARTAMENTOS = {f"{codigo:02d}": nombre for codigo, nombre in NOMBRES.items()}
AMBITOS = {
    "nacional": {"PE": "Perú"},
    "area": {"U": "Urbana", "R": "Rural"},
    "sexo": {"1": "Hombres", "2": "Mujeres"},
    "departamento": DEPARTAMENTOS,
}
# Sumaria reproduce el redondeo a una décima del curso. Las estimaciones
# directas usan otro marco poblacional y se contrastan por separado.
TOLERANCIAS = {
    "personas": {"nacional": 0.10, "area": 0.20, "departamento": 0.60},
    "sumaria": {"nacional": 0.05, "area": 0.05, "departamento": 0.05},
}


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def huella(ruta):
    with ruta.open("rb") as archivo:
        return file_digest(archivo, "sha256").hexdigest()


def preparar_archivo(datos, nombre, descargar):
    ruta = datos / nombre
    if ruta.is_file():
        return ruta
    url = FUENTES[nombre]
    instruccion = f"Guarda el archivo oficial en {ruta} desde {url}."
    if not descargar:
        raise FileNotFoundError(instruccion)
    datos.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(dir=datos) as temporal:
            parcial = Path(temporal) / nombre
            with httpx.stream("GET", url, follow_redirects=True, timeout=60) as respuesta:
                respuesta.raise_for_status()
                with parcial.open("wb") as archivo:
                    for bloque in respuesta.iter_bytes():
                        archivo.write(bloque)
            if ruta.suffix == ".zip":
                exigir(is_zipfile(parcial), f"{nombre}: la descarga no es un ZIP válido. {instruccion}")
            parcial.replace(ruta)
    except httpx.HTTPError as error:
        raise OSError(f"Falló la descarga de {nombre} ({error}). {instruccion}") from error
    return ruta


def normalizar_nombre(nombre):
    texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def normalizar_codigo(serie, ancho, nombre):
    texto = serie.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
    invalidos = ~texto.str.fullmatch(rf"[0-9]{{1,{ancho}}}", na=False)
    exigir(not invalidos.any(), f"{nombre}: {invalidos.sum()} códigos faltantes o inválidos.")
    return texto.str.zfill(ancho)


def leer_modulo(ruta, dta, columnas, registro):
    with ZipFile(ruta) as zip_modulo:
        archivos = [nombre for nombre in zip_modulo.namelist()
                    if PurePosixPath(nombre).name.lower() == dta]
        exigir(len(archivos) == 1, f"{ruta.name} debe contener un solo {dta}.")
        # Extrae únicamente el DTA requerido, sin desplegar rutas del ZIP en disco.
        contenido = BytesIO(zip_modulo.read(archivos[0]))
    with pd.read_stata(contenido, convert_categoricals=False, iterator=True) as lector:
        originales = list(lector.variable_labels())
        normalizados = [normalizar_nombre(c) for c in originales]
        exigir(len(set(normalizados)) == len(originales),
               f"{dta}: nombres de columnas duplicados tras normalizar.")
        nombres = dict(zip(normalizados, originales))
        faltantes = set(columnas) - nombres.keys()
        exigir(not faltantes, f"{dta}: faltan columnas {sorted(faltantes)}.")
        base = lector.read(columns=[nombres[c] for c in columnas])
        etiquetas = lector.value_labels()
    base = base.rename(columns=dict(zip(originales, normalizados)))
    registro.append(f"APROBADO {dta}: {len(base)} filas leídas de {len(originales)} columnas.")
    registro.append("  Tipos Stata leídos: " + ", ".join(f"{c}={base.dtypes[c]}" for c in columnas))
    for variable in ("p204", "p205", "p206", "p207", "pobreza", "estrato"):
        if variable in base:
            etiquetas_variable = etiquetas.get(nombres[variable], {})
            categorias = ", ".join(f"{clave}={valor.strip()}"
                                   for clave, valor in sorted(etiquetas_variable.items()))
            registro.append(f"  {variable}: {categorias}; nulos={base[variable].isna().sum()}")
    return base


def validar_llave(base, columnas, nombre):
    exigir(not base[columnas].isna().any().any(), f"{nombre}: llave con valores faltantes.")
    repetidas = base.duplicated(columnas, keep=False).sum()
    exigir(repetidas == 0, f"{nombre}: {repetidas} filas con llave duplicada ({', '.join(columnas)}).")


def residentes(miembros):
    for variable, condicion in (
        ("p204", miembros.p204.notna()),
        ("p205", miembros.p204.eq(1)),
        ("p206", miembros.p204.eq(2)),
    ):
        exigir(miembros.loc[condicion, variable].isin([1, 2]).all(),
               f"{variable}: código inválido o respuesta faltante cuando aplica.")
    return miembros.loc[
        ((miembros.p204 == 1) & (miembros.p205 == 2))
        | ((miembros.p204 == 2) & (miembros.p206 == 1))
    ].copy()


def unir_residentes(personas, hogares):
    validar_llave(hogares, LLAVE_HOGAR, "Sumaria")
    validar_llave(personas, LLAVE_PERSONA, "Personas")
    unidos = personas.merge(
        hogares, on=LLAVE_HOGAR, how="left", validate="m:1",
        indicator=True, suffixes=("", "_sumaria"),
    )
    exigir(len(unidos) == len(personas), "La unión m:1 alteró la cantidad de personas.")
    sin_hogar = unidos["_merge"].ne("both").sum()
    exigir(sin_hogar == 0, f"La unión m:1 encontró {sin_hogar} residentes sin hogar en Sumaria.")
    for campo in GEOGRAFIA:
        iguales = unidos[campo].eq(unidos[f"{campo}_sumaria"]).fillna(False)
        exigir(iguales.all(), f"La unión m:1 encontró {int((~iguales).sum())} discrepancias en {campo}.")
    return unidos.drop(columns=["_merge"] + [f"{c}_sumaria" for c in GEOGRAFIA])


def pesos_positivos(serie, nombre):
    pesos = pd.to_numeric(serie, errors="raise").astype("float64")
    exigir((np.isfinite(pesos) & pesos.gt(0)).all(), f"{nombre}: pesos faltantes, no finitos o no positivos.")
    return pesos


def preparar_bases(miembros, hogares, registro):
    for base, llave, nombre in (
        (miembros, LLAVE_PERSONA, "Módulo 02"), (hogares, LLAVE_HOGAR, "Módulo 34"),
    ):
        for columna in llave + ["ubigeo"]:
            base[columna] = normalizar_codigo(base[columna], ANCHOS[columna], columna)
        validar_llave(base, llave, nombre)
        exigir(base.ano.astype("string").eq("2024").fillna(False).all(), f"{nombre}: año distinto de 2024 o faltante.")
        exigir(base.estrato.isin(range(1, 9)).all(), f"{nombre}: estrato inválido.")
        exigir(base.dominio.isin(range(1, 9)).all(), f"{nombre}: dominio inválido.")
        registro.append(f"APROBADO {nombre}: llaves únicas y completas, año 2024, estrato y dominio válidos.")
    personas = residentes(miembros)
    registro.append(f"Filtro de residencia: {len(miembros)} filas iniciales, {len(personas)} residentes, "
                    f"{len(miembros) - len(personas)} excluidas.")
    personas = unir_residentes(personas, hogares)
    registro.append(f"APROBADO unión m:1: {len(personas)} filas antes y después, 0 sin hogar, "
                    "0 multiplicaciones, año y geografía concordantes.")

    exigir(personas.p207.isin([1, 2]).all(), "p207: sexo inválido o faltante en residentes.")
    personas["sexo"] = personas.p207.astype("int8").astype("string")
    personas["facpob07"] = pesos_positivos(personas.facpob07, "facpob07")
    hogares["factor07"] = pesos_positivos(hogares.factor07, "factor07")
    miembros_hogar = pesos_positivos(hogares.mieperho, "mieperho")
    exigir(miembros_hogar.mod(1).eq(0).all(), "mieperho: número de miembros no entero.")

    for base, metodo in ((personas, "personas"), (hogares, "sumaria")):
        exigir(base.pobreza.isin([1, 2, 3]).all(), f"{metodo}: código de pobreza inválido o faltante.")
        base["pobre"] = base.pobreza.le(2)
        base["area"] = np.where(base.estrato.le(5), "U", "R")
        base["departamento"] = base.ubigeo.str[:2]
        observados = set(base.departamento)
        exigir(observados == DEPARTAMENTOS.keys(),
               f"{metodo}: se esperaban 25 departamentos; faltan {sorted(DEPARTAMENTOS.keys() - observados)}, "
               f"sobran {sorted(observados - DEPARTAMENTOS.keys())}.")
        registro.append(f"APROBADO {metodo}: 25 ámbitos, Callao (07) y Lima (15) separados; códigos de pobreza válidos.")
    registro.append("APROBADO ponderación: facpob07 en residentes, factor07 × mieperho en Sumaria; pesos finitos y positivos.")
    registro.append("APROBADO sexo en residentes: p207=1 hombre, p207=2 mujer.")
    return personas, hogares


def estimar(base, pesos, metodo):
    exigir(base.index.equals(pesos.index), "Los pesos deben corresponder a las filas de la base.")
    datos = base.assign(_peso=pesos_positivos(pesos, metodo), nacional="PE")
    exigir(datos.pobre.isin([0, 1]).all(), "El indicador de pobreza debe ser binario y completo.")
    datos["_peso_pobre"] = datos._peso * datos.pobre
    filas = []
    for grupo, etiquetas in AMBITOS.items():
        if grupo == "sexo" and metodo == "sumaria":
            continue
        for codigo, ambito in datos.groupby(grupo, sort=True, dropna=False):
            exigir(codigo in etiquetas, f"{grupo}: código inválido o faltante.")
            poblacion = ambito._peso.sum()
            poblacion_pobre = ambito._peso_pobre.sum()
            filas.append({
                "metodo": metodo, "grupo": grupo, "codigo": codigo, "ambito": etiquetas[codigo],
                "n_observaciones": len(ambito), "poblacion_expandida": poblacion,
                "poblacion_pobre_expandida": poblacion_pobre,
                "pobreza_pct": 100 * poblacion_pobre / poblacion,
            })
    return pd.DataFrame(filas)


def leer_referencia(ruta):
    referencia = pd.read_csv(ruta, dtype={"ccdd": "string"})
    exigir({"ccdd", "pobreza_pct"} <= set(referencia), "La referencia debe contener ccdd y pobreza_pct.")
    codigos = normalizar_codigo(referencia.ccdd, 2, "ccdd de referencia")
    exigir(codigos.is_unique and set(codigos) == DEPARTAMENTOS.keys(),
           "La referencia debe contener 25 códigos distintos, del 01 al 25.")
    tasas = pd.to_numeric(referencia.pobreza_pct, errors="raise")
    exigir(tasas.between(0, 100).all(), "La referencia contiene tasas inválidas o faltantes.")
    return dict(zip(codigos, tasas))


def contrastar(indicadores, referencia, grupos):
    objetivos = {"nacional": {"PE": 27.6}, "area": {"U": 24.8, "R": 39.3},
                 "departamento": referencia}
    resultados = []
    for metodo, tolerancias in TOLERANCIAS.items():
        for grupo in grupos:
            tasas = indicadores.loc[indicadores.metodo.eq(metodo) & indicadores.grupo.eq(grupo)]
            exigir(tasas.codigo.is_unique and set(tasas.codigo) == objetivos[grupo].keys(),
                   f"{metodo}/{grupo}: faltan estimaciones o hay códigos inesperados o duplicados.")
            tolerancia = tolerancias[grupo]
            for fila in tasas.itertuples(index=False):
                meta = objetivos[grupo][fila.codigo]
                diferencia = abs(fila.pobreza_pct - meta)
                pasa = diferencia <= tolerancia + 1e-12
                resultados.append((pasa, f"{metodo}/{grupo}/{fila.codigo} {fila.ambito}: "
                                   f"{fila.pobreza_pct:.6f} % vs {meta:.1f} %, "
                                   f"Δ {diferencia:.6f} pp, tolerancia {tolerancia:.2f} pp"))
    return resultados


def escribir_validacion(ruta, estado, registro):
    with TemporaryDirectory(dir=ruta.parent) as temporal:
        informe = Path(temporal) / ruta.name
        informe.write_text(f"ENAHO 2024 | Validación\nEstado: {estado}\n\n"
                           + "\n".join(registro) + "\n", encoding="utf-8")
        informe.replace(ruta)


def limpiar(datos, salidas, descargar):
    salidas.mkdir(parents=True, exist_ok=True)
    informe = salidas / VALIDACION
    registro = [
        "Personas: denominador = suma de facpob07 de residentes habituales del ámbito.",
        "Sumaria: denominador = suma de factor07 × mieperho de hogares del ámbito (personas representadas).",
        "Numerador: suma del mismo peso en hogares de pobreza monetaria 1 o 2.",
        "Referencias de validación: Issue #201 y CSV departamental de la Sesión 16.",
    ]
    escribir_validacion(informe, "EN PROCESO", registro)
    try:
        fuentes = {}
        for nombre in ("966-Modulo34.zip", "966-Modulo02.zip", REFERENCIA):
            ruta = preparar_archivo(datos, nombre, descargar)
            fuentes[nombre] = ruta
            registro.append(f"Entrada {nombre} SHA-256 {huella(ruta)}")
        hogares = leer_modulo(fuentes["966-Modulo34.zip"], "sumaria-2024.dta", COLUMNAS_HOGARES, registro)
        miembros = leer_modulo(fuentes["966-Modulo02.zip"], "enaho01-2024-200.dta", COLUMNAS_MIEMBROS, registro)
        personas, hogares = preparar_bases(miembros, hogares, registro)
        indicadores = pd.concat([
            estimar(personas, personas.facpob07, "personas"),
            estimar(hogares, hogares.factor07 * hogares.mieperho, "sumaria"),
        ], ignore_index=True)
        referencia = leer_referencia(fuentes[REFERENCIA])
        resultados = [
            (len(hogares) == 33691, f"hogares de Sumaria: {len(hogares)} (esperados: 33691)"),
            (len(miembros) == 117721, f"filas de miembros: {len(miembros)} (esperadas: 117721)"),
            (len(personas) == 108664, f"residentes habituales: {len(personas)} (esperados: 108664)"),
            *contrastar(indicadores, referencia, ("nacional", "area", "departamento")),
        ]
        for aprobado, mensaje in resultados:
            registro.append(f"{'APROBADO' if aprobado else 'FALLÓ'} {mensaje}")
        exigir(all(pasa for pasa, _ in resultados), "Falló al menos una comprobación estadística.")
        with TemporaryDirectory(dir=salidas) as temporal:
            lote = Path(temporal)
            personas.to_parquet(lote / PARQUET, engine="pyarrow", index=False)
            indicadores.to_csv(lote / INDICADORES, index=False)
            for nombre in (PARQUET, INDICADORES):
                registro.append(f"SHA-256 {huella(lote / nombre)} {nombre}")
                (lote / nombre).replace(salidas / nombre)
            escribir_validacion(informe, "APROBADO", registro)
    except (OSError, ValueError, BadZipFile) as error:
        registro.append(f"FALLÓ {error}")
        escribir_validacion(informe, "RECHAZADO", registro)
        raise
    return indicadores


def cargar_indicadores_validados(salidas):
    """Usa el agregado del mismo lote aprobado que el Parquet local."""
    try:
        informe = (salidas / VALIDACION).read_text(encoding="utf-8").splitlines()
        exigir(APROBADO in informe and not any(linea.startswith("FALLÓ") for linea in informe),
               "La validación de ENAHO no está aprobada.")
        csv = (salidas / INDICADORES).read_bytes()
        for nombre, digest in ((PARQUET, huella(salidas / PARQUET)), (INDICADORES, sha256(csv).hexdigest())):
            exigir(f"SHA-256 {digest} {nombre}" in informe,
                   f"{nombre} no corresponde al lote aprobado.")
        return pd.read_csv(BytesIO(csv), dtype={"codigo": "string"})
    except (OSError, ValueError) as error:
        raise ValueError(f"{error} Ejecuta primero limpiando-enaho con {COMANDO_LIMPIAR}.") from error
