from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import tkinter as tk
from melody_notation.gui import Editor
from melody_notation.workspace import ProjectWorkspace

root=tk.Tk()
app=Editor(root)
root.update()
with TemporaryDirectory() as td:
    app.project=ProjectWorkspace.create(Path(td),'demo')
    app.refresh_project_tree()
    with patch('melody_notation.workspace_gui.simpledialog.askstring',return_value='main.jianpu'):
        app.new_score()
    f=app.project.root/'main.jianpu'
    assert f.exists()
    assert app.path==f
    assert len(app.documents)==2
    assert app.project_tree.get_children()

    app.selected=(1,1)
    app.degree.set('5')
    app.apply_properties()
    assert app._modified
    assert app.save()
    assert not app._modified
    assert '5 2 3 4' in f.read_text(encoding='utf-8')

    app._select_tree_path(f)
    with patch('melody_notation.workspace_gui.simpledialog.askstring',return_value='main-renamed'):
        app.rename_project_item()
    f2=app.project.root/'main-renamed.jianpu'
    assert f2.exists() and not f.exists()
    assert app.path==f2
    assert app.active_document.path==f2

    with patch('melody_notation.workspace_gui.simpledialog.askstring',return_value='chapter'):
        app.new_subproject()
    assert (app.project.root/'chapter').is_dir()

    # Create a second score inside the new folder.
    app._select_tree_path(app.project.root/'chapter')
    with patch('melody_notation.workspace_gui.simpledialog.askstring',return_value='part2'):
        app.new_score()
    assert (app.project.root/'chapter'/'part2.jianpu').exists()
    assert len(app.project.list_scores())==2
    assert len(app.documents)==3

    # Closing a dirty tab and choosing cancel must leave all data intact.
    app.edit.insert('end','\n# unfinished change')
    app._on_source_edit()
    before=app.active_document
    with patch('melody_notation.workspace_gui.messagebox.askyesnocancel',return_value=None):
        app.close_current_tab()
    assert app.active_document is before
    assert before in app.documents
    assert app.source_dirty
    with patch('melody_notation.workspace_gui.messagebox.askyesnocancel',return_value=False):
        app.close_current_tab()
    assert before not in app.documents
    assert app.active_document is not before
root.destroy()
print('Project file GUI smoke passed')
