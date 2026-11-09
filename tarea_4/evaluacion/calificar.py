"""Aplica los criterios prerregistrados a la extracción revisada y genera la comparación."""

import argparse
from collections import Counter
import csv
from decimal import Decimal
import json
from pathlib import Path
from statistics import mean

from ejecutar import CONDICIONES, RAIZ, huella


ESTADOS = ("no contestada", "incorrecta", "parcial", "correcta")
UNIDADES_NUMERICAS = {"%", "pp", "meses"}


def comprobar(criterio, observado):
    if observado is None:
        return False
    valor, unidad = observado
    if unidad != criterio["unidad"]:
        return False
    if unidad in UNIDADES_NUMERICAS:
        numero = Decimal(valor.replace(",", "."))
        return numero.is_finite() and abs(numero - Decimal(criterio["esperado"])) <= Decimal(
            criterio["tolerancia_absoluta"])
    if unidad == "texto":
        return valor is True
    return valor.casefold() == criterio["esperado"].casefold()


def calificar(criterios, revision, hay_respuesta):
    extraido = revision["extraido"]
    if extraido.keys() - criterios.keys():
        raise ValueError("La revisión contiene un criterio ajeno a la pregunta.")
    aciertos = {nombre: comprobar(criterio, extraido.get(nombre))
                for nombre, criterio in criterios.items()}
    if not hay_respuesta or not revision["afirmacion_evaluable"]:
        return "no contestada", aciertos
    if all(aciertos.values()):
        return "correcta", aciertos
    if any(aciertos.values()):
        return "parcial", aciertos
    return "incorrecta", aciertos


def herramientas(eventos):
    invocaciones = Counter()
    for evento in eventos:
        if evento["type"] != "item.completed":
            continue
        item = evento["item"]
        tipo = item["type"]
        if tipo == "mcp_tool_call":
            nombre = f"MCP {item['server']}/{item['tool']}"
            invocaciones[(nombre, item.get("status"), bool(item.get("error")))] += 1
        elif tipo == "command_execution":
            codigo = item.get("exit_code")
            invocaciones[("terminal", item.get("status"), codigo != 0)] += 1
        elif tipo in {"web_search", "file_change", "dynamic_tool_call", "collab_tool_call"}:
            invocaciones[(tipo, item.get("status"), bool(item.get("error")))] += 1
    return [{"herramienta": nombre, "estado": estado, "fallo": fallo, "veces": n}
            for (nombre, estado, fallo), n in sorted(invocaciones.items(), key=lambda par: str(par[0]))]


def leer_traza(ruta):
    eventos = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    inicio, fin = eventos[0], eventos[-1]
    if inicio["type"] != "evaluacion.inicio" or fin["type"] != "evaluacion.fin":
        raise ValueError(f"Traza incompleta: {ruta}")
    return inicio, eventos[1:-1], fin


def generar_filas(preguntas, revision, evidencias):
    filas = []
    for pregunta in preguntas:
        id_pregunta = pregunta["id"]
        criterios = json.loads(pregunta["referencia_y_criterios"])
        for modo in CONDICIONES:
            nombre = f"{modo}-{id_pregunta}"
            ruta = evidencias / f"{nombre}.jsonl"
            if not ruta.is_file():
                continue
            inicio, eventos, fin = leer_traza(ruta)
            if (inicio["pregunta"], inicio["condicion"]) != (id_pregunta, modo):
                raise ValueError(f"Traza en ruta equivocada: {ruta}")
            notas = revision[nombre]
            etiqueta, aciertos = calificar(criterios, notas, bool(fin["respuesta"]))
            errores = [e.get("message", e.get("error")) for e in eventos
                       if e["type"] in {"error", "turn.failed"}]
            errores += [e["item"].get("message") for e in eventos if e["type"] == "item.completed"
                        and e["item"]["type"] == "error"
                        and not e["item"].get("message", "").startswith("Under-development features enabled:")]
            for evento in eventos:
                if evento["type"] != "item.completed":
                    continue
                item = evento["item"]
                if item["type"] == "command_execution" and item.get("exit_code") != 0:
                    errores.append(f"{item['id']}: terminal, salida {item.get('exit_code')}")
                if item["type"] == "mcp_tool_call" and (item.get("error") or item.get("status") == "failed"):
                    errores.append(f"{item['id']}: MCP {item['server']}/{item['tool']}: {item.get('error')}")
            if fin["error_ejecucion"]:
                errores.append(fin["error_ejecucion"])
            filas.append({
                "id": id_pregunta, "categoria": pregunta["categoria"], "condicion": modo,
                "sesion": fin["sesion"], "modelo": inicio["modelo_solicitado"],
                "inicio_peru": inicio["inicio_peru"], "instruccion": inicio["instruccion"],
                "respuesta": fin["respuesta"], "estado_ejecucion": fin["estado"],
                "segundos": fin["segundos"], "codigo_salida": fin["codigo_salida"],
                "clasificacion": etiqueta, "acierto": int(etiqueta == "correcta"),
                "componentes_extraidos": json.dumps(notas["extraido"], ensure_ascii=False),
                "componentes_cumplidos": json.dumps(aciertos, ensure_ascii=False),
                "fuentes_observadas": notas["fuentes"],
                "skills_observadas": notas["skills"],
                "herramientas_invocadas": json.dumps(herramientas(eventos), ensure_ascii=False),
                "errores": json.dumps(errores, ensure_ascii=False), "observaciones": notas["notas"],
                "transcripcion": "../evidencias_ia/evaluacion/" + ruta.name,
            })
    return filas


