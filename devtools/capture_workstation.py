"""Real GUI screenshots under Xvfb, used to inspect spacing and states."""
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor

out=Path(__file__).resolve().parents[1]/'docs'/'screenshots'
out.mkdir(exist_ok=True)
root=tk.Tk()
root.geometry('1330x820+25+25')
app=Editor(root)
root.update();app.redraw();root.update()
ImageGrab.grab(bbox=(25,25,1355,845)).save(out/'workstation-light.png')
app.toggle_source();root.update();app.redraw();root.update()
ImageGrab.grab(bbox=(25,25,1355,845)).save(out/'workstation-source.png')
app.toggle_theme();root.update();app.redraw();root.update()
ImageGrab.grab(bbox=(25,25,1355,845)).save(out/'workstation-dark.png')
root.destroy()
