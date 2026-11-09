"""Regresiones del encadenamiento entre limpieza y consumidores de ENAHO."""

import json
from unittest.mock import Mock

import pytest

from scripts import investigar


@pytest.mark.parametrize("lote_aprobado", [False, True], ids=["reconstruir", "reutilizar"])
def test_ambos_consumidores_usan_el_mismo_lote(tmp_path, monkeypatch, lote_aprobado):
    trabajo = tmp_path / "trabajo"
    salidas = tmp_path / "salidas"
    datos = tmp_path / "datos"
    bitacora = tmp_path / "flujo.jsonl"
    esperado = salidas if lote_aprobado else trabajo / "enaho"
    agregado = object()
    cargar = Mock(side_effect=[agregado] if lote_aprobado else [ValueError("Parquet ausente"), agregado])
    ejecutar = Mock()
    monkeypatch.setattr(investigar, "cargar_indicadores_validados", cargar)
    monkeypatch.setattr(investigar, "ejecutar_skill", ejecutar)
    monkeypatch.setattr(investigar, "huella", lambda ruta: "huella simulada")

    assert investigar.ejecutar_enaho(bitacora, trabajo, datos, salidas, True) == (agregado, esperado)
    esperadas = ["graficando-enaho", "mapeando-enaho"]
    if not lote_aprobado:
        esperadas.insert(0, "limpiando-enaho")
    assert [llamada.args[0] for llamada in ejecutar.call_args_list] == esperadas
    assert all(llamada.kwargs["salidas"] == esperado for llamada in ejecutar.call_args_list)
    assert cargar.call_args.args == (esperado,)


def test_limpieza_real_fallida_bloquea_grafico_y_mapa(tmp_path, monkeypatch):
    monkeypatch.chdir(investigar.RAIZ)
    bitacora = tmp_path / "fallo.jsonl"
    datos = tmp_path / "datos"
    datos.mkdir()
    with pytest.raises(ValueError, match="Falló limpiando-enaho"):
        investigar.ejecutar_enaho(bitacora, tmp_path, datos, tmp_path / "vacio", True)

    eventos = [json.loads(linea) for linea in bitacora.read_text(encoding="utf-8").splitlines()]
    assert [(e["evento"], e.get("skill")) for e in eventos] == [
        ("enaho_lote", None),
        ("skill_inicio", "limpiando-enaho"),
        ("skill_fin", "limpiando-enaho"),
    ]
    assert eventos[-1]["retorno"] == 1
    assert "966-Modulo34.zip" in eventos[-1]["stderr"]
    assert "Estado: RECHAZADO" in (tmp_path / "enaho/validacion.txt").read_text(encoding="utf-8")
    assert not (tmp_path / "figuras").exists() and not (tmp_path / "mapas").exists()
