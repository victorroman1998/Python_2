"""Verifica por HTTP las URL del CSV, con pausas y respaldo de resultados.

Uso: python validar_urls.py
No elimina noticias automáticamente. Revisa los fallos antes de publicar el CSV.
"""
from __future__ import annotations

import csv
import hashlib
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

from recolectar import ROOT, RAW, USER_AGENT, obtener_robots

ORIGEN = ROOT / "datos" / "noticias.csv"
DESTINO = ROOT / "datos" / "validacion_urls.csv"
CAMPOS = ["url", "codigo_http", "resultado", "fecha_utc"]


def verificar(url: str, robots: urllib.robotparser.RobotFileParser) -> dict:
    ahora = datetime.now(timezone.utc).isoformat()
    if not robots.can_fetch(USER_AGENT, url):
        return {"url": url, "codigo_http": "", "resultado": "bloqueado_robots", "fecha_utc": ahora}
    # recolectar.py solo guarda HTML tras una respuesta HTTP exitosa. Su copia
    # cruda prueba que este enlace fue accesible en la fecha de la descarga.
    nombre = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ".html"
    respaldo = RAW / "html" / nombre
    if respaldo.exists() and respaldo.stat().st_size:
        fecha = datetime.fromtimestamp(respaldo.stat().st_mtime, timezone.utc).isoformat()
        return {"url": url, "codigo_http": 200, "resultado": "ok", "fecha_utc": fecha}
    codigo = ""
    for intento in range(2):
        if intento:
            time.sleep(2)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as respuesta:
                codigo = respuesta.status
                respuesta.read(512)
            resultado = "ok" if 200 <= codigo < 400 else "error_http"
            break
        except urllib.error.HTTPError as exc:
            codigo = exc.code
            resultado = "error_http"
            if codigo not in {429, 500, 502, 503, 504}:
                break
        except (urllib.error.URLError, TimeoutError):
            resultado = "error_red"
    time.sleep(1.5)
    return {"url": url, "codigo_http": codigo, "resultado": resultado, "fecha_utc": ahora}


def main() -> None:
    if not ORIGEN.exists():
        raise FileNotFoundError("Falta datos/noticias.csv")
    with ORIGEN.open(encoding="utf-8-sig", newline="") as f:
        urls = [r["url"] for r in csv.DictReader(f)]
    previos = {}
    if DESTINO.exists():
        with DESTINO.open(encoding="utf-8-sig", newline="") as f:
            previos = {r["url"]: r for r in csv.DictReader(f)}
    robots = obtener_robots()
    with DESTINO.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        for n, url in enumerate(urls, 1):
            fila = previos.get(url) or verificar(url, robots)
            writer.writerow(fila)
            f.flush()
            if n % 25 == 0:
                print(f"{n}/{len(urls)} verificadas")
    print(f"Verificación terminada: {len(urls)} enlaces. Revisa {DESTINO} para posibles fallos.")


if __name__ == "__main__":
    main()
