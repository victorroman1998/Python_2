"""Descarga noticias de RSS, sitemaps e índice de URL históricas.

Uso: python recolectar.py --objetivo 400
Conserva las respuestas crudas, reporta procedencia y nunca inventa titulares.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "datos" / "raw"
RSS_ROOT = "https://larepublica.pe/rss/"
INDICE = "https://freenewsapi.ai/v1/search"
ROBOTS = "https://larepublica.pe/robots.txt"
USER_AGENT = "DiplomadoNoticiasPeru/1.0 (proyecto academico; RSS respetuoso)"
SECCIONES = {
    "politica": "politica",
    "economia": "economia",
    "deportes": "deportes",
    "ciencia": "ciencia_tecnologia",
}
COLUMNAS = ["titular", "bajada", "medio", "seccion_original", "url", "fecha", "etiqueta"]


def descargar(url: str, destino: Path, usar_cache: bool = True) -> bytes:
    """Una solicitud, a lo sumo un reintento, y caché cruda reutilizable."""
    if usar_cache and destino.exists() and destino.stat().st_size:
        return destino.read_bytes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    error = None
    for intento in range(2):
        if intento:
            time.sleep(2)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as respuesta:
                contenido = respuesta.read()
            destino.write_bytes(contenido)
            time.sleep(1.5)
            return contenido
        except (urllib.error.URLError, TimeoutError) as exc:
            error = exc
    raise RuntimeError(f"No se pudo descargar {url}: {error}")


def obtener_robots() -> urllib.robotparser.RobotFileParser:
    crudo = descargar(ROBOTS, RAW / "robots.txt", usar_cache=False)
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(crudo.decode("utf-8", errors="replace").splitlines())
    return parser


def texto(valor: str | None) -> str:
    valor = re.sub(r"<[^>]+>", " ", valor or "")
    return re.sub(r"\s+", " ", html.unescape(valor)).strip()


def fecha_iso(valor: str | None) -> str:
    if not valor:
        return ""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(valor).date().isoformat()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return ""


def etiqueta_seccion(seccion: str) -> str | None:
    normal = seccion.lower().strip().replace("-", "_")
    if normal in SECCIONES:
        return SECCIONES[normal]
    if normal in {"tecnologia", "ciencia_tecnologia"}:
        return "ciencia_tecnologia"
    return None


def entradas_rss(crudo: bytes, seccion: str) -> list[dict]:
    raiz = ET.fromstring(crudo)
    items = raiz.findall("./channel/item")
    resultados = []
    for item in items:
        resultados.append({
            "titular": texto(item.findtext("title")),
            "bajada": texto(item.findtext("description")),
            "medio": "La Republica",
            "seccion_original": seccion,
            "url": (item.findtext("link") or "").strip(),
            "fecha": fecha_iso(item.findtext("pubDate")),
            "etiqueta": etiqueta_seccion(seccion),
        })
    return resultados


class Metadatos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        d = dict(attrs)
        clave = d.get("property") or d.get("name")
        if clave in {"og:title", "og:description", "description", "article:published_time"}:
            self.meta[clave] = d.get("content", "")


def urls_sitemap(crudo: bytes) -> list[str]:
    raiz = ET.fromstring(crudo)
    return [x.text.strip() for x in raiz.iter() if x.tag.endswith("}loc") and x.text]


def entrada_html(crudo: bytes, seccion: str, url: str, ultima_modificacion: str) -> dict:
    parser = Metadatos()
    parser.feed(crudo.decode("utf-8", errors="replace"))
    m = parser.meta
    fecha = fecha_iso(m.get("article:published_time")) or fecha_iso(ultima_modificacion)
    if not fecha and ultima_modificacion:
        fecha = ultima_modificacion[:10]
    return {
        "titular": texto(m.get("og:title")),
        "bajada": texto(m.get("og:description") or m.get("description")),
        "medio": "La Republica",
        "seccion_original": seccion,
        "url": url,
        "fecha": fecha,
        "etiqueta": etiqueta_seccion(seccion),
    }


def completar_con_sitemap(registros: list[dict], objetivo_por_categoria: int, fuentes: dict,
                           robots: urllib.robotparser.RobotFileParser) -> None:
    """Solo si el RSS es corto: usa sitemaps públicos y metadatos HTML."""
    validos, _ = limpiar(registros, objetivo_por_categoria)
    categorias_actuales = Counter(r["etiqueta"] for r in validos)
    titulos_vistos = {re.sub(r"\s+", " ", r["titular"].casefold()).strip() for r in validos}
    urls_vistas = {r["url"].split("?", 1)[0].rstrip("/") for r in registros}
    for seccion, etiqueta in SECCIONES.items():
        if categorias_actuales[etiqueta] >= objetivo_por_categoria:
            continue
        sitemap = f"https://larepublica.pe/sitemap/{seccion}.xml"
        if not robots.can_fetch(USER_AGENT, sitemap):
            fuentes[seccion]["sitemap_error"] = "Bloqueado por robots.txt"
            continue
        try:
            crudo = descargar(sitemap, RAW / f"sitemap_{seccion}.xml")
            raiz = ET.fromstring(crudo)
        except (RuntimeError, ET.ParseError) as exc:
            fuentes[seccion]["sitemap_error"] = str(exc)
            continue
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        elementos = raiz.findall("s:url", ns)
        # El sitemap puede ser índice. Se procesan hasta cinco archivos hijos.
        if not elementos:
            for i, hijo in enumerate(urls_sitemap(crudo)[:5]):
                if not robots.can_fetch(USER_AGENT, hijo):
                    continue
                try:
                    sub = descargar(hijo, RAW / f"sitemap_{seccion}_{i}.xml")
                    elementos.extend(ET.fromstring(sub).findall("s:url", ns))
                except (RuntimeError, ET.ParseError):
                    continue
        añadidas = 0
        for elemento in elementos:
            if categorias_actuales[etiqueta] >= objetivo_por_categoria:
                break
            url = (elemento.findtext("s:loc", default="", namespaces=ns)).split("?", 1)[0].rstrip("/")
            if (url in urls_vistas or not url.startswith("https://larepublica.pe/")
                    or not robots.can_fetch(USER_AGENT, url)):
                continue
            ultima = elemento.findtext("s:lastmod", default="", namespaces=ns)
            nombre = f"{seccion}_{len(registros):05d}.html"
            try:
                pagina = descargar(url, RAW / nombre)
                fila = entrada_html(pagina, seccion, url, ultima)
            except RuntimeError:
                continue
            urls_vistas.add(url)
            clave_titulo = re.sub(r"\s+", " ", fila["titular"].casefold()).strip()
            if not fila["titular"] or not fila["fecha"] or clave_titulo in titulos_vistos:
                continue
            registros.append(fila)
            titulos_vistos.add(clave_titulo)
            categorias_actuales[etiqueta] += 1
            añadidas += 1
        fuentes[seccion]["sitemap_anadidas"] = añadidas


def seccion_de_url(url: str) -> str | None:
    """Usa únicamente la ruta editorial del medio, nunca la categoría del índice."""
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "https" or partes.netloc.lower() != "larepublica.pe":
        return None
    seccion = partes.path.strip("/").split("/", 1)[0].lower()
    return seccion if etiqueta_seccion(seccion) else None


def completar_con_indice(registros: list[dict], objetivo: int, fuentes: dict,
                         robots: urllib.robotparser.RobotFileParser) -> None:
    """Descubre URLs anteriores y extrae metadatos del HTML oficial cuando se puede."""
    limpios, _ = limpiar(registros, objetivo)
    faltan = objetivo - len(limpios)
    if faltan <= 0:
        return
    vistas = {r["url"].split("?", 1)[0].rstrip("/") for r in registros}
    candidatos: dict[str, list[dict]] = {s: [] for s in SECCIONES}
    estado = {"url": INDICE, "paginas": 0, "candidatos": 0,
              "html_oficial": 0, "solo_metadatos_indice": 0, "errores_html": 0,
              "descripcion": "El índice descubre URLs; la clase sale de la ruta editorial del medio."}
    descartes_indice = Counter()
    fuentes["indice_externo"] = estado
    # API pública: páginas de 100, offset 0..9900; se conserva cada JSON original.
    for pagina in range(100):
        parametros = urllib.parse.urlencode({"host": "larepublica.pe", "lang": "es",
                                              "size": 100, "offset": pagina * 100})
        url_indice = f"{INDICE}?{parametros}"
        try:
            crudo = descargar(url_indice, RAW / f"indice_{pagina:04d}.json")
            datos = json.loads(crudo)
            resultados = datos.get("results", [])
        except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
            estado["error_indice"] = str(exc)
            break
        estado["paginas"] += 1
        for item in resultados:
            url = str(item.get("url") or "").split("?", 1)[0].rstrip("/")
            seccion = seccion_de_url(url)
            if not seccion:
                descartes_indice["fuera_de_categorias"] += 1
                continue
            if url in vistas:
                descartes_indice["url_duplicada"] += 1
                continue
            if not robots.can_fetch(USER_AGENT, url):
                descartes_indice["bloqueado_robots"] += 1
                continue
            if not texto(item.get("title")) or not fecha_iso(item.get("published_at")):
                descartes_indice["titulo_o_fecha_ausente"] += 1
                continue
            vistos_candidato = item.copy()
            vistos_candidato["url"] = url
            grupo = "ciencia" if seccion == "tecnologia" else seccion
            candidatos[grupo].append(vistos_candidato)
            vistas.add(url)
        disponibles = sum(map(len, candidatos.values()))
        if pagina % 10 == 0:
            print(f"Índice: {estado['paginas']} páginas; {disponibles} candidatos de las cuatro secciones.", flush=True)
        # Un margen amplio permite rechazar duplicados o artículos inaccesibles.
        if disponibles >= faltan * 2 and min(map(len, candidatos.values())) >= 35:
            break
        if len(resultados) < 100 or (pagina + 1) * 100 >= int(datos.get("total", 0)):
            break
    estado["candidatos"] = sum(map(len, candidatos.values()))
    if not estado["candidatos"]:
        estado["descartes"] = dict(descartes_indice)
        return
    # Alternar secciones evita que la cronología sesgue el cupo de una clase.
    orden = []
    for posicion in range(max(map(len, candidatos.values()))):
        for grupo in SECCIONES:
            if posicion < len(candidatos[grupo]):
                item = candidatos[grupo][posicion]
                orden.append((seccion_de_url(item["url"]), item))
    titulos = {re.sub(r"\s+", " ", r["titular"].casefold()).strip() for r in limpios}
    usadas = Counter(r["etiqueta"] for r in limpios)
    iniciales = usadas.copy()
    errores_iniciales = 0
    html_bloqueado = False
    for seccion, item in orden:
        if len(limpios) >= objetivo:
            break
        etiqueta = SECCIONES[seccion] if seccion in SECCIONES else etiqueta_seccion(seccion)
        url = item["url"]
        fila = None
        origen_html = False
        if not html_bloqueado:
            nombre = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ".html"
            try:
                pagina_html = descargar(url, RAW / "html" / nombre)
                fila_html = entrada_html(pagina_html, seccion, url, item.get("published_at", ""))
                if fila_html["titular"]:
                    fila = fila_html
                    origen_html = True
            except RuntimeError:
                estado["errores_html"] += 1
                errores_iniciales += 1
                if errores_iniciales >= 5 and estado["html_oficial"] == 0:
                    html_bloqueado = True
                    estado["aviso_html"] = "No se pudo acceder a cinco artículos; se usaron metadatos del índice."
        if fila is None:
            fila = {"titular": texto(item.get("title")),
                    "bajada": texto(item.get("description")),
                    "medio": "La Republica", "seccion_original": seccion,
                    "url": url, "fecha": fecha_iso(item.get("published_at")),
                    "etiqueta": etiqueta}
        clave = re.sub(r"\s+", " ", fila["titular"].casefold()).strip()
        if not fila["titular"] or not fila["fecha"] or clave in titulos:
            descartes_indice["titular_o_fecha_duplicada"] += 1
            continue
        registros.append(fila)
        limpios.append(fila)
        estado["html_oficial" if origen_html else "solo_metadatos_indice"] += 1
        titulos.add(clave)
        usadas[etiqueta] += 1
        if len(limpios) % 25 == 0:
            print(f"Noticias únicas acumuladas: {len(limpios)}/{objetivo}", flush=True)
    estado["filas_anadidas"] = len(limpios) - (objetivo - faltan)
    estado["por_categoria_anadidas"] = {c: usadas[c] - iniciales[c] for c in SECCIONES.values()}
    estado["descartes"] = dict(descartes_indice)


def limpiar(registros: list[dict], tope_por_categoria: int) -> tuple[list[dict], Counter]:
    motivos = Counter()
    vistos_url: set[str] = set()
    vistos_titulos: set[str] = set()
    por_categoria = Counter()
    limpios = []
    for fila in registros:
        url = fila["url"].split("?", 1)[0].rstrip("/")
        titulo = fila["titular"]
        clave_titulo = re.sub(r"\s+", " ", titulo.casefold()).strip()
        categoria = fila["etiqueta"]
        if not titulo:
            motivos["titular_vacio"] += 1
        elif not url.startswith("https://larepublica.pe/"):
            motivos["url_invalida"] += 1
        elif not categoria:
            motivos["fuera_de_categorias"] += 1
        elif not fila["fecha"]:
            motivos["fecha_ausente"] += 1
        elif url in vistos_url:
            motivos["url_duplicada"] += 1
        elif clave_titulo in vistos_titulos:
            motivos["titular_duplicado"] += 1
        elif por_categoria[categoria] >= tope_por_categoria:
            motivos["excede_cupo_categoria"] += 1
        else:
            fila["url"] = url
            limpios.append(fila)
            vistos_url.add(url)
            vistos_titulos.add(clave_titulo)
            por_categoria[categoria] += 1
    return limpios, motivos


def recolectar(objetivo: int = 400) -> dict:
    robots = obtener_robots()
    if not all(robots.can_fetch(USER_AGENT, RSS_ROOT + x + ".xml") for x in SECCIONES):
        raise RuntimeError("robots.txt no permite uno de los RSS; se detiene la descarga.")
    registros = []
    fuentes = {}
    for seccion in SECCIONES:
        url = RSS_ROOT + seccion + ".xml"
        crudo = descargar(url, RAW / f"rss_{seccion}.xml")
        filas = entradas_rss(crudo, seccion)
        fuentes[seccion] = {"url": url, "items": len(filas)}
        registros.extend(filas)
    completar_con_sitemap(registros, (objetivo + 3) // 4, fuentes, robots)
    completar_con_indice(registros, objetivo, fuentes, robots)
    limpios, motivos = limpiar(registros, objetivo)
    motivos.update({"indice_" + k: v for k, v in fuentes.get("indice_externo", {}).get("descartes", {}).items()})
    salida = ROOT / "datos" / "noticias.csv"
    salida.parent.mkdir(exist_ok=True)
    with salida.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerows(limpios)
    reporte = {
        "descarga_utc": datetime.now(timezone.utc).isoformat(),
        "opcion": "A: La Republica",
        "fuentes": fuentes,
        "filas_crudas": len(registros),
        "filas_finales": len(limpios),
        "por_categoria": dict(Counter(x["etiqueta"] for x in limpios)),
        "descartes": dict(motivos),
        "cumple_minimo_350": len(limpios) >= 350,
        "nota": "Algunos HTML se pudieron comprobar; las demás URLs requieren validar_urls.py.",
    }
    (ROOT / "datos" / "reporte_recoleccion.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return reporte


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--objetivo", type=int, default=400)
    args = parser.parse_args()
    print(json.dumps(recolectar(args.objetivo), indent=2, ensure_ascii=False))
