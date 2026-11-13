"""Real Tk smoke test and visual screenshots under Xvfb."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor
from melody_notation.workspace import ProjectWorkspace
from melody_notation.arrangement import Arrangement,add_clip
from melody_notation.drums import default_drum_pattern,DrumPattern

output=Path(__file__).resolve().parents[1]/'docs'/'screenshots'
output.mkdir(exist_ok=True)
with TemporaryDirectory() as d:
    os.environ['MELODY_RECENT_PROJECTS_FILE']=str(Path(d)/'recents.json')
    root=tk.Tk();root.geometry('1550x890+20+20')
    print('AT: app=Editor(root)',flush=True)
    app=Editor(root)
    pr=ProjectWorkspace.create(Path(d),'测试多轨项目')
    app.project=pr;app._register_project(pr.root)
    song=pr.new_score('主旋律.jianpu','title: Main\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 | 5 6 7 1\' |')
    drum=pr.new_asset('节奏.drum','drum')
    track=pr.new_asset('总编排.mtrack','mtrack')
    arr=Arrangement.load(track)
    add_clip(arr,track,song)
    add_clip(arr,track,drum)
    arr.tracks[1].clips[0].start_beat=4
    arr.save(track)
    print('AT: app.refresh_project_tree()',flush=True)
    app.refresh_project_tree()
    assert len(pr.list_assets())==3
    print('AT: app._open_asset_editor(track)',flush=True)
    app._open_asset_editor(track)
    print('AT: root.update()',flush=True)
    root.update()
    ed=app._asset_editors[track]
    assert len(ed.arr.tracks)==2
    print('AT: ed._select_clip(0,0)',flush=True)
    ed._select_clip(0,0)
    ed.trim_a_var.set('1')
    ed.trim_b_var.set('4')
    ed.reverse_var.set(True)
    print('AT: ed.apply_clip()',flush=True)
    ed.apply_clip()
    assert ed.arr.tracks[0].clips[0].reversed
    print('AT: ed.save()',flush=True)
    assert ed.save()
    assert Arrangement.load(track).tracks[0].clips[0].trim_start==1
    # Capture timeline editor with full tracks visible.
    ed.window.geometry('1280x760+80+60')
    ed.window.lift();root.update()
    bx=ed.window.winfo_rootx();by=ed.window.winfo_rooty()
    ImageGrab.grab(bbox=(bx,by,bx+ed.window.winfo_width(),by+ed.window.winfo_height())).save(output/'multitrack-editor.png')
    print('AT: ed.close();root.update()',flush=True)
    ed.close();root.update()
    print('AT: app._open_asset_editor(drum)',flush=True)
    app._open_asset_editor(drum)
    ed2=app._asset_editors[drum]
    root.update()
    before=DrumPattern.load(drum).hits['kick'][:]
    from unittest.mock import Mock
    print('AT: ed2._on_click',flush=True)
    ed2._on_click(Mock(x=ed2.LEFT+1,y=ed2.TOP+10))
    assert ed2.pattern.hits['kick']!=before
    print('AT: ed2.save()',flush=True)
    assert ed2.save()
    ed2.window.geometry('1200x680+100+90')
    ed2.window.lift();root.update()
    bx=ed2.window.winfo_rootx();by=ed2.window.winfo_rooty()
    ImageGrab.grab(bbox=(bx,by,bx+ed2.window.winfo_width(),by+ed2.window.winfo_height())).save(output/'drum-step-editor.png')
    ed2.close()
    print('AT: app.toggle_theme()',flush=True)
    app.toggle_theme()
    root.update()
    app._open_asset_editor(track)
    ed3=app._asset_editors[track]
    ed3.window.geometry('1280x760+80+60')
    ed3.window.lift();root.update()
    bx=ed3.window.winfo_rootx();by=ed3.window.winfo_rooty()
    ImageGrab.grab(bbox=(bx,by,bx+ed3.window.winfo_width(),by+ed3.window.winfo_height())).save(output/'multitrack-editor-dark.png')
    ed3.close()
    root.destroy()
print('GUI multitrack/drum smoke and screenshots passed')
