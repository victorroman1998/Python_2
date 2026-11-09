"""Descarga y valida los microdatos oficiales de ENAHO 2024."""

import argparse
from pathlib import Path
import sys
from zipfile import BadZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from enaho import RAIZ, VALIDACION, limpiar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=RAIZ / "datos")
    parser.add_argument("--salidas", type=Path, default=RAIZ / "salidas")
    parser.add_argument("--sin-descarga", action="store_true", help="Usa solo archivos locales.")
    args = parser.parse_args()
    try:
        indicadores = limpiar(args.datos, args.salidas, not args.sin_descarga)
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(1, f"ENAHO rechazada. {error}\nConsulta {args.salidas / VALIDACION}.\n")
    for fila in indicadores.query("grupo == 'nacional' or grupo == 'area'").itertuples():
        print(f"{fila.metodo} | {fila.ambito} | {fila.pobreza_pct:.6f} % "
              f"| denominador: {fila.poblacion_expandida:.2f}")
    print(f"Validación aprobada en {args.salidas / VALIDACION}.")


if __name__ == "__main__":
    main()
