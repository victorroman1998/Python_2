"""Pruebas de comparar_series a través de un cliente MCP en memoria."""

import httpx
import pytest
from fastmcp.exceptions import ToolError

import server
from test_server import llamar


def test_comparar_alinea_periodos_y_declara_faltantes(monkeypatch):
    fichas = {
        codigo: {"codigo": codigo, "frecuencia": "Mensual"}
        for codigo in ("PN01271PM", "PN01273PM")
    }
    monkeypatch.setattr(server, "_ficha", fichas.__getitem__)
    respuestas = {
        "PN01271PM": [("Mar.2025", "4"), ("Feb.2025", "n.d."), ("Ene.2025", "0")],
        "PN01273PM": [("Abr.2025", "9"), ("Ene.2025", "2"), ("Mar.2025", "6")],
    }

    def responder(url, **_):
        codigo = url.split("/")[-4]
        periodos = [{"name": nombre, "values": [valor]} for nombre, valor in respuestas[codigo]]
        return httpx.Response(200, json={"periods": periodos}, request=httpx.Request("GET", url))

    monkeypatch.setattr(server.httpx, "get", responder)
    server._periodos.cache_clear()
    try:
        r = llamar(
            "comparar_series", codigo_a="PN01271PM", codigo_b="PN01273PM",
            desde="2025-1", hasta="2025-04",
        )
    finally:
        server._periodos.cache_clear()

    assert r["frecuencia"] == "Mensual"
    assert r["n_pares"] == 2
    assert r["datos"] == [
        {"periodo": "2025-01", "valor_a": 0, "valor_b": 2},
        {"periodo": "2025-03", "valor_a": 4, "valor_b": 6},
    ]
    assert r["faltantes"] == {"PN01271PM": ["2025-02", "2025-04"], "PN01273PM": ["2025-02"]}
    assert r["correlacion_pearson"] == pytest.approx(1.0)
    assert r["serie_a"]["fuente"] == f"{server.API}/PN01271PM/json/2025-1/2025-4"


def test_comparar_rechaza_frecuencias_distintas(monkeypatch):
    fichas = {
        "PN01271PM": {"codigo": "PN01271PM", "frecuencia": "Mensual"},
        "PD04638PD": {"codigo": "PD04638PD", "frecuencia": "Diaria"},
    }
    monkeypatch.setattr(server, "_ficha", fichas.__getitem__)

    def consulta_inesperada(*args, **kwargs):
        pytest.fail("La frecuencia debe validarse antes de consultar observaciones.")

    monkeypatch.setattr(server.httpx, "get", consulta_inesperada)
    with pytest.raises(ToolError, match="Frecuencias incompatibles.*Mensual.*Diaria"):
        llamar(
            "comparar_series", codigo_a="PN01271PM", codigo_b="PD04638PD",
            desde="2025-01", hasta="2025-04",
        )
