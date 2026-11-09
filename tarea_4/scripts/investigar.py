"""Integra BCRP por MCP stdio y las Skills ENAHO 2024 desde tarea_4/."""

import argparse
import asyncio
import filecmp
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
import pandas as pd
from fastmcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enaho import (
    INDICADORES, PARQUET, RAIZ, VALIDACION, cargar_indicadores_validados, exigir, huella,
    preparar_archivo,
)
from scripts.verificar_cifras import MODULOS, verificar_y_redactar

LIMA = timezone(timedelta(hours=-5))
PERIODO = {"desde": "2020-01", "hasta": "2024-12"}
GRUPO_IPC = "Índice de precios Lima Metropolitana (var% 12 meses)"
HERRAMIENTAS = {"buscar_series", "serie", "resumen", "comparar_series"}
SKILLS = {
    "limpiando-enaho": "limpiar",
    "graficando-enaho": "graficar",
    "mapeando-enaho": "mapear",
}


def evento(bitacora, nombre, **detalle):
    registro = {"fecha": datetime.now(LIMA).isoformat(timespec="milliseconds"),
                "evento": nombre, **detalle}
    with bitacora.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def publicar(origen, destino):
    """Instala el archivo solo si difiere, con reemplazo atómico por archivo."""
    if destino.is_file() and filecmp.cmp(origen, destino, shallow=False):
        return "reutilizado"
    with TemporaryDirectory(dir=destino.parent) as directorio:
        copia = Path(directorio) / destino.name
        shutil.copyfile(origen, copia)
        copia.replace(destino)
    return "publicado"


def sin_rutas_privadas(texto):
    for ruta, etiqueta in ((RAIZ, "."), (Path.home(), "[perfil local]")):
        texto = texto.replace(str(ruta), etiqueta).replace(ruta.as_posix(), etiqueta)
    return texto


