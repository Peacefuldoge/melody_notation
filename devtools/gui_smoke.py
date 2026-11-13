"""Optional GUI integration smoke test (Linux: xvfb-run -a python devtools/gui_smoke.py)."""
import tkinter as tk
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from melody_notation.gui import Editor

root=tk.Tk()
e=Editor(root)
root.update_idletasks();root.update();e.redraw()
# Verify mouse hit testing instead of directly assigning selection.
bi,ni,(x0,y0,x1,y1)=e.hits[0]
x=round((x0+x1)/2*e.scale+e.offset[0])
y=round((y0+y1)/2*e.scale+e.offset[1])
e.canvas.event_generate('<Button-1>',x=x,y=y)
root.update()
assert e.selected==(bi,ni),('click hit test failed',e.selected,bi,ni)
e.degree.set('5');e.apply_properties()
assert e.score_model.measures[0][0].degree==5
assert e.score_model.validate()==[]
# source serialization round-trips after graphical changes
from melody_notation.core import parse_text
assert parse_text(e.edit.get('1.0','end')).to_dict()==e.score_model.to_dict()
e.undo(); assert e.score_model.measures[0][0].degree==1
e.redo(); assert e.score_model.measures[0][0].degree==5
root.destroy()
print('GUI smoke OK: real mouse hit testing, edit, source sync, undo, redo')
