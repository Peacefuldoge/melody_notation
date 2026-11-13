"""Visual regression smoke: app menus in navigation, transport card above inspector."""
import sys, tempfile
from pathlib import Path
from PIL import ImageGrab
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from melody_notation.gui import Editor

def run():
    screenshots = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
    screenshots.mkdir(parents=True, exist_ok=True)
    root=tk.Tk()
    ed=Editor(root)
    root.update_idletasks()
    root.update()
    assert not hasattr(ed, 'file_menu_button')
    assert not hasattr(ed, 'export_button')
    assert ed.playback_border.winfo_y() < ed.left_border.winfo_y()
    assert ed.play_button.winfo_ismapped()
    assert ed.stop_button.winfo_ismapped()
    assert ed.instrument_box.winfo_ismapped()
    assert ed.speed_box.winfo_ismapped()
    assert ed.playback_scale.winfo_ismapped()
    assert ed.nav_file_button.winfo_ismapped()
    assert ed.nav_export_button.winfo_ismapped()
    assert ed.bars.get() == '3'
    assert ed.project_tree.winfo_ismapped()
    assert len(ed._build_file_actions_menu().entrycget(0,'label')) > 0
    # Open a real bundled score to verify that the project/score pipeline remains usable.
    ed.open_sample_tab('huang.jianpu')
    ed.redraw();root.update_idletasks();root.update()
    assert ed.score_model.title == '荒'
    assert len(ed.score_model.measures) == 41
    # Ensure menu actions have not inadvertently been kept on top.
    bounds=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
    ImageGrab.grab(bbox=bounds).save(screenshots / 'workbench-light.png')
    ed.toggle_theme();root.update_idletasks();root.update()
    assert ed.theme_mode=='dark'
    assert ed.inspector_canvas.cget('bg')==ed.palette['surface']
    ImageGrab.grab(bbox=bounds).save(screenshots / 'workbench-dark.png')
    ed.toggle_project_sidebar();root.update_idletasks();root.update()
    assert not ed.nav_panel.winfo_ismapped()
    assert ed.play_button.winfo_ismapped()
    ed.toggle_project_sidebar();root.update_idletasks();root.update()
    assert ed.nav_panel.winfo_ismapped()
    # Small viewport: bottom inspector controls remain accessible by scrolling.
    root.geometry('1120x700');root.update_idletasks();root.update()
    assert ed.left_border.winfo_height()>140
    ed.inspector_canvas.yview_moveto(1.0)
    root.update()
    assert ed.slur_label.get().startswith('先选择')
    bounds=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
    ImageGrab.grab(bbox=bounds).save(screenshots / 'workbench-compact.png')
    root.destroy()
    print('Tkinter sidebar/transport smoke passed')
if __name__=='__main__':run()
