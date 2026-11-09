"""Ejecuta el protocolo de Codex en Windows con MXC y guarda una traza por sesión."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
from tempfile import mkdtemp
from time import perf_counter

from referencias import BCRP, INEI, MODULOS, RAIZ, SERIES


MODELO = "gpt-6.1-sol"
LIMITE_SEGUNDOS = 360
CONCURRENCIA = 4
SEMILLA = 20261108
PERU = timezone(timedelta(hours=-5))
HABILIDADES = ("limpiando-enaho", "graficando-enaho", "mapeando-enaho")
CONDICIONES = ("A", "B")
INSTRUCCION = """Responde en español a esta pregunta usando evidencia verificable.
En datos/ están los insumos originales y FUENTES.md identifica su procedencia.
Si tienes herramientas especializadas pertinentes, úsalas para consultar o calcular.
Incluye valores, unidades, períodos, fuentes y un procedimiento breve que permita comprobarlos.
Informa cualquier dato que no hayas podido verificar. Trabaja dentro del directorio actual.
Usa solo resultados de esta sesión. Nunca imprimas filas individuales ni llaves muestrales.

"""


def huella(ruta):
    return sha256(ruta.read_bytes()).hexdigest()


def preparar(cwd, modo, macro, datos):
    entradas = cwd / "datos"
    entradas.mkdir(parents=True)
    (cwd / "tmp").mkdir()
    fuentes = []
    for archivo in MODULOS:
        shutil.copy2(datos / archivo, entradas)
        fuentes.append(f"- {archivo} (INEI, ENAHO 2024). {INEI + archivo}")
    for codigo, nombre in SERIES.items():
        shutil.copy2(macro / f"{codigo}.json", entradas)
        fuentes.append(f"- {codigo}.json (BCRPData, {nombre}, Lima Metropolitana, var% 12 meses). "
                       + BCRP.format(codigo))
    (entradas / "FUENTES.md").write_text("\n".join(fuentes) + "\n", encoding="utf-8")
    if modo == "B":
        for archivo in ("peru_departamental_simple.geojson", "pobreza_departamento_2024.csv"):
            shutil.copy2(datos / archivo, entradas)
        for archivo in ("enaho.py", "pyproject.toml", "uv.lock", "mcp/server.py", "datos/README.md"):
            destino = cwd / archivo
            destino.parent.mkdir(exist_ok=True)
            shutil.copy2(RAIZ / archivo, destino)
        catalogo = RAIZ / "mcp/datos/catalogo_bcrp.csv"
        if catalogo.is_file():
            (cwd / "mcp/datos").mkdir()
            shutil.copy2(catalogo, cwd / "mcp/datos")
        for nombre in HABILIDADES:
            origen = Path(".claude/skills") / nombre
            shutil.copytree(RAIZ / origen, cwd / origen)
            shutil.copytree(RAIZ / origen, cwd / ".agents/skills" / nombre)
    return {ruta.relative_to(cwd).as_posix(): huella(ruta)
            for ruta in sorted(cwd.rglob("*")) if ruta.is_file()}


def invocacion(cwd, modo, runtime, base_python, codex, uv, respuesta, prohibido):
    python = runtime / "Scripts/python.exe"
    windows = Path(os.environ["SystemRoot"])
    politica = {
        ":root": "deny", ":minimal": "read", ":workspace_roots": "write",
        str(RAIZ.parents[1]): "deny", str(prohibido): "deny",
        str(Path.home() / ".codex"): "deny",
        str(runtime): "read", str(base_python): "read", str(uv): "read",
    }
    entorno = {
        "PATH": os.pathsep.join(map(str, [runtime / "Scripts", uv.parent, windows / "System32", windows])),
        "UV_PROJECT_ENVIRONMENT": str(runtime), "UV_NO_SYNC": "1", "UV_OFFLINE": "1",
        "UV_CACHE_DIR": str(cwd / "tmp/uv"), "TMP": str(cwd / "tmp"), "TEMP": str(cwd / "tmp"),
        "PYTHONUTF8": "1", "MPLCONFIGDIR": str(cwd / "tmp/matplotlib"),
    }
    config = {
        "default_permissions": "evaluation",
        "approval_policy": "never",
        "windows.sandbox": "elevated",
        "permissions.evaluation.filesystem": politica,
        "permissions.evaluation.network.enabled": False,
        "web_search": "disabled",
        "shell_environment_policy.inherit": "core",
        "shell_environment_policy.set": entorno,
        "model_reasoning_effort": "low",
        "mcp_servers": {},
        **{f"features.{f}": False for f in (
            "apps", "plugins", "memories", "browser_use", "computer_use", "multi_agent",
            "shell_snapshot", "fast_mode", "skill_mcp_dependency_install")},
        "features.prefer_mxc": True,
    }
    if modo == "B":
        config["mcp_servers.bcrp.command"] = str(python)
        config["mcp_servers.bcrp.args"] = [str(cwd / "mcp/server.py")]
        config["mcp_servers.bcrp.cwd"] = str(cwd)
        config["mcp_servers.bcrp.startup_timeout_sec"] = 45
        config["mcp_servers.bcrp.tool_timeout_sec"] = 90
    comando = [codex, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
               "--skip-git-repo-check", "--json", "-C", str(cwd), "-m", MODELO,
               "--output-last-message", str(respuesta)]
    for clave, valor in config.items():
        if isinstance(valor, dict):
            valor_toml = "{" + ",".join(json.dumps(k) + "=" + json.dumps(v) for k, v in valor.items()) + "}"
        else:
            valor_toml = json.dumps(valor)
        comando += ["-c", f"{clave}={valor_toml}"]
    return [*comando, "-"]


def ocultar(objeto, sustituciones):
    if isinstance(objeto, dict):
        return {clave: ocultar(valor, sustituciones) for clave, valor in objeto.items()}
    if isinstance(objeto, list):
        return [ocultar(valor, sustituciones) for valor in objeto]
    if isinstance(objeto, str):
        for ruta, alias in sustituciones:
            for forma in {str(ruta), ruta.as_posix(), str(ruta).replace("\\", "\\\\")}:
                objeto = objeto.replace(forma, alias)
    return objeto


def sesion(id_pregunta, modo, instruccion, cwd, archivo, comando, sustituciones, insumos):
    inicio = datetime.now(PERU)
    reloj = perf_counter()
    error = ""
    try:
        proceso = subprocess.run(comando, input=instruccion.encode("utf-8"),
                                 capture_output=True, timeout=LIMITE_SEGUNDOS, cwd=cwd)
        salida, stderr, codigo = proceso.stdout, proceso.stderr, proceso.returncode
    except subprocess.TimeoutExpired as exc:
        salida, stderr, codigo = exc.stdout, exc.stderr, None
        error = f"Límite de {LIMITE_SEGUNDOS} segundos"
    except OSError as exc:
        salida, stderr, codigo = None, None, None
        error = str(exc)
    segundos = round(perf_counter() - reloj, 3)
    eventos = []
    for linea in (salida or b"").decode("utf-8", errors="replace").splitlines():
        try:
            eventos.append(json.loads(linea))
        except json.JSONDecodeError:
            eventos.append({"type": "registro.stdout", "text": linea})
    sesion_id = next((e["thread_id"] for e in eventos if e["type"] == "thread.started"), "")
    ultimo = Path(comando[comando.index("--output-last-message") + 1])
    respuesta = ultimo.read_text(encoding="utf-8").strip() if ultimo.is_file() else ""
    completa = any(e["type"] == "turn.completed" for e in eventos)
    if not respuesta and completa:
        mensajes = [e["item"]["text"] for e in eventos if e["type"] == "item.completed"
                    and e["item"]["type"] == "agent_message"]
        respuesta = mensajes[-1] if mensajes else ""
    estado = "completada" if codigo == 0 and completa and respuesta else "fallida"
    metadata = {
        "type": "evaluacion.inicio", "pregunta": id_pregunta, "condicion": modo,
        "inicio_peru": inicio.isoformat(), "modelo_solicitado": MODELO,
        "instruccion": instruccion, "argv": comando, "insumos_sha256": insumos,
    }
    cierre = {
        "type": "evaluacion.fin", "sesion": sesion_id, "respuesta": respuesta,
        "estado": estado, "segundos": segundos, "codigo_salida": codigo,
        "error_ejecucion": error, "stderr": (stderr or b"").decode("utf-8", errors="replace"),
    }
    with archivo.open("x", encoding="utf-8", newline="\n") as destino:
        for evento in [metadata, *eventos, cierre]:
            destino.write(json.dumps(ocultar(evento, sustituciones), ensure_ascii=False) + "\n")
    print(f"{modo}/{id_pregunta}: {estado} en {segundos:.3f} s", flush=True)
    return eventos, cierre


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bcrp", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--evidencias", type=Path, required=True)
    parser.add_argument("--solo-control", action="store_true")
    args = parser.parse_args()
    runtime, evidencias = args.runtime.resolve(), args.evidencias.resolve()
    if os.name != "nt" or runtime.is_relative_to(RAIZ.parents[1]):
        raise SystemExit("Se requiere Windows y un entorno Python fuera del directorio del proyecto.")
    python = runtime / "Scripts/python.exe"
    base_python = Path(subprocess.check_output([python, "-c", "import sys; print(sys.base_prefix)"],
                                              text=True).strip())
    codex, uv = shutil.which("codex"), shutil.which("uv")
    if not codex or not uv:
        raise SystemExit("Se requieren codex y uv en PATH.")
    patron = RAIZ / "evaluacion/preguntas.csv"
    prerregistro = json.loads((RAIZ / "evaluacion/prerregistro.json").read_text(encoding="utf-8"))
    if huella(patron) != prerregistro["preguntas_sha256"]:
        raise SystemExit("Las preguntas no coinciden con el prerregistro.")
    for archivo, esperado in prerregistro["insumos_sha256"].items():
        ruta = (args.bcrp if archivo.endswith(".json") else RAIZ / "datos") / archivo
        if huella(ruta) != esperado:
            raise SystemExit(f"Insumo diferente del prerregistro: {archivo}")
    with patron.open(encoding="utf-8", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    raiz = Path(mkdtemp(prefix="tarea4-fase4-", dir=runtime.parent))
    control = raiz / "privado"
    control.mkdir()
    canario = control / "canario.txt"
    canario.write_text("Control de lectura, sin respuestas.\n", encoding="utf-8")
    evidencias.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output([codex, "--version"], text=True).strip()
    print(version, flush=True)

    def ejecutar(id_pregunta, modo, instruccion):
        cwd = raiz / f"{modo}-{id_pregunta}"
        insumos = preparar(cwd, modo, args.bcrp, RAIZ / "datos")
        archivo = evidencias / f"{modo}-{id_pregunta}.jsonl"
        respuesta = control / f"{modo}-{id_pregunta}.txt"
        comando = invocacion(cwd, modo, runtime, base_python, codex, Path(uv), respuesta, control)
        reemplazos = [(cwd, "<SESION>"), (runtime, "<RUNTIME>"), (raiz, "<AISLAMIENTO>"),
                      (RAIZ.parents[1], "<PROYECTO>"), (base_python, "<PYTHON>"), (Path.home(), "<USUARIO>")]
        return sesion(id_pregunta, modo, instruccion, cwd, archivo, comando, reemplazos, insumos)

    control_codigo = ("from pathlib import Path; import pandas; "
                      "assert Path('datos/FUENTES.md').is_file(); print('PYTHON_OK');\n"
                      f"for ruta in {list(map(str, [canario, patron, RAIZ / 'salidas/indicadores.csv']))!r}:\n"
                      " try:\n  with open(ruta, 'rb') as f: f.read(0)\n"
                      " except PermissionError: print('LECTURA_DENEGADA')\n"
                      " else: print('LECTURA_PERMITIDA')\n")
    for modo in CONDICIONES:
        instruccion = ("Prueba técnica, fuera de la evaluación. Ejecuta exactamente este código Python "
                       "mediante una here-string de PowerShell conectada a python -. "
                       "La prueba no muestra contenido privado.\n\n" + control_codigo)
        if modo == "B":
            instruccion += ("\nAdemás llama a la herramienta MCP bcrp serie para PN01273PM 2019-01 a 2019-01. "
                            "Abre los tres SKILL.md de .agents/skills/ y ejecuta, sin procesar datos, "
                            "uv run --locked python .claude/skills/limpiando-enaho/scripts/limpiar.py --help.")
        eventos, cierre = ejecutar("control", modo, instruccion)
        items = [e["item"] for e in eventos if e["type"] == "item.completed"]
        terminal = "\n".join(i["aggregated_output"] for i in items
                             if i["type"] == "command_execution" and i["exit_code"] == 0)
        if (cierre["estado"] != "completada" or "PYTHON_OK" not in terminal
                or terminal.count("LECTURA_DENEGADA") != 3 or "LECTURA_PERMITIDA" in terminal):
            raise SystemExit(f"Control de aislamiento fallido en {modo}. Revisa su traza.")
        if modo == "B" and not any(i["type"] == "mcp_tool_call" and i.get("server") == "bcrp"
                                   and i.get("status") == "completed" and not i.get("error")
                                   for i in items):
            raise SystemExit("El MCP del BCRP no superó el control de conexión.")
    if args.solo_control:
        return

    pares = [(fila["id"], modo, INSTRUCCION + fila["pregunta"]) for fila in filas for modo in CONDICIONES]
    random.Random(SEMILLA).shuffle(pares)
    (evidencias / "lote.json").write_text(json.dumps({
        "cli": version, "modelo_solicitado": MODELO, "inicio_peru": datetime.now(PERU).isoformat(),
        "preguntas_sha256": huella(patron), "orden_de_envio": [(modo, q) for q, modo, _ in pares],
        "concurrencia_maxima": CONCURRENCIA, "limite_segundos": LIMITE_SEGUNDOS,
    }, indent=2) + "\n", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=CONCURRENCIA) as pool:
        pendientes = [pool.submit(ejecutar, q, modo, instruccion) for q, modo, instruccion in pares]
        for pendiente in pendientes:
            pendiente.result()


if __name__ == "__main__":
    main()
