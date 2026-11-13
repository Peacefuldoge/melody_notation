from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import tkinter as tk
from melody_notation.gui import Editor
from melody_notation.workspace import ProjectWorkspace

root=tk.Tk()
root.geometry('1500x850')
e=Editor(root)
root.update()
assert len(e.documents)==1
assert e.active_document is e.documents[0]
with TemporaryDirectory() as td:
    project=ProjectWorkspace.create(Path(td),'曲集')
    p1=project.new_score('初见.jianpu',e._blank_score_text('初见'))
    folder=project.new_folder('第一乐章')
    p2=project.new_score('第一乐章/再会.jianpu',e._blank_score_text('再会'))
    e.project=project
    e.refresh_project_tree()
    assert len(project.list_scores())==2
    d1=e._open_disk_tab(p1)
    root.update()
    e.selected=(1,1)
    e.degree.set('3')
    e.apply_properties()
    assert e._modified
    d2=e._open_disk_tab(p2)
    root.update()
    assert e.score_model.title=='再会'
    assert not e._modified
    assert len(e.documents)==3
    # Edit a pending source draft, change tab, make sure it survives unchanged.
    e.edit.insert('end','\n# unsaved draft')
    e._on_source_edit()
    assert e.source_dirty
    e.switch_tab(d1)
    root.update()
    assert e.score_model.measures[0][0].degree==3
    assert e._modified
    assert not e.source_dirty
    e.switch_tab(d2)
    root.update()
    assert '# unsaved draft' in e.edit.get('1.0','end')
    assert e.source_dirty
    # Screenshot with the first file selected and a multi-file tree open.
    e.switch_tab(d1)
    root.update()
    root.update_idletasks()
    import pyautogui
    screenshot_dir = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    pyautogui.screenshot().save(screenshot_dir / 'workspace-preview.png')
    # A tab must switch without erasing the other tab's unapplied source.
    assert d2.source_dirty
    with patch('melody_notation.workspace_gui.messagebox.askyesnocancel',return_value=False):
        e.close_tab(d2)
    assert len(e.documents)==2
    assert d1 in e.documents
    e._modified=False
    e.active_document.modified=False
    e.active_document.undo_stack.clear()
    root.destroy()
print('GUI workspace smoke passed')
