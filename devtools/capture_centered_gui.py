"""One-shot graphical screenshot of the resize regression (run under Xvfb)."""
import tkinter as tk
from pathlib import Path
from PIL import ImageGrab
from melody_notation.gui import Editor

root=tk.Tk()
app=Editor(root)
app.load_sample('huang.jianpu')
root.geometry('1820x930+20+20')
root.update_idletasks()
root.update()
app.redraw()
root.update()
print('CANVAS',app.canvas.winfo_width(),app.canvas.winfo_height(), 'IMAGE',app.photo.width(),app.photo.height(),'OFFSET',app.offset)
screenshots = Path(__file__).resolve().parents[1] / 'docs' / 'screenshots'
screenshots.mkdir(parents=True, exist_ok=True)
ImageGrab.grab(bbox=(0,0,1850,980),all_screens=True).save(screenshots / 'centered-wide-window.png')
root.destroy()
