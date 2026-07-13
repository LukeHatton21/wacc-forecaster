import sys
from pathlib import Path
from unittest import TestCase

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wacc_prediction_v2 import WaccPredictor


class DummyCalculator:
    def calculate_wacc_individual(
        self,
        rf_rate,
        crp,
        cds,
        tax_rate,
        technology,
        year,
        erp,
        tech_penetration,
        country_code,
    ):
        if not isinstance(technology, str):
            raise TypeError("technology must be a single string")
        return pd.DataFrame(
            {
                "Country code": [country_code],
                "WACC": [1.0],
                "Technology": [technology],
                "Year": [year],
            }
        )


class TestWaccPredictorMultiTechnology(TestCase):
    def make_predictor(self):
        predictor = WaccPredictor.__new__(WaccPredictor)
        predictor.recent_year = 2023
        predictor.ir_data = pd.DataFrame(
            [{"Country code": "USA", "2020": 2.0, "2021": 2.1, "2022": 2.2, "2023": 2.3}]
        )
        predictor.crp_data = pd.DataFrame([{"Country": "United States", "Country code": "USA"}])
        predictor.tax_data = pd.DataFrame(
            [{"Country code": "USA", "2020": 0.25, "2021": 0.25, "2022": 0.25, "2023": 0.25}]
        )
        predictor.tech_mappings = {"Solar PV": "Solar PV", "Wind": "Wind"}
        predictor.calculator = DummyCalculator()
        predictor.pull_CRP_data = lambda year: pd.DataFrame(
            {"Country code": ["ERP", "USA"], f"CRP_{year}": [0.10, 0.20]}
        )
        predictor.pull_CDS_data = lambda year: pd.DataFrame(
            {"Country code": ["ERP", "USA"], f"CDS_{year}": [0.01, 0.02]}
        )
        predictor.pull_generation_data_v2 = lambda year_str, technology: pd.DataFrame(
            {"Country code": ["USA"], f"Penetration_{year_str}": [0.1]}
        )
        return predictor

    def test_year_range_wacc_supports_multiple_technologies(self):
        predictor = self.make_predictor()

        results = predictor.year_range_wacc(2020, 2021, ["Solar PV", "Wind"], "USA")

        self.assertEqual(len(results), 4)
        self.assertEqual(set(results["Technology"]), {"Solar PV", "Wind"})
        self.assertEqual(set(results["Year"]), {2020, 2021})
