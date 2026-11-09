"""Grafica tasas ponderadas de pobreza a partir de un lote ENAHO validado."""

import argparse
from math import ceil
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from enaho import AMBITOS, RAIZ, cargar_indicadores_validados, exigir

TITULOS = {
    "area": "Pobreza monetaria por área de residencia",
    "sexo": "Pobreza monetaria por sexo",
    "departamento": "Pobreza monetaria por departamento",
}
FUENTE = "Fuente · INEI, ENAHO 2024, módulos 02 y 34. Estimaciones con facpob07."


def dibujar(indicadores, grupo):
    tasas = indicadores.loc[indicadores.metodo.eq("personas") & indicadores.grupo.eq(grupo)]
    exigir(tasas.codigo.is_unique and set(tasas.codigo) == AMBITOS[grupo].keys()
           and tasas.pobreza_pct.between(0, 100).all(),
           f"Indicadores inválidos o incompletos para {grupo}.")
    tasas = tasas.sort_values("pobreza_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(8.4, 2.9 if len(tasas) == 2 else 10.5), layout="constrained")
    barras = ax.barh(tasas.ambito, tasas.pobreza_pct, color="#176b77", height=0.66, zorder=2)
    etiquetas = [f"{valor:.2f}".replace(".", ",") + " %" for valor in tasas.pobreza_pct]
    ax.bar_label(barras, labels=etiquetas, padding=5, color="#163843", fontsize=9)
    ax.invert_yaxis()
    maximo = indicadores.loc[indicadores.metodo.eq('personas'), 'pobreza_pct'].max()
    ax.set_xlim(0, max(10, ceil((maximo + 5) / 10) * 10))
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.set_xlabel("Personas en situación de pobreza (%)", labelpad=8)
    ax.set_title(f"{TITULOS[grupo]} · Perú, 2024", loc="left", pad=14, weight="bold")
    ax.grid(axis="x", color="#dbe5e7")
    ax.tick_params(length=0, pad=6)
    ax.spines[:].set_visible(False)
    ax.set_ylabel("")
    fig.supxlabel(FUENTE, fontsize=8, color="#465a63", x=0.015, ha="left")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salidas", type=Path, default=RAIZ / "salidas")
    parser.add_argument("--figuras", type=Path, default=RAIZ / "figuras")
    parser.add_argument("--grupo", choices=TITULOS, help="Por defecto genera los tres gráficos.")
    args = parser.parse_args()
    try:
        indicadores = cargar_indicadores_validados(args.salidas)
        args.figuras.mkdir(parents=True, exist_ok=True)
        for grupo in ([args.grupo] if args.grupo else TITULOS):
            fig = dibujar(indicadores, grupo)
            ruta = args.figuras / f"pobreza_{grupo}_2024.png"
            fig.savefig(ruta, dpi=250, facecolor="white")
            plt.close(fig)
            print(f"Generado {ruta}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
