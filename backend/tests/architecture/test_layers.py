"""AD-001: domain and application layers stay pure Python."""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
PURE_LAYERS = ("domain", "application")
FORBIDDEN = ("fastapi", "sqlalchemy", "httpx", "app.infrastructure", "app.presentation")


def _module_name(path: Path, root: Path) -> str:
    parts = list(path.relative_to(root.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_statements(path: Path, root: Path) -> list[tuple[int, list[str]]]:
    """Return (line, candidate module names) for each import statement."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module = _module_name(path, root)
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    found: list[tuple[int, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.append((node.lineno, [alias.name for alias in node.names]))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            names = [target] + [f"{target}.{alias.name}" for alias in node.names]
            found.append((node.lineno, names))
    return found


def forbidden_imports(layer_dir: Path, root: Path) -> list[str]:
    violations = []
    for path in sorted(layer_dir.rglob("*.py")):
        for lineno, names in _import_statements(path, root):
            bad = [n for n in names if any(n == f or n.startswith(f + ".") for f in FORBIDDEN)]
            if bad:
                violations.append(f"{path.relative_to(root.parent)}:{lineno}: {bad[0]}")
    return violations


@pytest.mark.parametrize("layer", PURE_LAYERS)
def test_pure_layer_has_no_forbidden_imports(layer):
    layer_dir = APP_DIR / layer
    assert layer_dir.is_dir()
    assert forbidden_imports(layer_dir, APP_DIR) == []


@pytest.mark.parametrize(
    "source",
    [
        "import fastapi\n",
        "from sqlalchemy.orm import Session\n",
        "import httpx\n",
        "from app.infrastructure.database import models\n",
        "from ..infrastructure import database\n",
        "from app.presentation import api\n",
    ],
)
def test_checker_detects_forbidden_import(tmp_path, source):
    root = tmp_path / "app"
    layer = root / "domain"
    layer.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (layer / "__init__.py").write_text("")
    (layer / "bad.py").write_text(source)

    violations = forbidden_imports(layer, root)

    assert len(violations) == 1
    assert violations[0].startswith("app/domain/bad.py")


def test_checker_allows_stdlib_and_domain_imports(tmp_path):
    root = tmp_path / "app"
    layer = root / "application"
    layer.mkdir(parents=True)
    (layer / "ok.py").write_text(
        "from datetime import date\nfrom app.domain import entities\nfrom ..domain import rules\n"
    )

    assert forbidden_imports(layer, root) == []
