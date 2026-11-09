"""Verifica .mcp.json por stdio y contrasta resultados con consultas directas a BCRPData."""

import asyncio
import json
from math import fsum, isclose
from pathlib import Path

import httpx
from fastmcp import Client

API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"


async def verificar():
    config = json.loads(Path(".mcp.json").read_text(encoding="utf-8"))
    async with Client(config, timeout=120) as cliente, httpx.AsyncClient(timeout=30) as http:
        async def llamar(nombre, **args):
            return (await cliente.call_tool(nombre, args)).data

        async def oficial(ruta):
            url = f"{API}/{ruta}"
            for intento in range(4):
                try:
                    respuesta = await http.get(url)
                    respuesta.raise_for_status()
                    periodos = respuesta.json()["periods"]
                    break
                except (httpx.HTTPError, ValueError, KeyError):
                    if intento == 3:
                        raise
                    await asyncio.sleep(2 ** (intento + 1))
            return url, {
                fila["name"]: None if fila["values"][0] == "n.d." else float(fila["values"][0])
                for fila in periodos
            }

        herramientas = sorted(t.name for t in await cliente.list_tools())
        recursos = [str(r.uri) for r in await cliente.list_resources()]
        plantillas = [r.uri_template for r in await cliente.list_resource_templates()]
        prompts = [p.name for p in await cliente.list_prompts()]
        assert herramientas == ["buscar_series", "comparar_series", "resumen", "serie"]
        assert "bcrp://catalogo" in recursos and "bcrp://serie/{codigo}" in plantillas
        assert "informe" in prompts
        print("Herramientas:", ", ".join(herramientas))
        print("Recurso y plantilla:", ", ".join(recursos + plantillas))
        print("Prompt:", ", ".join(prompts))

        guia = (await cliente.read_resource("bcrp://catalogo"))[0].text
        ficha = json.loads((await cliente.read_resource("bcrp://serie/PN01273PM"))[0].text)
        assert ficha["codigo"] == "PN01273PM" and ficha["frecuencia"] == "Mensual"
        assert ficha["fuente"] in guia
        tema = "inflación de Lima Metropolitana"
        prompt = await cliente.get_prompt("informe", {"tema": tema})
        assert tema in prompt.messages[0].content.text
        print("Recurso, ficha PN01273PM y prompt leídos por stdio.")

        codigo = "PN01271PM"
        mensual = await llamar("serie", codigo=codigo, desde="2025-01", hasta="2025-12")
        url, datos = await oficial(f"{codigo}/json/2025-1/2025-12")
        assert mensual["fuente"] == url
        assert [fila["valor"] for fila in mensual["datos"]] == list(datos.values())
        print(f"{codigo} marzo 2025: {datos['Mar.2025']} ({url})")

        codigo = "PD04638PD"
        diaria = await llamar("serie", codigo=codigo, desde="2026-10-01", hasta="2026-10-15")
        url, datos = await oficial(f"{codigo}/json/2026-10-01/2026-10-15")
        assert diaria["fuente"] == url
        assert [fila["valor"] for fila in diaria["datos"]] == [v for v in datos.values() if v is not None]
        assert datos["08.Oct.26"] is None and "2026-10-08" in diaria["periodos_sin_dato"]
        print(f"{codigo} 15/10/2026: {datos['15.Oct.26']}; 08/10/2026: n.d. ({url})")

        codigo = "PN01273PM"
        resumen = await llamar("resumen", codigo=codigo, desde="2025-12", hasta="2026-09")
        url, datos = await oficial(f"{codigo}/json/2025-12/2026-9")
        valores = list(datos.values())
        assert resumen["fuente"] == url
        assert resumen["primero"]["valor"] == valores[0] and resumen["ultimo"]["valor"] == valores[-1]
        assert resumen["maximo"] == {"periodo": "2026-09", "valor": max(valores)}
        assert isclose(resumen["promedio"], fsum(valores) / len(valores))
        assert isclose(resumen["cambio"], valores[-1] - valores[0])
        assert isclose(resumen["variacion_pct"], 100 * (valores[-1] / valores[0] - 1))
        print(f"{codigo} diciembre 2025: {valores[0]}; septiembre 2026: {valores[-1]} ({url})")

        comparacion = await llamar(
            "comparar_series", codigo_a="PN01271PM", codigo_b=codigo, desde="2025-01", hasta="2025-12"
        )
        url, datos = await oficial(f"{codigo}/json/2025-1/2025-12")
        assert comparacion["serie_b"]["fuente"] == url
        assert comparacion["n_pares"] == len(mensual["datos"]) == len(datos) == 12
        assert comparacion["faltantes"] == {"PN01271PM": [], "PN01273PM": []}
        assert comparacion["datos"] == [
            {"periodo": dato["periodo"], "valor_a": dato["valor"], "valor_b": valor_b}
            for dato, valor_b in zip(mensual["datos"], datos.values(), strict=True)
        ]
        print(f"Comparación mensual de 2025: 12 pares verificados ({url})")

        trimestral = await llamar("serie", codigo="PN02538AQ", desde="2000-T1", hasta="2000-T2")
        url, datos = await oficial("PN02538AQ/json/2000-1/2000-2")
        assert trimestral["datos"] == [
            {"periodo": "2000-T1", "valor": datos["T1.00"]},
            {"periodo": "2000-T2", "valor": datos["T2.00"]},
        ]
        anual = await llamar("serie", codigo="PD04746FA", desde="2019", hasta="2020")
        url_anual, datos = await oficial("PD04746FA/json/2019/2020")
        assert anual["datos"] == [{"periodo": p, "valor": v} for p, v in datos.items()]
        print(f"Normalización trimestral y anual verificada ({url}, {url_anual}).")


if __name__ == "__main__":
    asyncio.run(verificar())
