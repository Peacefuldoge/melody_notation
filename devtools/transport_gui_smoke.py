"""Test the in-window transport with a fake audio device; no speaker required.

Run: xvfb-run -a python -m devtools.transport_gui_smoke
"""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import time
import tkinter as tk
import numpy as np
from PIL import ImageGrab
from melody_notation.gui import Editor

class AudioDevice:
    def __init__(self):
        self.state='stopped'
        self.duration=90.0
        self.position=0.0
        self.closed=False
        self.loaded=False

    def load(self,samples,sr):
        assert samples.size>0
        self.loaded=True
    def play(self):
        assert self.loaded
        self.state='playing'
    def pause(self):
        self.state='paused'
    def stop(self):
        self.state='stopped'
        self.position=0
    def seek(self,seconds):
        self.position=max(0,min(self.duration,seconds))
    def close(self):
        self.state='stopped'
        self.closed=True

root=tk.Tk()
root.geometry('1330x820+25+25')
app=Editor(root)
root.update();app.redraw();root.update()
assert '试听' in app.play_button['text']
assert '停止' in app.stop_button['text']
assert app.playback_scale.winfo_ismapped()
dev=AudioDevice()
with patch('melody_notation.gui.create_player',return_value=dev), patch('melody_notation.gui.synthesize',return_value=np.zeros(200, dtype=np.float32)):
    app.listen()
    assert app._preview_future is not None
    for _ in range(60):
        root.update()
        if app._preview_future is None: break
        time.sleep(.025)
    assert dev.loaded and dev.state=='playing', (dev.loaded,dev.state)
    assert '暂停' in app.play_button['text']
    app.listen()
    assert dev.state=='paused' and '继续' in app.play_button['text']
    app.listen()
    assert dev.state=='playing'
    app.playback_progress.set(42.0)
    app._finish_seek()
    assert dev.position==42.0
    root.update()
    out=Path(__file__).resolve().parents[1]/'docs'/'screenshots'
    out.mkdir(exist_ok=True)
    ImageGrab.grab(bbox=(25,25,1355,845)).save(out/'workstation-internal-preview.png')
    app.stop_listen()
    assert dev.state=='stopped' and app._preview_signature
    app.listen()  # Replay without re-synthesizing
    assert dev.state=='playing'
    # A source edit must immediately stop old audio.
    app._on_source_edit()
    assert dev.closed and app._player is None
    assert '试听' in app.play_button['text']
app._set_source_text()
root.update()
app.on_close()
print('Transport GUI smoke OK: play, pause, resume, seek, stop, replay, invalidation, no external player')
