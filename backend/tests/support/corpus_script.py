"""Loads `scripts/process_corpus.py` as a module so tests can reach its functions (ACC-01)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "process_corpus.py"
_NAME = "process_corpus_script"


def load() -> ModuleType:
    if _NAME in sys.modules:
        return sys.modules[_NAME]
    spec = importlib.util.spec_from_file_location(_NAME, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[_NAME] = module  # dataclasses resolve their annotations through sys.modules
    spec.loader.exec_module(module)
    return module
