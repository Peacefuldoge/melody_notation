"""Visual and interaction smoke test: xvfb-run -a python -m devtools.ornament_gui_smoke"""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import numpy as np
import time
import tkinter as tk
from PIL import ImageGrab
from melody_notation.gui import Editor
from melody_notation.core import parse_text

class FakeSound:
    def __init__(self):
        self.duration=10.0
        self.position=0.0
        self.state='stopped'
        self.loaded=False
        self.closed=False
    def load(self,samples,sr):
        self.loaded=True
        self.duration=len(samples)/sr
        self.position=0.0
    def play(self):
        assert self.loaded
        self.state='playing'
    def pause(self):self.state='paused'
    def stop(self):self.state='stopped';self.position=0
    def seek(self,v):self.position=float(v)
    def close(self):self.closed=True;self.state='stopped'

root=tk.Tk();root.geometry('1330x820+25+25');app=Editor(root)
root.update();app.redraw();root.update()
assert 'gameboy' in app.instrument_box['values']
assert list(app.speed_box['values'])==['1.00×','1.25×','1.50×','1.75×','2.00×']
app.selected=(1,1);app._show_selection()
app.ornament.set('颤音 Trill');app.apply_properties()
assert app.score_model.measures[0][0].ornament=='tr'
assert '{tr}' in app.edit.get('1.0','end')
assert not app.score_model.validate()
app.instrument.set('gameboy');app._invalidate_preview()
app.speed_label.set('1.25×')
players=[]
def create_fake():
    p=FakeSound();players.append(p);return p

with patch('melody_notation.gui.create_player', side_effect=create_fake), patch('melody_notation.gui.synthesize', side_effect=lambda s,i,sr,rate: np.zeros(round(sr*4/rate),dtype=np.float32)) as synth:
    app.listen()
    for _ in range(60):
        root.update()
        if app._preview_future is None:break
        time.sleep(.02)
    assert app._player.state=='playing'
    assert '无需打开外部播放器' not in app.status.get()
    assert synth.call_args.args[-1]==1.25
    app._player.position=1
    original_frac=app._player.position/app._player.duration
    app.speed_label.set('1.75×');app._on_speed_changed()
    for _ in range(60):
        root.update()
        if app._preview_future is None:break
        time.sleep(.02)
    assert app._player.state=='playing'
    assert synth.call_args.args[-1]==1.75
    assert app._player.position/app._player.duration==original_frac
    assert len(players)==2 and players[0].closed
    out=Path(__file__).resolve().parents[1]/'docs'/'screenshots'
    out.mkdir(exist_ok=True)
    root.update()
    ImageGrab.grab(bbox=(25,25,1355,845)).save(out/'ornament-gameboy-editor.png')
    app.stop_listen()
root.update()
app.on_close()
print('v0.2.4 GUI smoke passed: ornament, 8-bit, live speed change, playhead, UI')
