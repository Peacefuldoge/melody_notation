"""Distribution metadata for v0.5.0 user-facing setup."""
from pathlib import Path
import tomllib

def test_gui_extra_includes_live_midi_dependencies():
    cfg=tomllib.loads((Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text(encoding='utf-8'))
    assert cfg['project']['version']=='0.5.10'
    gui=cfg['project']['optional-dependencies']['gui']
    for name in ('PySide6','mido','python-rtmidi','sounddevice'):
        assert any(x.startswith(name) for x in gui)
    assert cfg['project']['optional-dependencies']['mcp']==['mcp>=2,<3']
