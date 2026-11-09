"""Servidor MCP por stdio para las series oficiales de BCRPData."""

import re
import unicodedata
from datetime import date
from functools import cache, lru_cache
from io import StringIO
from math import isfinite
from pathlib import Path
from statistics import StatisticsError, correlation, mean
from tempfile import NamedTemporaryFile
from time import sleep, time

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).resolve().parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}
COLUMNAS_CATALOGO = {
    "Código de serie": "codigo",
    "Categoría de serie": "categoria",
    "Grupo de serie": "grupo",
    "Nombre de serie": "nombre",
    "Frecuencia": "frecuencia",
    "Fecha de actualización": "actualizada",
    "Fecha de inicio": "inicio",
    "Unidad de medida": "unidad",
    "Escala": "escala",
    "Fuente": "fuente_original",
}
MESES = {
    nombre: mes
    for mes, nombre in enumerate("ene feb mar abr may jun jul ago sep oct nov dic".split(), 1)
}
MESES["set"] = MESES["sep"]
FORMATOS = {
    "Diaria": (r"[0-9]{4}-[0-9]{2}-[0-9]{2}", "AAAA-MM-DD"),
    "Mensual": (r"([0-9]{4})-(0?[1-9]|1[0-2])", "AAAA-MM"),
    "Trimestral": (r"([0-9]{4})-T?([1-4])", "AAAA-T1 a AAAA-T4"),
    "Anual": (r"[0-9]{4}", "AAAA"),
}

mcp = FastMCP(
    "bcrp",
    instructions=(
        "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código "
        "con buscar_series. Usa serie para obtener datos, resumen para calcular variaciones, "
        "promedios y extremos, y comparar_series para alinear indicadores de la misma frecuencia. "
        "Cita el código, el periodo y la fuente de cada cifra."
    ),
)


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


def _descargar(url, interpretar, timeout=20):
    """Reintenta errores transitorios y cuerpos inválidos, incluidos bloqueos HTML."""
    for intento in range(3):
        try:
            respuesta = httpx.get(url, timeout=timeout, follow_redirects=True)
            respuesta.raise_for_status()
            return interpretar(respuesta)
        except httpx.HTTPStatusError as error:
            estado = error.response.status_code
            if estado not in (408, 429) and estado < 500:
                raise ToolError(f"BCRP respondió HTTP {estado} al consultar {url}.") from error
            causa = f"HTTP {estado}"
        except httpx.RequestError as error:
            causa = f"{type(error).__name__}: {error}"
        except ValueError as error:
            causa = f"respuesta inválida: {error}"
        if intento < 2:
            sleep(2 ** intento)
    raise ToolError(f"No se pudo consultar {url} después de tres intentos ({causa}).")


def _leer_catalogo(texto):
    df = pd.read_csv(StringIO(texto), sep=";", dtype=str).fillna("")
    if df.empty or not COLUMNAS_CATALOGO.keys() <= set(df.columns):
        raise ValueError("el CSV no contiene las columnas y filas esperadas del catálogo")
    df = df.rename(columns=COLUMNAS_CATALOGO)
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


