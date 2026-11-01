"""Regresiones de datos, cartografía y controles reales de Streamlit (unittest)."""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point, shape
from streamlit.testing.v1 import AppTest

import app

ROOT = Path(__file__).resolve().parent


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.geo = app.load_inputs()

    def row(self, dimension, category, year=2025):
        return app.select_rows(self.df, dimension, year).set_index("categoria_id").loc[category]

    def test_original_contract_and_checksum(self):
        app.validate_data(self.df)
        self.assertEqual(self.df.shape, (125, 28))
        self.assertEqual(hashlib.sha256((ROOT / "data/indicadores_dashboard.csv").read_bytes()).hexdigest(),
                         "f846d14025dbd6929d5e67879c632dbdbdb926f418b378c19b86ae3ab88c3803")
        self.assertEqual(set(self.df.anio), set(app.YEARS))
        self.assertFalse(self.df.duplicated(["anio", "escenario", "dimension", "categoria_id"]).any())

    def test_2025_regressions(self):
        national = self.row("nacional", "total")
        for field, expected in {"estimacion": 33.62658620018214, "ic95_inf": 32.290128181048374,
                                "ic95_sup": 34.96304421931591, "n": 29452}.items():
            self.assertAlmostEqual(national[field], expected, places=8)
        for dimension, category, expected in [
            ("riqueza", "q1", 19.23803479177793), ("riqueza", "q5", 45.48240942288355),
            ("brecha", "q5_menos_q1", 26.2443746311051),
            ("area", "urbana", 36.32228428986032), ("area", "rural", 20.9530362566484),
            ("brecha", "urbana_menos_rural", 15.3692480332125),
        ]:
            with self.subTest(dimension=dimension, category=category):
                self.assertAlmostEqual(self.row(dimension, category).estimacion, expected, places=8)
        gap = self.row("brecha", "q5_menos_q1")
        self.assertAlmostEqual(gap.ic95_inf, 22.42740120280748, places=8)
        self.assertAlmostEqual(gap.ic95_sup, 30.06134805940271, places=8)
        gap = self.row("brecha", "urbana_menos_rural")
        self.assertAlmostEqual(gap.ic95_inf, 13.32413416181454, places=8)
        self.assertAlmostEqual(gap.ic95_sup, 17.41436190461046, places=8)

    def test_2021_and_missingness(self):
        row = self.row("nacional", "total", 2021)
        self.assertAlmostEqual(row.estimacion, 35.033490445828406, places=8)
        self.assertEqual(row.n, 30971)
        self.assertEqual(row.n_faltantes_v217_anio, 2208)
        self.assertEqual(row.n_anual_15_49, 33179)

    def test_units_intervals_precision_and_counts(self):
        df = self.df
        self.assertTrue(df.publicable.eq(1).all())
        self.assertTrue((df.ic95_inf <= df.estimacion).all())
        self.assertTrue((df.estimacion <= df.ic95_sup).all())
        self.assertTrue(df.n.mod(1).eq(0).all())
        for year in app.YEARS:
            n = self.row("nacional", "total", year).n
            for dimension in ("riqueza", "educacion", "edad", "area"):
                self.assertEqual(app.select_rows(df, dimension, year).n.sum(), n)
        self.assertEqual(app.select_rows(df, "departamento", 2025).n.sum(), 29452)
        prevalence = df[~df.dimension.eq("brecha")]
        self.assertTrue(prevalence.unidad.eq("porcentaje").all())
        self.assertTrue(prevalence.cv_pct.le(15).all())
        self.assertTrue(df[df.dimension.eq("brecha")].unidad.eq("puntos_porcentuales").all())

    def test_validation_rejects_corruption(self):
        mutations = []
        duplicate = self.df.copy()
        duplicate.iloc[0] = duplicate.iloc[1]
        mutations.append(duplicate)
        bad_ci = self.df.copy()
        bad_ci.loc[0, "ic95_sup"] = -1
        mutations.append(bad_ci)
        wrong_year = self.df.copy()
        wrong_year.loc[wrong_year.dimension.eq("departamento"), "anio"] = 2024
        mutations.append(wrong_year)
        wrong_code = self.df.copy()
        wrong_code.loc[wrong_code.codigo_departamento.eq("01"), "codigo_departamento"] = "1"
        mutations.append(wrong_code)
        for index, df in enumerate(mutations):
            with self.subTest(case=index):
                with self.assertRaises(ValueError):
                    app.validate_data(df)

    def test_geography_match_validity_topology_and_fingerprint(self):
        app.validate_geo(self.df, self.geo)
        features = self.geo["features"]
        codes = [f["properties"]["CD_DEPA"] for f in features]
        self.assertEqual(codes, [f"{i:02}" for i in range(1, 26)])
        self.assertTrue(shapely.coverage_is_valid([shape(f["geometry"]) for f in features]))
        manifest = json.loads((ROOT / "data/cartografia_fuente.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256((ROOT / "data/peru_departamentos.geojson").read_bytes()).hexdigest(),
                         manifest["sha256_geojson"])
        self.assertEqual(manifest["excluidos_CD_DEPA_99"], 7)
        self.assertTrue(manifest["partes_multipoligono_conservadas"])
        geometries = {f["properties"]["CD_DEPA"]: shape(f["geometry"]) for f in features}
        # Puntos interiores conocidos: Lima Metropolitana, Huacho y Callao.
        self.assertTrue(geometries["15"].covers(Point(-77.03, -12.05)))
        self.assertTrue(geometries["15"].covers(Point(-77.61, -11.11)))
        self.assertTrue(geometries["07"].covers(Point(-77.12, -12.04)))
        self.assertFalse(geometries["15"].covers(Point(-77.12, -12.04)))
        missing = deepcopy(self.geo)
        missing["features"].pop()
        with self.assertRaises(ValueError):
            app.validate_geo(self.df, missing)

    def test_figures_use_exact_precomputed_values_and_intervals(self):
        before = self.df.copy(deep=True)
        for year in app.YEARS:
            for dimension in ("riqueza", "educacion"):
                rows = app.select_rows(self.df, dimension, year)
                trace = app.bar_chart(self.df, dimension, year).data[0]
                values = trace.x if dimension == "educacion" else trace.y
                errors = trace.error_x if dimension == "educacion" else trace.error_y
                np.testing.assert_array_equal(values, rows.estimacion)
                np.testing.assert_allclose(np.array(values) + np.array(errors.array), rows.ic95_sup)
                np.testing.assert_allclose(np.array(values) - np.array(errors.arrayminus), rows.ic95_inf)
            for dimension in app.DIMENSIONS:
                traces = app.temporal_chart(self.df, dimension, year).data
                self.assertEqual(list(traces[1].x), app.YEARS)
                np.testing.assert_array_equal(traces[1].y, app.select_rows(self.df, "nacional").estimacion)
        pd.testing.assert_frame_equal(before, self.df)

    def test_principal_never_mixes_sensitivity(self):
        for dimension in app.DIMENSIONS:
            self.assertTrue(app.select_rows(self.df, dimension).escenario.eq("principal").all())
        sensitivity = self.df.copy()
        sensitivity.loc[sensitivity.escenario.eq("sin_feb_mar"), "estimacion"] = 99
        self.assertEqual(app.temporal_chart(sensitivity, "area", 2025).to_json(),
                         app.temporal_chart(self.df, "area", 2025).to_json())

    def test_no_artificial_aggregate_calculations(self):
        tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        prohibited = {"mean", "average", "median", "agg", "aggregate", "pivot_table", "resample"}
        self.assertFalse([n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute) and n.func.attr in prohibited])
        # Un contraste deliberadamente distinto debe seguir siendo el dato de la fila.
        sentinel = self.df.copy()
        mask = sentinel.dimension.eq("brecha") & sentinel.categoria_id.eq("q5_menos_q1")
        sentinel.loc[mask, ["estimacion", "ic95_inf", "ic95_sup"]] = [7, 5, 9]
        row = app.select_rows(sentinel, "brecha", 2025).iloc[0]
        self.assertEqual(row.estimacion, 7)
        self.assertEqual(app.interval(row, "pp"), "IC95 %: 5,00–9,00 pp")

    def test_suppression_never_substitutes_zero(self):
        rows = app.select_rows(self.df, "riqueza", 2025)
        rows.loc[rows.categoria_id.eq("q1"), "publicable"] = 0
        self.assertEqual(len(app.publishable(rows)), 4)
        rows.loc[rows.categoria_id.eq("q2"), "cv_pct"] = 31
        rows.loc[rows.categoria_id.eq("q3"), "estimacion"] = np.nan
        rows.loc[rows.categoria_id.eq("q4"), "n"] = 29
        self.assertEqual(list(app.publishable(rows).categoria_id), ["q5"])


