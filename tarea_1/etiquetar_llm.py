"""Etiquetado débil real con Ollama local. Reanuda sin repetir respuestas guardadas.

Instalar Ollama, ejecutar `ollama pull qwen2.5:3b` y luego
`python etiquetar_llm.py --modelo qwen2.5:3b`.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ORIGEN = ROOT / "datos" / "noticias.csv"
DESTINO = ROOT / "datos" / "etiquetas_llm.csv"
CATEGORIAS = {"politica", "economia", "deportes", "ciencia_tecnologia"}
CAMPOS = ["titular", "etiqueta_llm", "confianza", "modelo_llm", "fecha"]


def normalizar_etiqueta(valor: object) -> str:
    """Acepta variantes ortográficas sin cambiar la clase propuesta por el LLM."""
    texto = str(valor).strip().lower()
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto)
                    if not unicodedata.combining(c))
    texto = "_".join(texto.replace("-", " ").split())
    equivalencias = {
        "deporte": "deportes",
        "ciencia": "ciencia_tecnologia",
        "tecnologia": "ciencia_tecnologia",
        "ciencia_y_tecnologia": "ciencia_tecnologia",
    }
    return equivalencias.get(texto, texto)


def clasificar_lote(titulares: list[str], modelo: str, servidor: str) -> list[tuple[str, float]]:
    esquema = {
        "type": "object",
        "properties": {
            "resultados": {
                "type": "array", "minItems": len(titulares), "maxItems": len(titulares),
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "etiqueta": {"type": "string", "enum": sorted(CATEGORIAS)},
                        "confianza": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["id", "etiqueta", "confianza"],
                },
            },
        },
        "required": ["resultados"],
    }
    prompt = (
        "Clasifica cada titular peruano en EXACTAMENTE una categoría: politica, economia, "
        "deportes, ciencia_tecnologia. Considera el tema principal, no palabras aisladas. "
        "Responde SOLO un objeto JSON con clave resultados, una lista con exactamente un "
        "objeto por titular en el mismo orden. Cada objeto lleva id (entero desde 0), etiqueta "
        "y confianza (número entre 0 y 1). "
        "La confianza es una autoevaluación y no una probabilidad calibrada. "
        "Datos: " + json.dumps([{"id": i, "titular": t} for i, t in enumerate(titulares)],
                               ensure_ascii=False)
    )
    cuerpo = json.dumps({
        "model": modelo,
        "stream": False,
        "format": esquema,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0},
    }).encode("utf-8")
    peticion = urllib.request.Request(
        servidor.rstrip("/") + "/api/chat", data=cuerpo,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        contenido = json.load(respuesta)
    dato = json.loads(contenido["message"]["content"])
    resultados = dato["resultados"]
    if not isinstance(resultados, list) or len(resultados) != len(titulares):
        raise ValueError(f"Número de respuestas incorrecto: {dato}")
    salidas = []
    for i, item in enumerate(resultados):
        if item.get("id") != i:
            raise ValueError(f"Orden de respuestas incorrecto: {dato}")
        etiqueta = normalizar_etiqueta(item["etiqueta"])
        confianza = float(item["confianza"])
        if etiqueta not in CATEGORIAS or not 0 <= confianza <= 1:
            raise ValueError(f"Respuesta fuera de esquema: {item}")
        salidas.append((etiqueta, confianza))
    return salidas


def main(modelo: str, servidor: str, lote: int = 10) -> None:
    if not 1 <= lote <= 20:
        raise ValueError("--lote debe estar entre 1 y 20")
    if not ORIGEN.exists():
        raise FileNotFoundError("Primero ejecuta recolectar.py para crear datos/noticias.csv")
    with ORIGEN.open(encoding="utf-8-sig", newline="") as f:
        noticias = list(csv.DictReader(f))
    if len(noticias) < 350:
        raise ValueError(f"El CSV tiene {len(noticias)} noticias; se requieren al menos 350.")
    previas = {}
    if DESTINO.exists():
        with DESTINO.open(encoding="utf-8-sig", newline="") as f:
            previas = {r["titular"]: r for r in csv.DictReader(f)}
    with DESTINO.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        for inicio in range(0, len(noticias), lote):
            grupo = noticias[inicio:inicio + lote]
            pendientes = [x["titular"] for x in grupo
                          if not (previas.get(x["titular"], {}).get("etiqueta_llm") in CATEGORIAS)]
            nuevas = {}
            if pendientes:
                error = None
                for intento in range(2):
                    if intento:
                        time.sleep(2)
                    try:
                        salidas = clasificar_lote(pendientes, modelo, servidor)
                        nuevas = dict(zip(pendientes, salidas))
                        break
                    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                        error = exc
                else:
                    raise RuntimeError(f"Lote iniciado en {inicio + 1}: falló Ollama ({error})")
            for noticia in grupo:
                titular = noticia["titular"]
                anterior = previas.get(titular)
                if anterior and anterior.get("etiqueta_llm") in CATEGORIAS:
                    fila = {c: anterior[c] for c in CAMPOS}
                else:
                    etiqueta, confianza = nuevas[titular]
                    fila = {"titular": titular, "etiqueta_llm": etiqueta,
                            "confianza": confianza, "modelo_llm": modelo,
                            "fecha": datetime.now(timezone.utc).date().isoformat()}
                writer.writerow(fila)
                f.flush()
            print(f"{min(inicio + lote, len(noticias))}/{len(noticias)} titulares etiquetados")
    print(f"Guardadas {len(noticias)} etiquetas en {DESTINO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", default="qwen2.5:3b")
    parser.add_argument("--servidor", default="http://127.0.0.1:11434")
    parser.add_argument("--lote", type=int, default=10)
    args = parser.parse_args()
    main(args.modelo, args.servidor, args.lote)
