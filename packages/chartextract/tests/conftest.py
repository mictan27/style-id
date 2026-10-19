from __future__ import annotations

import pytest
from chart_helpers import make_extraction

from styleid_schema import ChartExtraction


@pytest.fixture
def flat_tee() -> ChartExtraction:
    return make_extraction(
        [
            ("S", [("Chest (pit to pit)", 50), ("Length (HPS)", 70), ("Shoulder", 44)]),
            ("M", [("Chest (pit to pit)", 53), ("Length (HPS)", 72), ("Shoulder", 46)]),
            ("L", [("Chest (pit to pit)", 56), ("Length (HPS)", 74), ("Shoulder", 48)]),
        ]
    )