class InterfaceTests(unittest.TestCase):
    def start(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def assert_healthy(self, at):
        self.assertFalse(list(at.exception))
        self.assertFalse(list(at.error))
        self.assertEqual(len(at.get("plotly_chart")), 4)

    def specs(self, at):
        return [json.loads(chart.proto.spec) for chart in at.get("plotly_chart")]

    def test_default_kpis_and_three_controls(self):
        at = self.start()
        self.assert_healthy(at)
        self.assertEqual([m.value for m in at.metric], ["33,63 %", "29 452", "26,24 pp", "15,37 pp"])
        self.assertEqual([s.key for s in at.selectbox], ["year", "dimension", "department"])

    def test_year_updates_kpis_and_bars_map_remains_2025(self):
        at = self.start()
        df, _ = app.load_inputs()
        map_initial = self.specs(at)[3]
        for year in app.YEARS:
            at.selectbox(key="year").set_value(year).run()
            self.assert_healthy(at)
            national = app.select_rows(df, "nacional", year).iloc[0]
            self.assertEqual(at.metric[0].value, app.number(national.estimacion) + " %")
            self.assertEqual(at.metric[1].value, app.number(national.n, 0))
            gaps = app.select_rows(df, "brecha", year)
            self.assertEqual([m.value for m in at.metric[2:4]],
                             [app.number(v) + " pp" for v in gaps.estimacion])
            specs = self.specs(at)
            self.assertEqual(specs[3], map_initial)
            self.assertEqual(specs[0]["layout"]["shapes"][0]["x0"], year-0.07)
            for index, dimension in [(1, "riqueza"), (2, "educacion")]:
                axis = "y" if dimension == "riqueza" else "x"
                self.assertEqual(specs[index]["data"][0][axis],
                                 app.select_rows(df, dimension, year).estimacion.tolist())

    def test_all_temporal_dimensions(self):
        at = self.start()
        fixed = self.specs(at)[1:]
        metrics = [m.value for m in at.metric]
        expected = {"nacional": 1, "area": 3, "riqueza": 6, "educacion": 5, "edad": 6}
        for dimension in app.DIMENSIONS:
            at.selectbox(key="dimension").set_value(dimension).run()
            self.assert_healthy(at)
            specs = self.specs(at)
            self.assertEqual(len([t for t in specs[0]["data"] if t.get("showlegend", True)]), expected[dimension])
            self.assertEqual(specs[0]["data"][1]["name"], "Nacional")
            self.assertEqual(specs[1:], fixed)
            self.assertEqual([m.value for m in at.metric], metrics)

    def test_all_year_department_combinations(self):
        at = self.start()
        df, _ = app.load_inputs()
        departments = app.select_rows(df, "departamento", 2025).set_index("codigo_departamento")
        for year in app.YEARS:
            at.selectbox(key="year").set_value(year).run()
            fixed = self.specs(at)[:3]
            metrics = [m.value for m in at.metric[:4]]
            for code in ["todos"] + list(departments.index):
                with self.subTest(year=year, department=code):
                    at.selectbox(key="department").set_value(code).run()
                    self.assert_healthy(at)
                    specs = self.specs(at)
                    self.assertEqual(specs[:3], fixed)
                    self.assertEqual([m.value for m in at.metric[:4]], metrics)
                    self.assertEqual(specs[3]["data"][0]["zmin"], 0)
                    self.assertEqual(specs[3]["data"][0]["zmax"], 60)
                    self.assertEqual(len(specs[3]["data"][0]["locations"]), 25)
                    if code != "todos":
                        row = departments.loc[code]
                        self.assertEqual(at.metric[4].value, app.number(row.estimacion) + " %")
                        self.assertEqual(specs[3]["data"][1]["locations"], [code])
                        self.assertIn(f"{row.categoria} · 2025", " ".join(m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()
