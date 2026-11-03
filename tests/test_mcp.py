import asyncio
import importlib.util
from pathlib import Path

import pytest

from recall_lab.mcp_server import create_server


def test_stdio_protocol_boundaries():
    path = Path(__file__).resolve().parents[1] / "experiments/mcp_smoke.py"
    spec = importlib.util.spec_from_file_location("mcp_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = asyncio.run(module.evaluate())
    assert all(result["checks"].values()), result


def test_empty_project_rejected(tmp_path):
    with pytest.raises(ValueError, match="project"):
        create_server(tmp_path / "memory.db", " ")
