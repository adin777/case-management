import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _manifest() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current = ""
    for raw in (Path(__file__).with_name("api_coverage.yml")).read_text(encoding="utf-8").splitlines():
        if raw and not raw.startswith(" ") and raw.endswith(":"):
            current = raw[:-1]
            result[current] = []
        elif raw.strip().startswith("- "):
            result[current].append(raw.strip()[2:])
    return result


def test_every_manifest_endpoint_is_documented_and_has_a_real_test() -> None:
    specification = (ROOT / "docs/api/API_SPEC.md").read_text(encoding="utf-8")
    test_source = "\n".join(
        path.read_text(encoding="utf-8")
        for base in (ROOT / "apps/api/app/tests", ROOT / "tests/api_contract")
        for path in base.glob("test_*.py")
    )
    manifest = _manifest()
    assert manifest
    for endpoint, tests in manifest.items():
        method, path = endpoint.split(" ", 1)
        normalized_path = re.sub(r"\{[^}]+\}", "{param}", path.split("?")[0])
        normalized_specification = re.sub(r"\{[^}]+\}", "{param}", specification)
        assert method in specification and normalized_path in normalized_specification, endpoint
        assert tests, endpoint
        for test_name in tests:
            assert f"def {test_name}(" in test_source, f"{endpoint}: {test_name}"