async def consultar_bcrp(bitacora, trabajo):
    config = json.loads(Path(".mcp.json").read_text(encoding="utf-8"))
    servidor = config["mcpServers"]["bcrp"]
    evento(bitacora, "mcp_inicio", transporte=servidor["type"],
           comando=[servidor["command"], *servidor["args"]], configuracion=".mcp.json")
    respuestas = {}

    async with Client(config, timeout=180) as cliente:
        disponibles = {t.name for t in await cliente.list_tools()}
        evento(bitacora, "mcp_tools/list", herramientas=sorted(disponibles))
        exigir(HERRAMIENTAS <= disponibles, "Faltan herramientas en el servidor BCRP.")

        async def llamar(nombre, clave, **parametros):
            evento(bitacora, "mcp_tools/call", herramienta=nombre, parametros=parametros)
            resultado = (await cliente.call_tool(nombre, parametros)).data
            respuestas[clave] = {"herramienta": nombre, "parametros": parametros, "respuesta": resultado}
            evento(bitacora, "mcp_respuesta", herramienta=nombre,
                   archivo="salidas/bcrp_mcp.json", clave=clave)

        for clave, texto in (
            ("buscar_nacional", "ipc nacional"),
            ("buscar_alimentos", "ipc alimentos bebidas 12 meses"),
            ("buscar_general", "ipc lima metropolitana 12 meses"),
        ):
            await llamar("buscar_series", clave, texto=texto, frecuencia="Mensual", limite=100)

        elegidas = {}
        for clave, etiqueta in (("alimentos", "IPC Alimentos y Bebidas"), ("general", "IPC")):
            candidatas = [fila for fila in respuestas[f"buscar_{clave}"]["respuesta"]
                          if fila["nombre"] == f"{GRUPO_IPC} - {etiqueta}"
                          and fila["frecuencia"] == "Mensual" and fila["fuente_original"] == "INEI"]
            exigir(len(candidatas) == 1, f"El catálogo no identifica una única serie para {etiqueta}.")
            elegidas[clave] = candidatas[0]["codigo"]
        evento(bitacora, "mcp_seleccion", codigos=elegidas, cobertura="Lima Metropolitana",
               unidad="variación a 12 meses (%)")

        for clave, codigo in elegidas.items():
            for herramienta in ("serie", "resumen"):
                await llamar(herramienta, f"{herramienta}_{clave}", codigo=codigo, **PERIODO)
        await llamar("comparar_series", "comparacion", codigo_a=elegidas["alimentos"],
                     codigo_b=elegidas["general"], **PERIODO)

    (trabajo / "bcrp_mcp.json").write_text(
        json.dumps(respuestas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    evento(bitacora, "mcp_fin", llamadas=len(respuestas))
    return {clave: registro["respuesta"] for clave, registro in respuestas.items()}


def preparar_bcrp(bcrp, trabajo):
    """Comprueba coherencia de los contratos MCP y grafica las observaciones."""
    periodos = pd.period_range(PERIODO["desde"], PERIODO["hasta"], freq="M").astype(str).tolist()
    comparar = bcrp["comparacion"]
    exigir(comparar["n_pares"] == len(periodos) and not any(comparar["faltantes"].values())
           and [fila["periodo"] for fila in comparar["datos"]] == periodos,
           "La comparación no contiene los 60 meses completos en orden.")
    tabla = pd.DataFrame({"periodo": periodos})
    for clave, lado in (("alimentos", "a"), ("general", "b")):
        serie, resumen = bcrp[f"serie_{clave}"], bcrp[f"resumen_{clave}"]
        filas = serie["datos"]
        valores = [fila["valor"] for fila in filas]
        exigir([fila["periodo"] for fila in filas] == periodos and not serie["periodos_sin_dato"]
               and valores == [fila[f"valor_{lado}"] for fila in comparar["datos"]]
               and comparar[f"serie_{lado}"]["codigo"] == serie["codigo"] == resumen["codigo"]
               and resumen["n_observaciones"] == len(periodos)
               and (filas[0], filas[-1]) == (resumen["primero"], resumen["ultimo"])
               and resumen["maximo"] in filas and resumen["maximo"]["valor"] == max(valores)
               and resumen["minimo"] in filas and resumen["minimo"]["valor"] == min(valores),
               f"Respuestas MCP incompatibles para {clave}.")
        tabla[serie["codigo"]] = valores

    cod_a, cod_b = tabla.columns[1:]
    tabla["brecha_pp"] = (tabla[cod_a] - tabla[cod_b]).round(8)
    tabla.to_csv(trabajo / "inflacion_lima_2020_2024.csv", index=False)

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.dates import DateFormatter, YearLocator

    fechas = pd.to_datetime(tabla.periodo)
    fig, ax = plt.subplots(figsize=(9.4, 4.8), layout="constrained")
    ax.plot(fechas, tabla[cod_a], color="#00717c", lw=2.5, label=f"Alimentos y bebidas ({cod_a})")
    ax.plot(fechas, tabla[cod_b], color="#75411f", lw=2, linestyle="--", label=f"IPC general ({cod_b})")
    pico = bcrp["resumen_alimentos"]["maximo"]
    ax.scatter(pd.Timestamp(pico["periodo"]), pico["valor"], color="#00717c", zorder=4)
    ax.annotate(f"{pico['valor']:.2f} %".replace(".", ","), (pd.Timestamp(pico["periodo"]), pico["valor"]),
                xytext=(10, 5), textcoords="offset points", color="#00545c")
    ax.set_ylim(top=pico["valor"] + 2)
    ax.xaxis.set_major_locator(YearLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y"))
    ax.set_xlim(fechas.iloc[0], fechas.iloc[-1])
    ax.axhline(0, color="#758087", linewidth=0.8)
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["right", "top"]].set_visible(False)
    ax.set_ylabel("Variación respecto al mismo mes del año previo (%)")
    ax.set_title("Inflación en Lima Metropolitana · enero 2020 a diciembre 2024",
                 loc="left", weight="bold")
    ax.legend(frameon=False, loc="upper left")
    fig.supxlabel("Fuente · BCRPData (series del INEI). Frecuencia mensual.", fontsize=9, x=0.02, ha="left")
    fig.savefig(trabajo / "inflacion_lima_2020_2024.png", dpi=200)
    plt.close(fig)
    return tabla


def ejecutar_skill(skill, bitacora, **opciones):
    ruta = f".claude/skills/{skill}/scripts/{SKILLS[skill]}.py"
    comando = ["uv", "run", "--locked", "python", ruta]
    for opcion, valor in opciones.items():
        bandera = "--" + opcion.replace("_", "-")
        if valor is True:
            comando.append(bandera)
        elif valor is not False:
            comando.extend([bandera, str(valor)])

    evento(bitacora, "skill_inicio", skill=skill, comando=comando)
    proceso = subprocess.run(comando, capture_output=True, encoding="utf-8", errors="replace",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    evento(bitacora, "skill_fin", skill=skill, retorno=proceso.returncode,
           stdout=sin_rutas_privadas(proceso.stdout), stderr=sin_rutas_privadas(proceso.stderr))
    exigir(proceso.returncode == 0, f"Falló {skill}. Consulta la bitácora.")


def ejecutar_enaho(bitacora, trabajo, datos, salidas, sin_descarga):
    try:
        indicadores = cargar_indicadores_validados(salidas)
    except ValueError as error:
        evento(bitacora, "enaho_lote", estado="requiere limpieza", causa=sin_rutas_privadas(str(error)))
        salidas = trabajo / "enaho"
        ejecutar_skill("limpiando-enaho", bitacora, datos=datos, salidas=salidas,
                       sin_descarga=sin_descarga)
        indicadores = cargar_indicadores_validados(salidas)
    evento(bitacora, "enaho_lote", estado="APROBADO", indicadores_sha256=huella(salidas / INDICADORES),
           validacion_sha256=huella(salidas / VALIDACION), parquet_sha256=huella(salidas / PARQUET))
    ejecutar_skill("graficando-enaho", bitacora, salidas=salidas, figuras=trabajo / "figuras")
    ejecutar_skill("mapeando-enaho", bitacora, datos=datos, salidas=salidas, mapas=trabajo / "mapas",
                   sin_descarga=sin_descarga)
    return indicadores, salidas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-descarga", action="store_true", help="Usa insumos ENAHO locales.")
    parser.add_argument("--desde-cero", action="store_true", help="Comprueba la dependencia con un lote vacío aislado.")
    parser.add_argument("--bitacora", type=Path, default=Path("evidencias_ia/integracion/ejecucion_local.jsonl"))
    args = parser.parse_args()
    os.chdir(RAIZ)
    bitacora = args.bitacora
    bitacora.parent.mkdir(parents=True, exist_ok=True)
    try:
        bitacora.touch(exist_ok=False)
    except FileExistsError:
        parser.error("La bitácora ya existe. Usa --bitacora con un nombre nuevo.")
    evento(bitacora, "inicio", desde_cero=args.desde_cero, sin_descarga=args.sin_descarga)

    try:
        plan = Path("informes/plan_investigacion.md")
        evento(bitacora, "plan", archivo=plan.as_posix(), texto=plan.read_text(encoding="utf-8-sig"))
        for skill, script in SKILLS.items():
            directorio = Path(".claude/skills") / skill
            contrato = directorio / "SKILL.md"
            exigir(f"name: {skill}\n" in contrato.read_text(encoding="utf-8")
                   and (directorio / "scripts" / f"{script}.py").is_file(),
                   f"Skill incompleta: {skill}.")
            evento(bitacora, "skill_disponible", skill=skill, contrato=contrato.as_posix(),
                   sha256=huella(contrato))

        datos = Path("datos")
        with TemporaryDirectory(dir=datos, prefix="integracion-") as directorio:
            trabajo = Path(directorio).resolve().relative_to(RAIZ)
            bcrp = asyncio.run(consultar_bcrp(bitacora, trabajo))
            tabla = preparar_bcrp(bcrp, trabajo)
            evento(bitacora, "bcrp_validado", meses=len(tabla), faltantes=0)
            entrada = trabajo / "vacio" if args.desde_cero else Path("salidas")
            indicadores, lote = ejecutar_enaho(bitacora, trabajo, datos, entrada, args.sin_descarga)
            for modulo in MODULOS:
                preparar_archivo(datos, modulo, not args.sin_descarga)
            controles = verificar_y_redactar(bcrp, tabla, indicadores, datos, trabajo)
            evento(bitacora, "contrastes", controles=controles)

            productos = {trabajo / nombre: Path("salidas") / nombre for nombre in
                         ("bcrp_mcp.json", "inflacion_lima_2020_2024.csv", "contrastes_fase3.json")}
            productos[trabajo / "inflacion_lima_2020_2024.png"] = Path("figuras/inflacion_lima_2020_2024.png")
            for directorio, nombres in (
                ("figuras", ("pobreza_area_2024.png", "pobreza_sexo_2024.png", "pobreza_departamento_2024.png")),
                ("mapas", ("pobreza_departamento_2024.png",)),
            ):
                productos.update({trabajo / directorio / nombre: Path(directorio) / nombre for nombre in nombres})
            productos.update({lote / nombre: Path("salidas") / nombre for nombre in
                              (PARQUET, INDICADORES, VALIDACION)})
            productos.update({trabajo / nombre: Path("informes") / nombre for nombre in
                              ("informe_final.md", "verificacion_cifras.md")})

            for origen, destino in productos.items():
                exigir(origen.is_file() and origen.stat().st_size > 0, f"Falta {destino.as_posix()}.")
            for origen, destino in productos.items():
                estado = "reutilizado" if origen == destino else publicar(origen, destino)
                huellas = {"sha256": huella(destino)}
                if destino.suffix in {".csv", ".json", ".md", ".txt"}:
                    huellas["sha256_lf"] = sha256(destino.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                evento(bitacora, "archivo", estado=estado, ruta=destino.as_posix(),
                       local=destino.suffix == ".parquet", **huellas)
        evento(bitacora, "fin", estado="APROBADO")
        print(f"Integración aprobada. Consulta {bitacora.as_posix()}.")
    except Exception as error:
        mensaje = sin_rutas_privadas(str(error))
        evento(bitacora, "fin", estado="FALLÓ", tipo=type(error).__name__, error=mensaje)
        parser.exit(1, f"{mensaje}\n")


if __name__ == "__main__":
    main()
