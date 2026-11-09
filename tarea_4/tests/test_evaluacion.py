"""Consistencia del patrón, las condiciones, las trazas y las métricas."""

from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

import pytest


RAIZ = Path(__file__).resolve().parents[1]
EVALUACION = RAIZ / "evaluacion"
TRAZAS = RAIZ / "evidencias_ia/evaluacion"


def leer_csv(nombre):
    with (EVALUACION / nombre).open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


@pytest.fixture
def evaluador(monkeypatch):
    monkeypatch.syspath_prepend(str(EVALUACION))
    import calificar

    return calificar


def test_patron_prerregistrado():
    patron = EVALUACION / "preguntas.csv"
    registro = json.loads((EVALUACION / "prerregistro.json").read_text(encoding="utf-8"))
    preguntas = leer_csv(patron.name)
    assert sha256(patron.read_bytes()).hexdigest() == registro["preguntas_sha256"]
    assert Counter(f["categoria"] for f in preguntas) == {"BCRP": 4, "ENAHO": 4, "mixta": 2}
    assert [f["id"] for f in preguntas] == [f"Q{i:02}" for i in range(1, 11)]
    assert all(f["fuentes"].startswith("https://") for f in preguntas)
    assert all({"fuentes", "coberturas", "interpretacion"} <= json.loads(f["referencia_y_criterios"]).keys()
               for f in preguntas if f["categoria"] == "mixta")


def test_separacion_y_trazas(evaluador):
    filas = leer_csv("resultados.csv")
    preguntas = leer_csv("preguntas.csv")
    lote = json.loads((TRAZAS / "lote.json").read_text(encoding="utf-8"))
    patron = json.loads((EVALUACION / "prerregistro.json").read_text(encoding="utf-8"))
    assert lote["preguntas_sha256"] == patron["preguntas_sha256"]
    assert {(f["id"], f["condicion"]) for f in filas} == {
        (f["id"], modo) for f in preguntas for modo in "AB"}
    assert len(filas) == 20
    ids = [fila["sesion"] for fila in filas if fila["sesion"]]
    assert len(set(ids)) == len(ids)
    assert {fila["modelo"] for fila in filas} == {lote["modelo_solicitado"]}
    for pregunta in preguntas:
        pares = [fila for fila in filas if fila["id"] == pregunta["id"]]
        assert pares[0]["instruccion"] == pares[1]["instruccion"]
        assert pares[0]["instruccion"].endswith(pregunta["pregunta"])
    for fila in filas:
        inicio, eventos, fin = evaluador.leer_traza(EVALUACION / fila["transcripcion"])
        assert (inicio["pregunta"], inicio["condicion"]) == (fila["id"], fila["condicion"])
        assert (fin["sesion"], fin["respuesta"]) == (fila["sesion"], fila["respuesta"])
        assert fila["estado_ejecucion"] == fin["estado"]
        assert float(fila["segundos"]) == fin["segundos"] > 0
        assert {"--ignore-user-config", "--ignore-rules", "--ephemeral"} <= set(inicio["argv"])
        assert "resume" not in inicio["argv"]
        assert 'web_search="disabled"' in inicio["argv"]
        assert "permissions.evaluation.network.enabled=false" in inicio["argv"]
        assert len([e for e in eventos if e["type"] == "thread.started"]) == bool(fin["sesion"])
        archivos = inicio["insumos_sha256"]
        assert {nombre: archivos["datos/" + nombre] for nombre in patron["insumos_sha256"]} == (
            patron["insumos_sha256"])
        assert all(ruta.split("/")[0] not in {"salidas", "informes", "evidencias_ia", "evaluacion", ".git"}
                   for ruta in archivos)
        mcp_configurado = any(arg.startswith("mcp_servers.bcrp.command=") for arg in inicio["argv"])
        assert mcp_configurado == (fila["condicion"] == "B")
        if fila["condicion"] == "A":
            assert set(archivos) == {"datos/FUENTES.md", *("datos/" + x for x in patron["insumos_sha256"])}
            assert all(not h["herramienta"].startswith("MCP ") for h in evaluador.herramientas(eventos))
        else:
            assert {p.split("/")[2] for p in archivos if p.startswith(".agents/skills/")} == {
                "limpiando-enaho", "graficando-enaho", "mapeando-enaho"}
            assert "mcp/server.py" in archivos
    for modo in "AB":
        prueba = json.loads((TRAZAS / f"{modo}-aislamiento.json").read_text(encoding="utf-8"))
        assert prueba["codigo_salida"] == 0
        assert prueba["stdout"].splitlines() == ["PYTHON_OK", *["LECTURA_DENEGADA"] * 3]


def test_tolerancia_unidades_y_parciales(evaluador):
    criterios = {
        "tasa": {"esperado": "10.00", "unidad": "%", "tolerancia_absoluta": "0.05"},
        "brecha": {"esperado": "-0.72", "unidad": "pp", "tolerancia_absoluta": "0.01"},
    }
    revision = {"afirmacion_evaluable": True, "extraido": {"tasa": ["10,05", "%"], "brecha": ["-0.72", "pp"]}}
    assert evaluador.calificar(criterios, revision, True)[0] == "correcta"
    revision["extraido"]["brecha"] = ["0.72", "pp"]
    assert evaluador.calificar(criterios, revision, True)[0] == "parcial"
    revision["extraido"]["tasa"] = ["10,05", "pp"]
    assert evaluador.calificar(criterios, revision, True)[0] == "incorrecta"
    revision["extraido"]["tasa"] = ["10,05001", "%"]
    assert evaluador.calificar(criterios, revision, True)[0] == "incorrecta"
    assert evaluador.calificar(criterios, revision, False)[0] == "no contestada"


def test_resultados_regenerables(evaluador):
    notas = json.loads((EVALUACION / "revision.json").read_text(encoding="utf-8"))
    regeneradas = evaluador.generar_filas(leer_csv("preguntas.csv"), notas, TRAZAS)
    publicadas = leer_csv("resultados.csv")
    assert [{k: "" if v is None else str(v) for k, v in fila.items()} for fila in regeneradas] == publicadas
    for modo in "AB":
        m = evaluador.metricas(regeneradas, modo)
        grupo = [f for f in publicadas if f["condicion"] == modo]
        assert sum(m[estado] for estado in evaluador.ESTADOS) == 10
        assert sum(int(f["acierto"]) for f in grupo) == m["correcta"]
        assert m["media"] == pytest.approx(sum(float(f["segundos"]) for f in grupo) / 10)
    assert evaluador.resumen(regeneradas) in (EVALUACION / "comparacion.md").read_text(encoding="utf-8")