@cache
def catalogo():
    """Carga el catálogo oficial, con caché en memoria y CSV local en UTF-8."""
    try:
        if time() - CATALOGO.stat().st_mtime < 86400:
            return _leer_catalogo(CATALOGO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    def interpretar(respuesta):
        # El catálogo del BCRP se entrega en Latin-1 aunque declare UTF-8.
        texto = respuesta.content.decode("latin-1")
        return texto, _leer_catalogo(texto)

    texto, df = _descargar(URL_CATALOGO, interpretar, timeout=120)
    try:
        CATALOGO.parent.mkdir(parents=True, exist_ok=True)
        archivo = NamedTemporaryFile(dir=CATALOGO.parent, encoding="utf-8", mode="w", delete=False)
        temporal = Path(archivo.name)
        try:
            with archivo:
                archivo.write(texto)
            temporal.replace(CATALOGO)
        finally:
            temporal.unlink(missing_ok=True)
    except OSError:
        # La consulta sigue siendo utilizable desde un checkout de solo lectura.
        pass
    return df


def _metadatos(fila):
    return {
        "codigo": fila.codigo,
        "nombre": f"{fila.grupo} - {fila.nombre}",
        "categoria": fila.categoria,
        "frecuencia": fila.frecuencia,
        "inicio": fila.inicio,
        "actualizada": fila.actualizada,
        "unidad": fila.unidad,
        "escala": fila.escala,
        "fuente_original": fila.fuente_original,
    }


def _ficha(codigo):
    codigo = codigo.strip().upper()
    if re.fullmatch(r"[A-Z]{2}[0-9]{5}[A-Z]{2}", codigo):
        df = catalogo()
        filas = df.loc[df.codigo == codigo]
        if not filas.empty:
            return _metadatos(filas.iloc[0])
    raise ToolError(f"No existe el código de serie {codigo!r}. Búsquelo con buscar_series.")


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca todas las palabras en la categoría, el grupo o el nombre de series del BCRP.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "tasa de referencia".
    Frecuencias: Diaria, Mensual, Trimestral o Anual. Devuelve códigos y fichas del catálogo.
    """
    palabras = _sin_tildes(texto).split()
    if not palabras or limite < 1:
        raise ToolError("Indique palabras clave y un límite de al menos 1.")
    df = catalogo()
    mascara = pd.Series(True, index=df.index)
    for palabra in palabras:
        mascara &= df.texto.str.contains(palabra, regex=False)
    if frecuencia:
        mascara &= df.frecuencia.str.lower() == frecuencia.strip().lower()
    # Se conserva la prioridad del ejemplo de la sesión 04.
    seleccion = df.loc[mascara]
    orden = seleccion.assign(
        vieja=seleccion.actualizada < "2025", largo=(seleccion.grupo + seleccion.nombre).str.len()
    )
    filas = orden.sort_values(["vieja", "largo", "codigo"]).head(limite)
    return [_metadatos(fila) for fila in filas.itertuples(index=False)]


def _normalizar_limite(periodo, frecuencia):
    patron, formato = FORMATOS[frecuencia]
    periodo = periodo.strip().upper()
    coincidencia = re.fullmatch(patron, periodo)
    if coincidencia and int(periodo[:4]) > 0:
        if frecuencia == "Mensual":
            anio, mes = coincidencia.groups()
            return f"{anio}-{int(mes):02d}"
        if frecuencia == "Trimestral":
            anio, trimestre = coincidencia.groups()
            return f"{anio}-T{trimestre}"
        if frecuencia == "Anual":
            return periodo
        try:
            return date.fromisoformat(periodo).isoformat()
        except ValueError:
            pass
    raise ToolError(f"Periodo {periodo!r} inválido para frecuencia {frecuencia}. Use {formato}.")


def _formato_api(periodo, frecuencia):
    if frecuencia == "Mensual":
        return f"{periodo[:4]}-{int(periodo[5:])}"
    return periodo.replace("-T", "-")


def _anio_completo(anio, desde, hasta):
    if len(anio) == 4:
        return int(anio)
    inicio, fin = int(desde[:4]), int(hasta[:4])
    candidato = inicio + (int(anio) - inicio) % 100
    if not candidato <= fin < candidato + 100:
        raise ValueError(f"año de dos dígitos ambiguo o fuera del intervalo: {anio}")
    return candidato


def _normalizar_periodo(nombre, frecuencia, desde, hasta):
    partes = _sin_tildes(nombre).strip().split(".")
    if frecuencia == "Anual":
        return _normalizar_limite(nombre, frecuencia)
    if frecuencia == "Mensual":
        mes, anio = partes
        return f"{int(anio):04d}-{MESES[mes]:02d}"
    if frecuencia == "Trimestral":
        trimestre, anio = partes
        return _normalizar_limite(f"{_anio_completo(anio, desde, hasta):04d}-{trimestre}", frecuencia)
    dia, mes, anio = partes
    return date(_anio_completo(anio, desde, hasta), MESES[mes], int(dia)).isoformat()


@lru_cache(maxsize=128)
def _periodos(url, bloque):
    """Comparte las consultas en memoria dentro de bloques de 15 minutos."""
    def interpretar(respuesta):
        cuerpo = respuesta.json()
        filas = cuerpo.get("periods") if isinstance(cuerpo, dict) else None
        if not isinstance(filas, list):
            raise ValueError("falta la lista 'periods' en el JSON")
        for fila in filas:
            if (
                not isinstance(fila, dict)
                or not isinstance(fila.get("name"), str)
                or not isinstance(fila.get("values"), list)
                or len(fila["values"]) != 1
            ):
                raise ValueError("se esperaba un nombre y un valor por periodo")
        return filas

    return _descargar(url, interpretar)


def _consultar(ficha, desde, hasta):
    frecuencia = ficha["frecuencia"]
    desde = _normalizar_limite(desde, frecuencia)
    hasta = _normalizar_limite(hasta, frecuencia)
    if desde > hasta:
        raise ToolError("'desde' debe ser anterior o igual a 'hasta'.")
    url = f"{API}/{ficha['codigo']}/json/{_formato_api(desde, frecuencia)}/{_formato_api(hasta, frecuencia)}"

    observaciones = {}
    for fila in _periodos(url, int(time() // 900)):
        try:
            periodo = _normalizar_periodo(fila["name"], frecuencia, desde, hasta)
            bruto = fila["values"][0]
            valor = None if bruto is None or str(bruto).strip().lower() in ("", "n.d.") else float(bruto)
            if valor is not None and not isfinite(valor):
                valor = None
        except (KeyError, ValueError, TypeError, ToolError) as error:
            raise ToolError(f"BCRP devolvió una observación inválida en {url}: {fila!r}.") from error
        if desde <= periodo <= hasta:
            observaciones[periodo] = valor
    return url, desde, hasta, dict(sorted(observaciones.items()))


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Obtiene datos oficiales con fechas inclusivas y metadatos del BCRP.

    Use AAAA-MM-DD (diaria), AAAA-MM (mensual), AAAA-T1 a AAAA-T4 (trimestral)
    o AAAA (anual). Los periodos publicados sin valor se reportan aparte.
    """
    ficha = _ficha(codigo)
    url, desde, hasta, observaciones = _consultar(ficha, desde, hasta)
    return {
        **ficha,
        "desde": desde,
        "hasta": hasta,
        "datos": [
            {"periodo": periodo, "valor": valor}
            for periodo, valor in observaciones.items()
            if valor is not None
        ],
        "periodos_sin_dato": [periodo for periodo, valor in observaciones.items() if valor is None],
        "fuente": url,
    }


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Calcula extremos, media aritmética, cambio y variación relativa sobre valores observados.

    La variación relativa es 100 × (último − primero) / primero y se devuelve nula si el primero es cero.
    """
    resultado = serie(codigo, desde, hasta)
    datos = resultado.pop("datos")
    if not datos:
        raise ToolError(f"No hay observaciones con valor para {resultado['codigo']} en ese intervalo.")
    primero, ultimo = datos[0], datos[-1]
    cambio = ultimo["valor"] - primero["valor"]
    return {
        **resultado,
        "n_observaciones": len(datos),
        "primero": primero,
        "ultimo": ultimo,
        "cambio": cambio,
        "variacion_pct": 100 * cambio / primero["valor"] if primero["valor"] else None,
        "promedio": mean(dato["valor"] for dato in datos),
        "maximo": max(datos, key=lambda dato: dato["valor"]),
        "minimo": min(datos, key=lambda dato: dato["valor"]),
    }


@mcp.tool(annotations=SOLO_LECTURA)
def comparar_series(codigo_a: str, codigo_b: str, desde: str, hasta: str) -> dict:
    """Alinea dos indicadores de la misma frecuencia por periodo y calcula su correlación de Pearson.

    Usa solo pares con dos valores. Informa los faltantes por serie sobre la unión de periodos
    publicados, sin imputar. Conserva las unidades de origen. Pearson es nula cuando hay menos
    de dos pares o una serie es constante.
    """
    ficha_a, ficha_b = _ficha(codigo_a), _ficha(codigo_b)
    if ficha_a["frecuencia"] != ficha_b["frecuencia"]:
        raise ToolError(
            f"Frecuencias incompatibles: {ficha_a['codigo']} es {ficha_a['frecuencia']} "
            f"y {ficha_b['codigo']} es {ficha_b['frecuencia']}."
        )
    codigo_a, codigo_b = ficha_a["codigo"], ficha_b["codigo"]
    if codigo_a == codigo_b:
        raise ToolError("Indique dos códigos de serie distintos.")
    fuente_a, desde, hasta, datos_a = _consultar(ficha_a, desde, hasta)
    fuente_b, _, _, datos_b = _consultar(ficha_b, desde, hasta)
    pares = []
    faltantes = {codigo_a: [], codigo_b: []}
    for periodo in sorted(datos_a.keys() | datos_b.keys()):
        valor_a, valor_b = datos_a.get(periodo), datos_b.get(periodo)
        if valor_a is None:
            faltantes[codigo_a].append(periodo)
        if valor_b is None:
            faltantes[codigo_b].append(periodo)
        if valor_a is not None and valor_b is not None:
            pares.append({"periodo": periodo, "valor_a": valor_a, "valor_b": valor_b})
    try:
        pearson = correlation([p["valor_a"] for p in pares], [p["valor_b"] for p in pares])
    except StatisticsError:
        pearson = None
    return {
        "serie_a": {**ficha_a, "fuente": fuente_a},
        "serie_b": {**ficha_b, "fuente": fuente_b},
        "frecuencia": ficha_a["frecuencia"],
        "desde": desde,
        "hasta": hasta,
        "n_pares": len(pares),
        "datos": pares,
        "faltantes": faltantes,
        "correlacion_pearson": pearson,
    }


@mcp.resource("bcrp://catalogo", mime_type="text/plain")
def guia_catalogo() -> str:
    """Guía de consulta de series estadísticas del Banco Central de Reserva del Perú."""
    return (
        f"Catálogo oficial BCRPData: {URL_CATALOGO}\n"
        "Busque códigos con buscar_series y consulte su ficha en bcrp://serie/{codigo}.\n"
        "Use serie para observaciones y resumen para cálculos descriptivos. "
        "Use comparar_series para alinear periodos de dos indicadores de igual frecuencia."
    )


@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> dict:
    """Ficha oficial de una serie del BCRP, con frecuencia, cobertura y fuente."""
    return {**_ficha(codigo), "fuente": URL_CATALOGO}


@mcp.prompt()
def informe(tema: str) -> str:
    """Guía reutilizable para redactar un informe descriptivo con series del BCRP."""
    return (
        f"Redacta un informe descriptivo sobre {tema} con datos del BCRP. "
        "Usa buscar_series para identificar el indicador y confirmar cobertura y frecuencia. "
        "Usa serie para recuperar observaciones, resumen para cálculos y comparar_series "
        "si necesitas contrastar indicadores de la misma frecuencia. Cita el código, la unidad "
        "cuando esté disponible, el periodo y el enlace oficial de cada cifra. Explica los "
        "faltantes y limita la interpretación a lo que sustentan los datos."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
