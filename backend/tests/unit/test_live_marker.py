"""ACC-04: the live MariTalk contract test is opt-in and outside the default suite."""

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _pytest_options() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]


def test_maritalk_live_marker_is_registered():
    markers = _pytest_options()["markers"]

    assert any(marker.startswith("maritalk_live:") for marker in markers)


def test_default_run_excludes_the_maritalk_live_marker():
    assert "-m 'not maritalk_live'" in _pytest_options()["addopts"]
