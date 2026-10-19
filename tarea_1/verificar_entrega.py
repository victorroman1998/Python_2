"""Comprueba requisitos medibles sin crear datos ni métricas faltantes.

Uso: python verificar_entrega.py
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

RAIZ = Path(__file__).resolve().parent
CLASES = {"politica", "economia", "deportes", "ciencia_tecnologia"}
COLUMNAS = ["titular", "bajada", "medio", "seccion_original", "url", "fecha", "etiqueta"]


def leer_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        return list(lector.fieldnames or []), list(lector)


def notebook_ejecutado(nombre: str) -> tuple[bool, str]:
    path = RAIZ / nombre
    if not path.exists():
        return False, "falta el notebook"
    cuaderno = json.loads(path.read_text(encoding="utf-8"))
    celdas = [c for c in cuaderno.get("cells", []) if c.get("cell_type") == "code"]
    hechas = sum(c.get("execution_count") is not None for c in celdas)
    salidas = sum(bool(c.get("outputs")) for c in celdas)
    return hechas == len(celdas) and salidas > 0, f"{hechas}/{len(celdas)} celdas ejecutadas; {salidas} con salidas"


def main() -> None:
    resultados: dict[str, dict] = {}
    noticias_path = RAIZ / "datos" / "noticias.csv"
    noticias = []
    if noticias_path.exists():
        columnas, noticias = leer_csv(noticias_path)
        urls = [r["url"] for r in noticias]
        titulos = [r["titular"].casefold().strip() for r in noticias]
        dominios = all(urlsplit(u).netloc.lower() == "larepublica.pe" for u in urls)
        clases = Counter(r["etiqueta"] for r in noticias)
        bien = (columnas == COLUMNAS and len(noticias) >= 350 and
                set(clases) == CLASES and len(urls) == len(set(urls)) and
                len(titulos) == len(set(titulos)) and all(titulos) and dominios)
        resultados["noticias"] = {"ok": bien, "filas": len(noticias), "por_clase": dict(clases),
                                  "columnas": columnas}
    else:
        resultados["noticias"] = {"ok": False, "detalle": "falta datos/noticias.csv"}

    comprobacion_path = RAIZ / "datos" / "validacion_urls.csv"
    if comprobacion_path.exists() and noticias:
        _, comprobacion = leer_csv(comprobacion_path)
        comprobadas = {r["url"] for r in comprobacion
                       if r["resultado"] == "ok" and r["codigo_http"] == "200"}
        urls_finales = {r["url"] for r in noticias}
        resultados["urls_http_200"] = {
            "ok": urls_finales <= comprobadas,
            "comprobadas": len(urls_finales & comprobadas),
            "total": len(urls_finales),
        }
    else:
        resultados["urls_http_200"] = {"ok": False, "detalle": "falta comprobación HTTP"}

    etiquetas_path = RAIZ / "datos" / "etiquetas_llm.csv"
    if etiquetas_path.exists() and noticias:
        columnas, etiquetas = leer_csv(etiquetas_path)
        bien = (columnas == ["titular", "etiqueta_llm", "confianza", "modelo_llm", "fecha"] and
                len(etiquetas) == len(noticias) and
                {r["titular"] for r in etiquetas} == {r["titular"] for r in noticias} and
                all(r["etiqueta_llm"] in CLASES for r in etiquetas))
        resultados["llm"] = {"ok": bien, "filas": len(etiquetas)}
    else:
        resultados["llm"] = {"ok": False, "detalle": "faltan etiquetas LLM completas"}

    for nombre in ("01_recoleccion.ipynb", "02_clasificacion.ipynb"):
        ok, detalle = notebook_ejecutado(nombre)
        resultados[nombre] = {"ok": ok, "detalle": detalle}

    metricas = RAIZ / "modelo" / "metrics.json"
    if metricas.exists():
        m = json.loads(metricas.read_text(encoding="utf-8"))
        resultados["evaluacion"] = {
            "ok": (m.get("test", {}).get("f1_macro") is not None and
                   m.get("zero_shot_test_40", {}).get("f1_macro") is not None and
                   m.get("auditoria", {}).get("acuerdo") is not None),
            "detalle": m.get("test", {}),
        }
    else:
        resultados["evaluacion"] = {"ok": False, "detalle": "falta modelo/metrics.json"}
    resultados["modelo_local"] = {"ok": (RAIZ / "modelo" / "config.json").exists() and
                                  any((RAIZ / "modelo" / n).exists() for n in
                                      ("model.safetensors", "pytorch_model.bin"))}
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    if not all(r["ok"] for r in resultados.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
