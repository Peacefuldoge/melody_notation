"""Tkinter layout/interaction regression for Route A.
Run: xvfb-run -a python -m devtools.route_a_gui_smoke
"""
from copy import deepcopy
import tkinter as tk
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from melody_notation.gui import Editor

root=tk.Tk()
app=Editor(root)
root.update();app.redraw();root.update()
original=deepcopy(app.score_model.to_dict())
assert app.source_visible is False
assert '导出' in app.export_button['text']
assert [app.menus[1].entrycget(i,'label') for i in range(4)] == [
    'MIDI 音符文件', 'WAV 音频', 'MP3 音频', 'PNG 乐谱图片'
]
assert app.file_menu_button['text'].startswith('文件')
app.toggle_source(); root.update()
assert app.source_visible is True
assert app.edit.winfo_ismapped()
assert app.edit.winfo_height() >= 60, app.edit.winfo_height()
app.edit.insert('end',' ')
app._on_source_edit()  # simulate the bound KeyRelease handler
assert app.source_dirty is True
app.toggle_theme();root.update()
assert app.theme_mode == 'dark' and app.score_model.to_dict() == original
assert app.source_dirty is True
# restore draft without overwriting score model
app._set_source_text()
app.toggle_source();root.update()
assert app.source_visible is False
app.toggle_theme();root.update()
assert app.theme_mode == 'light' and app.score_model.to_dict() == original
with TemporaryDirectory() as td:
    p=Path(td)
    with patch('melody_notation.gui.messagebox.showinfo'):
     with patch('melody_notation.gui.filedialog.asksaveasfilename',return_value=str(p/'score.mid')):
      app.export('.mid')
     with patch('melody_notation.gui.filedialog.asksaveasfilename',return_value=str(p/'score.png')):
      app.export('.png')
    assert (p/'score.mid').stat().st_size > 0
    assert (p/'score.png').stat().st_size > 1000
# check small window never clips source apply button
root.geometry('970x720+10+10');app.toggle_source();root.update()
assert app.source_visible and app.edit.winfo_ismapped()
root.destroy()
print('Route A smoke OK: menus, drawer, theme/draft preservation, MIDI+PNG, small window')
