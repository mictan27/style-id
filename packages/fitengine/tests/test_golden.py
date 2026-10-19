"""Golden cases: whole-report expectations reviewed by product. Add a JSON file to extend."""

import pytest
from conftest import golden_cases, load_body, load_garment

from styleid_fit import Zone, build_report


@pytest.mark.parametrize(
    ("name", "case"), golden_cases(), ids=lambda c: c if isinstance(c, str) else ""
)
def test_golden(name, case):
    candidates = [load_garment(c) for c in case["candidates"]]
    refs = [load_garment(r) for r in case.get("references", [])]
    body = load_body(case.get("body"))
    report = build_report(candidates, body, refs)
    exp = case["expected"]

    assert (report.pick.size_label if report.pick else None) == exp["pick"], name
    if "runner_up" in exp:
        assert (report.runner_up.size_label if report.runner_up else None) == exp["runner_up"], name
    for size_label, labels in exp.get("labels", {}).items():
        size = next(s for s in report.sizes if s.size_label == size_label)
        for zone_name, label in labels.items():
            z = size.zone(Zone(zone_name))
            assert z is not None, (name, size_label, zone_name)
            assert (z.label.value if z.label else None) == label, (name, size_label, zone_name)
    for size_label, text in exp.get("positions", {}).items():
        size = next(s for s in report.sizes if s.size_label == size_label)
        z = size.zone(Zone.LENGTH)
        assert z is not None and z.position is not None and z.position.text == text, (
            name,
            size_label,
        )
    assert sorted(s.size_label for s in report.sizes if s.excluded_reason) == sorted(
        exp.get("excluded", [])
    ), name