def metricas(filas, modo):
    sesiones = [f for f in filas if f["condicion"] == modo]
    tiempos = [float(f["segundos"]) for f in sesiones if f["segundos"] not in ("", None)]
    cuenta = Counter(f["clasificacion"] for f in sesiones)
    return {**{etiqueta: cuenta[etiqueta] for etiqueta in ESTADOS},
            "intentos": len(sesiones), "mediciones": len(tiempos),
            "media": mean(tiempos) if tiempos else None}


def cambios(filas):
    por_pregunta = {(f["id"], f["condicion"]): f["clasificacion"] for f in filas}
    diferencias = {}
    for id_pregunta in sorted({f["id"] for f in filas}):
        a, b = (por_pregunta.get((id_pregunta, modo)) for modo in CONDICIONES)
        if a and b:
            diferencia = ESTADOS.index(b) - ESTADOS.index(a)
            diferencias[id_pregunta] = "mejoró" if diferencia > 0 else "empeoró" if diferencia < 0 else "igual"
        else:
            diferencias[id_pregunta] = "sin par"
    return diferencias


def resumen(filas):
    lineas = [
        "| Modo | Intentos | Correctas | Incorrectas | Parciales | No contestadas | Media (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for modo in CONDICIONES:
        m = metricas(filas, modo)
        promedio = "—" if m["media"] is None else f"{m['media']:.2f} (n={m['mediciones']})"
        lineas.append(f"| {modo} | {m['intentos']} | {m['correcta']} | {m['incorrecta']} | "
                      f"{m['parcial']} | {m['no contestada']} | {promedio} |")
    lineas += ["", "| Pregunta | A | B | Cambio |", "| --- | --- | --- | --- |"]
    por_par = {(f["id"], f["condicion"]): f for f in filas}
    for pregunta, cambio in cambios(filas).items():
        celdas = []
        for modo in CONDICIONES:
            fila = por_par.get((pregunta, modo))
            if fila is None:
                celdas.append("Sin intento registrado")
            else:
                nota = fila["observaciones"].replace("|", r"\|")
                celdas.append(f"[{fila['clasificacion']}]({fila['transcripcion']}) "
                              f"({fila['segundos']:.2f} s). {nota}")
        lineas.append(f"| {pregunta} | {celdas[0]} | {celdas[1]} | {cambio} |")
    return "\n".join(lineas) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidencias", type=Path, default=RAIZ / "evidencias_ia/evaluacion")
    parser.add_argument("--salida", type=Path, default=RAIZ / "evaluacion/resultados.csv")
    args = parser.parse_args()
    carpeta = RAIZ / "evaluacion"
    patron = carpeta / "preguntas.csv"
    prerregistro = json.loads((carpeta / "prerregistro.json").read_text(encoding="utf-8"))
    if huella(patron) != prerregistro["preguntas_sha256"]:
        raise SystemExit("Las preguntas no coinciden con el prerregistro.")
    with patron.open(encoding="utf-8", newline="") as archivo:
        preguntas = list(csv.DictReader(archivo))
    revision = json.loads((carpeta / "revision.json").read_text(encoding="utf-8"))
    filas = generar_filas(preguntas, revision, args.evidencias)
    if not filas:
        raise SystemExit("Sin trazas de preguntas ejecutadas.")
    with args.salida.open("x", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=filas[0], lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)
    print(resumen(filas))


if __name__ == "__main__":
    main()
