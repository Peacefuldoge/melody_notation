"""Release layout guardrails: keep user exports out of the Git tree."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_src_layout():
    from melody_notation import __version__
    assert __version__ == "0.5.10"
    assert (ROOT / "src" / "mcp_server.py").is_file()


def test_gitignore_keeps_output_folder_only():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/output/*" in gitignore
    assert "!/output/.gitkeep" in gitignore
    assert (ROOT / "output" / ".gitkeep").is_file()


def test_gui_screenshots_separate_from_user_exports():
    assert (ROOT / "docs" / "screenshots" / "workbench-light.png").is_file()
    scripts = [p.read_text(encoding="utf-8") for p in (ROOT / "devtools").glob("*.py")]
    assert any("'docs' / 'screenshots'" in s or "'docs'/'screenshots'" in s for s in scripts)
