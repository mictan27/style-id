"""Write JSON Schema for every public model to packages/schema/json/. CI diffs the output."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

import styleid_schema as s

OUT = Path(__file__).resolve().parents[1] / "json"

MODELS: list[type[BaseModel]] = [
    s.MeasurementModel,
    s.GarmentModel,
    s.LandmarksModel,
    s.BodyModel,
    s.ChartExtraction,
    s.NormalisedChart,
    s.FitReportModel,
    s.PreferencesModel,
    s.OutcomeModel,
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for model in MODELS:
        path = OUT / f"{model.__name__}.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        print(path.relative_to(OUT.parents[2]))


if __name__ == "__main__":
    main()
