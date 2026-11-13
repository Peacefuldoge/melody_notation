"""PyInstaller entry point for the Melody Notation desktop application.

The repository's physical Python package is ``src``, while ``pyproject.toml``
installs that directory under the public package name ``melody_notation``.
Keep a frozen-only compatibility alias for legacy import/resource lookups.
"""
from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    # A directly invoked script starts with packaging/ on sys.path, not the
    # repository root (unlike ``python -m src.cli``).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src as _source_package

if getattr(sys, "frozen", False):
    # Some old code/external integrations use the distribution's public name.
    # The frozen GUI is bundled as ``src``. Keep both package names working
    # without importing or creating duplicate package objects.
    sys.modules.setdefault("melody_notation", _source_package)


def verify_package() -> int:
    """Check actual packaged imports and sample resources without opening GUI."""
    from importlib import resources
    from importlib import import_module

    names = (
        "shanfeng.jianpu",
        "huang.jianpu",
        "visual_demo.jianpu",
        "chiptune_ornaments.jianpu",
        "yueguang.jianpu",
    )
    packages = ("src", "melody_notation") if getattr(sys, "frozen", False) else ("src",)
    for package_name in packages:
        pkg = import_module(package_name)
        root = resources.files(pkg).joinpath("samples")
        for name in names:
            sample = root.joinpath(name)
            if not sample.is_file():
                raise RuntimeError(f"Missing bundled sample: {package_name}/{name}")
            if not sample.read_text(encoding="utf-8").strip():
                raise RuntimeError(f"Empty bundled sample: {package_name}/{name}")

    # Import the GUI module too, to detect missed PySide6/Qt dependencies.
    from src.qt_gui import MelodyMainWindow
    if not callable(getattr(MelodyMainWindow, "open_sample", None)):
        raise RuntimeError("Sample-opening GUI handler was not collected")

    print("Melody Notation package verification passed: GUI + 5 bundled examples")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--verify-package"]:
        raise SystemExit(verify_package())

    from src.cli import main
    sys.argv.insert(1, "gui")
    raise SystemExit(main())
