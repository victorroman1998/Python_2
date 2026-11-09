"""Representa la pobreza de los 25 ámbitos departamentales de ENAHO 2024."""

import argparse
from math import ceil
from pathlib import Path
import sys

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import PercentFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from enaho import (
    DEPARTAMENTOS, GEOJSON, RAIZ, REFERENCIA, cargar_indicadores_validados,
    contrastar, exigir, huella, leer_referencia, normalizar_codigo, preparar_archivo,
)


def unir_geografia(geografia, tasas):
    exigir("FIRST_IDDP" in geografia, "Falta FIRST_IDDP en la geometría del curso.")
    exigir(geografia.crs is not None, "El GeoJSON no declara un sistema de coordenadas.")
    geometria = geografia.geometry
    exigir((geometria.notna() & ~geometria.is_empty & geometria.is_valid
            & geometria.geom_type.isin(["Polygon", "MultiPolygon"])).all(),
           "Hay geometrías vacías, inválidas o que no son polígonos.")
    geografia = geografia.assign(codigo=normalizar_codigo(geografia.FIRST_IDDP, 2, "FIRST_IDDP"))
    tasas = tasas.assign(codigo=normalizar_codigo(tasas.codigo, 2, "código departamental"))
    for datos, nombre in ((geografia, "GeoJSON"), (tasas, "Indicadores")):
        exigir(datos.codigo.is_unique and set(datos.codigo) == DEPARTAMENTOS.keys(),
               f"{nombre}: se requieren 25 códigos únicos del 01 al 25.")
    mapa = geografia.merge(tasas[["codigo", "pobreza_pct"]], on="codigo", how="left", validate="1:1")
    exigir(len(mapa) == 25 and mapa.pobreza_pct.between(0, 100).all(),
           "La unión territorial dejó tasas faltantes o inválidas.")
    return mapa


def dibujar_mapa(mapa):
    mapa = mapa.to_crs("EPSG:4326")
    normalizacion = Normalize(vmin=0, vmax=max(10, ceil(mapa.pobreza_pct.max() / 10) * 10))
    fig = plt.figure(figsize=(8.0, 8.9), facecolor="white")
    ax = fig.add_axes((0.07, 0.15, 0.68, 0.73))
    zoom = fig.add_axes((0.68, 0.21, 0.27, 0.24))
    barra = fig.add_axes((0.15, 0.10, 0.70, 0.022))
    estilo = dict(column="pobreza_pct", cmap="YlGnBu", norm=normalizacion, edgecolor="#4a6066")
    mapa.plot(ax=ax, linewidth=0.45, **estilo)
    mapa.plot(ax=zoom, linewidth=0.7, **estilo)
    ax.set_axis_off()
    zoom.set_xticks([])
    zoom.set_yticks([])
    zoom.set(xlabel="", ylabel="")
    zoom.spines[:].set_color("#a7b5bc")

    callao = mapa.loc[mapa.codigo.eq("07"), "geometry"].iloc[0]
    punto = callao.representative_point()
    oeste, sur, este, norte = callao.bounds
    zoom.set_xlim(oeste - 0.11, este + 0.15)
    zoom.set_ylim(sur - 0.06, norte + 0.03)
    zoom.set_title("Lima y Callao · detalle", loc="left", fontsize=10, weight="bold")
    zoom.annotate("Callao", xy=(punto.x, punto.y), xycoords="data",
                  xytext=(0.05, 0.19), textcoords="axes fraction",
                  arrowprops=dict(arrowstyle="-", color="#304752"), fontsize=9, color="#1d333e")
    zoom.text(0.76, 0.73, "Lima", transform=zoom.transAxes, fontsize=9,
              bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))

    escala = fig.colorbar(
        plt.cm.ScalarMappable(norm=normalizacion, cmap="YlGnBu"),
        cax=barra, orientation="horizontal", format=PercentFormatter(xmax=100, decimals=0),
    )
    escala.set_label("Personas en situación de pobreza (%)", labelpad=5)
    escala.outline.set_linewidth(0.4)
    fig.text(0.07, 0.94, "Pobreza monetaria por departamento", fontsize=21,
             weight="bold", color="#163843")
    fig.text(0.07, 0.904, "Perú · ENAHO 2024", fontsize=12, color="#465a63")
    fig.text(0.07, 0.029, "Fuente · INEI, ENAHO 2024, módulos 02 y 34 (facpob07). Límites · curso, Sesión 06.",
             fontsize=8, color="#465a63")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=RAIZ / "datos")
    parser.add_argument("--salidas", type=Path, default=RAIZ / "salidas")
    parser.add_argument("--mapas", type=Path, default=RAIZ / "mapas")
    parser.add_argument("--sin-descarga", action="store_true", help="Usa solo archivos locales.")
    args = parser.parse_args()
    try:
        indicadores = cargar_indicadores_validados(args.salidas)
        referencia = leer_referencia(preparar_archivo(args.datos, REFERENCIA, not args.sin_descarga))
        comprobaciones = contrastar(indicadores, referencia, ("departamento",))
        for pasa, mensaje in comprobaciones:
            print(f"{'APROBADO' if pasa else 'FALLÓ'} {mensaje}")
        exigir(all(pasa for pasa, _ in comprobaciones), "Falló el contraste departamental.")
        ruta_geojson = preparar_archivo(args.datos, GEOJSON, not args.sin_descarga)
        tasas = indicadores.query("metodo == 'personas' and grupo == 'departamento'")
        mapa = unir_geografia(gpd.read_file(ruta_geojson), tasas)
        print(f"GeoJSON SHA-256 {huella(ruta_geojson)}")
        print(f"Unión aprobada: {len(mapa)} geometrías válidas con tasa; Callao (07) y Lima (15) separados.")
        fig = dibujar_mapa(mapa)
        args.mapas.mkdir(parents=True, exist_ok=True)
        ruta = args.mapas / "pobreza_departamento_2024.png"
        fig.savefig(ruta, dpi=250, facecolor="white")
        plt.close(fig)
        print(f"Generado {ruta}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
