"""End-to-end smoke test for the ChatGPT-like project navigation sidebar."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import tkinter as tk

from melody_notation.gui import Editor
from melody_notation.workspace import ProjectWorkspace, load_recent_projects

with TemporaryDirectory() as td:
    os.environ['MELODY_RECENT_PROJECTS_FILE'] = str(Path(td) / 'recent.json')
    root=tk.Tk()
    root.geometry('1520x850')
    editor=Editor(root)
    root.update()
    assert editor.nav_panel.winfo_ismapped()
    assert editor.search_hint.winfo_ismapped()
    p1=ProjectWorkspace.create(Path(td),'项目 A')
    p2=ProjectWorkspace.create(Path(td),'项目 B')
    file_a=p1.new_score('主题.jianpu',editor._blank_score_text('主题'))
    file_b=p2.new_score('片尾.jianpu',editor._blank_score_text('片尾'))
    editor.project=p1
    editor._register_project(p1.root)
    editor.project=p2
    editor._register_project(p2.root)
    editor.refresh_project_tree()
    root.update()
    assert editor._tree_item_for(file_a)
    assert editor._tree_item_for(file_b)
    assert load_recent_projects() == [p2.root,p1.root]

    # Selecting a file under another project changes the active project.
    editor._select_tree_path(file_a)
    editor._on_tree_open()
    root.update()
    assert editor.project.root == p1.root
    assert editor.path == file_a

    # Search narrows the tree without mutating the file system or editor data.
    editor.nav_search.set('片尾')
    root.update()
    assert editor._tree_item_for(file_b)
    assert not editor._tree_item_for(file_a)
    editor.nav_search.set('')
    root.update()
    assert editor._tree_item_for(file_a)
    assert editor._tree_item_for(file_b)

    # Collapsed icon rail still exposes the editor and expands again.
    editor.toggle_project_sidebar()
    root.update()
    assert editor._nav_collapsed
    assert not editor.nav_panel.winfo_ismapped()
    import pyautogui
    (Path(__file__).resolve().parents[1] / 'docs' / 'screenshots').mkdir(parents=True, exist_ok=True)
    pyautogui.screenshot().save(Path(__file__).resolve().parents[1] / 'docs' / 'screenshots' / 'sidebar-collapsed.png')
    editor.focus_project_search()
    root.update()
    assert editor.nav_panel.winfo_ismapped()

    # Final screenshot with a user-facing example project under the navigator.
    editor._select_tree_path(file_a)
    root.update()
    import pyautogui
    (Path(__file__).resolve().parents[1] / 'docs' / 'screenshots').mkdir(parents=True, exist_ok=True)
    pyautogui.screenshot().save(Path(__file__).resolve().parents[1] / 'docs' / 'screenshots' / 'chat-style-sidebar.png')
    root.destroy()
print('Chat-style sidebar GUI smoke passed')
