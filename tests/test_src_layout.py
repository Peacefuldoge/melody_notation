"""Regression checks for the on-disk v0.5.0 src/ layout."""
from pathlib import Path
import importlib
import melody_notation

ROOT = Path(__file__).resolve().parents[1]

def test_public_import_points_to_src():
    assert melody_notation.__version__ == "0.5.10"
    assert Path(melody_notation.__file__).resolve() == (ROOT / "src" / "__init__.py").resolve()
    assert not (ROOT / "melody_notation").exists()

def test_commands_and_resources_remain_importable():
    for mod in ("cli", "audio", "qt_gui", "mcp_server", "harmony"):
        if mod in ("qt_gui", "mcp_server"):
            # import is kept lazy: Qt/MCP are optional extras
            continue
        module = importlib.import_module(f"melody_notation.{mod}")
        assert module is not None
    assert (ROOT / "src" / "harmony" / "chords.json").is_file()
    assert list((ROOT / "src" / "samples").glob("*.jianpu"))
