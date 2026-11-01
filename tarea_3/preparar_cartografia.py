"""Preparación opcional de cartografía; nunca se ejecuta desde el dashboard.

python tarea_3/preparar_cartografia.py --source departamentos_original.geojson
Sin --source, descarga la capa pública de INGEMMET. No procesa datos ENDES.
"""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import shapely
from shapely.geometry import mapping, shape

SOURCE = ("https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/"
          "SERV_CARTOGRAFIA_DEMARCACION_WGS84/MapServer/0")
QUERY = SOURCE + "/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=geojson"


def prepare(raw, output_dir):
    original = json.loads(raw.decode("utf-8-sig"))
    features = sorted(
        [f for f in original["features"] if f["properties"]["CD_DEPA"] != "99"],
        key=lambda f: f["properties"]["CD_DEPA"],
    )
    if [f["properties"]["CD_DEPA"] for f in features] != [f"{i:02}" for i in range(1, 26)]:
        raise ValueError("La fuente no contiene exactamente los 25 códigos esperados")
    geometries = [shape(f["geometry"]) for f in features]
    if not all(g.is_valid and not g.is_empty for g in geometries):
        raise ValueError("Geometrías originales inválidas")
    if not shapely.coverage_is_valid(geometries):
        raise ValueError("La cobertura original tiene superposiciones")
    simplified = shapely.coverage_simplify(geometries, tolerance=0.001)
    changes = []
    for f, before, after in zip(features, geometries, simplified):
        change = abs(after.area / before.area - 1)
        if (after.is_empty or not after.is_valid or change > 0.005
                or shapely.get_num_geometries(before) != shapely.get_num_geometries(after)):
            raise ValueError("La simplificación alteró una unidad o eliminó una parte")
        changes.append(change)
        f["geometry"] = mapping(after)
        f["properties"] = {k: f["properties"][k] for k in ("CD_DEPA", "NM_DEPA", "FEC_ING")}
    if not shapely.coverage_is_valid(simplified):
        raise ValueError("La simplificación alteró la topología de la cobertura")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "peru_departamentos.geojson"
    output.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    manifest = {
        "fuente": "INGEMMET, GEOCATMIN, capa Departamentos (0)",
        "url": SOURCE, "consulta": QUERY, "fecha_acceso": date.today().isoformat(),
        "crs": "EPSG:4326", "sha256_descarga_original": hashlib.sha256(raw).hexdigest(),
        "sha256_geojson": hashlib.sha256(output.read_bytes()).hexdigest(),
        "features_originales": len(original["features"]), "features_finales": len(features),
        "excluidos_CD_DEPA_99": len(original["features"]) - len(features),
        "transformacion": "coverage_simplify, tolerancia 0.001 grados; límites compartidos conservados",
        "shapely": shapely.__version__, "max_cambio_relativo_area": max(changes),
        "partes_multipoligono_conservadas": True,
        "nota": "Límites referenciales; Lima completa 15; Callao separado 07. Atribución: INGEMMET.",
    }
    (output_dir / "cartografia_fuente.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.source:
        raw = args.source.read_bytes()
    else:
        with urlopen(QUERY, timeout=120) as response:
            raw = response.read()
    prepare(raw, Path(__file__).resolve().parent / "data")
