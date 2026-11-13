"""Capture the real help dialog in an Xvfb display for the README.

Usage: xvfb-run -a -s '-screen 0 1500x950x24' python devtools/capture_help.py
"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor

root = tk.Tk()
root.geometry('1360x850+45+45')
e = Editor(root)
root.update()
e.show_help()
e._help_dialog.window.geometry('1000x700+225+110')
root.update()
e._help_dialog.window.lift()
for _ in range(4): root.update()
screenshots = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
screenshots.mkdir(parents=True, exist_ok=True)
ImageGrab.grab().save(screenshots / 'help-tutorial-preview.png')
root.destroy()
