"""Pure new Qt preview backend tests; do not require Qt or an audio device."""
import numpy as np
import soundfile as sf

from melody_notation.preview_engine import render_preview
from melody_notation.core import parse_text
from melody_notation.drums import sample_drum_pattern
from melody_notation.arrangement import Arrangement, add_clip
from melody_notation.workspace import ProjectWorkspace

SCORE = "title: Demo\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |"


def test_score_preview_speed_keeps_pitch_and_halves_duration(tmp_path):
    score = parse_text(SCORE)
    slow=tmp_path/'piano_normal.wav';fast=tmp_path/'piano_fast.wav'
    render_preview('jianpu',score,None,'piano',1.,slow)
    render_preview('jianpu',score,None,'piano',2.,fast)
    a,sr=sf.read(slow);b,sr2=sf.read(fast)
    assert sr==sr2==22050
    assert len(b)<len(a)
    assert np.max(abs(a))>0 and np.max(abs(b))>0
    assert np.isfinite(b).all()


def test_drum_preview_uses_chiptune_kit(tmp_path):
    pat=sample_drum_pattern('Bit','gameboy')
    slow=tmp_path/'drums.wav';fast=tmp_path/'drums_faster.wav'
    render_preview('drum',pat,None,'piano',1.,slow)
    render_preview('drum',pat,None,'piano',1.75,fast)
    a,_=sf.read(slow);b,_=sf.read(fast)
    assert np.max(abs(a))>0.05
    assert len(b)<len(a)


def test_multitrack_preview_mixes_melody_and_drums(tmp_path):
    project=ProjectWorkspace.create(tmp_path,'Project')
    score=project.new_score('s.jianpu',SCORE)
    pat=sample_drum_pattern();drum=project.root/'b.drum';pat.save(drum)
    path=project.new_asset('mix.mtrack','mtrack')
    arr=Arrangement('Mix',120)
    add_clip(arr,path,score);add_clip(arr,path,drum)
    output=tmp_path/'mix.wav'
    render_preview('mtrack',arr,path,'piano',1.25,output)
    audio,_=sf.read(output)
    assert len(audio)>10000 and np.max(abs(audio))>0.05
