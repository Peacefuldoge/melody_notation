from pathlib import Path
import json
import numpy as np
import pytest

from melody_notation.workspace import ProjectWorkspace
from melody_notation.drums import DrumPattern, default_drum_pattern, sample_drum_pattern, drum_midi, render_drum_pattern, DRUM_VOICES
from melody_notation.arrangement import (Arrangement, add_clip, rendered_events,
    make_arrangement_midi, export_arrangement_audio, synthesize_arrangement,
    resolve_source, Track, Clip)

SCORE = 'title: Tiny\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |'


def setup_project(tmp_path):
    pr=ProjectWorkspace.create(tmp_path,'Project')
    score=pr.new_score('song.jianpu',SCORE)
    drum=sample_drum_pattern()
    drum.save(pr.root/'beat.drum')
    return pr,score,pr.root/'beat.drum'


def test_drum_edit_roundtrip(tmp_path):
    p=sample_drum_pattern('Test','gameboy')
    assert set(p.hits)==set(DRUM_VOICES)
    p.toggle('kick',0)
    assert 0 not in p.hits['kick']
    p.toggle('kick',0)
    p.resize_bars(1)
    assert p.steps == 16
    assert not any(i>=16 for v in p.hits.values() for i in v)
    file=tmp_path/'test.drum';p.save(file)
    assert DrumPattern.load(file).to_dict()==p.to_dict()
    assert {note.pitch for note in drum_midi(p).instruments[0].notes} == {36,38,42}
    assert drum_midi(p).instruments[0].is_drum
    audio=render_drum_pattern(p)
    assert len(audio)>1000 and np.max(abs(audio))>0


def test_invalid_drum_rejected():
    p=default_drum_pattern();p.hits['snare']=[500]
    with pytest.raises(ValueError):p.validate()
    with pytest.raises(ValueError):DrumPattern.from_dict({'format':'wrong','version':1})


def test_arrangement_tracks_clip_reverse_trim_and_export(tmp_path):
    pr,score,drum=setup_project(tmp_path)
    path=pr.root/'song.mtrack';a=Arrangement('Session',120)
    mel=add_clip(a,path,score)
    drums=add_clip(a,path,drum)
    assert [t.kind for t in a.tracks] == ['melody','drum']
    a.tracks[0].clips[0].trim_start=1
    a.tracks[0].clips[0].trim_end=3
    a.tracks[0].clips[0].reversed=True
    events=rendered_events(a,path)
    # original pitches D4 / E4; reversed => E4 then D4
    mel_ev=[x for x in events if x[0]==mel]
    assert [ev[3] for ev in mel_ev]==[64,62]
    assert [round(ev[1],2) for ev in mel_ev]==[.07,1.07]  # preserves short note-off gaps
    assert {ev[5] for ev in events if ev[0]==drums} == set(DRUM_VOICES)
    a.move_track(0,1)
    assert a.tracks[0].kind=='drum'
    a.save(path)
    loaded=Arrangement.load(path)
    assert loaded.to_dict()==a.to_dict()
    midi=make_arrangement_midi(loaded,path)
    assert len(midi.instruments)==2 and midi.instruments[0].is_drum
    audio=synthesize_arrangement(loaded,path)
    assert audio.ndim==1 and np.max(abs(audio))>0
    wav=export_arrangement_audio(loaded,path,tmp_path/'arrangement.wav')
    assert wav.exists() and wav.stat().st_size>1000


def test_arrangement_source_protection(tmp_path):
    pr,score,drum=setup_project(tmp_path)
    path=pr.root/'session.mtrack'
    outside=tmp_path/'outside.jianpu';outside.write_text(SCORE,encoding='utf-8')
    a=Arrangement()
    with pytest.raises(ValueError):add_clip(a,path,outside)
    with pytest.raises(ValueError):resolve_source(path,'../outside.jianpu')
    with pytest.raises(ValueError):resolve_source(path,'missing.jianpu')


def test_arrangement_mute_solo_and_multi_clip(tmp_path):
    pr,score,drum=setup_project(tmp_path)
    path=pr.root/'session.mtrack'
    arr=Arrangement('Test',96)
    i=add_clip(arr,path,score,start_beat=4)
    add_clip(arr,path,score,track_index=i,start_beat=8)
    j=add_clip(arr,path,drum)
    assert len([e for e in rendered_events(arr,path) if e[0]==i])==8
    arr.tracks[j].solo=True
    assert all(ev[0]==j for ev in rendered_events(arr,path))
    arr.tracks[j].muted=True
    assert rendered_events(arr,path)==[]
    arr.tracks[j].muted=False;arr.tracks[j].solo=False
    arr.tracks[i].clips[0].trim_end=5.0
    with pytest.raises(ValueError):rendered_events(arr,path)


def test_arrangement_json_validation():
    with pytest.raises(ValueError):Arrangement.from_dict({'format':'x','version':1})
    a=Arrangement();a.tracks=[Track('D','drum',clips=[Clip('oops.jianpu')])]
    with pytest.raises(ValueError):a.validate()


def test_rename_updates_arrangement_clip_references(tmp_path):
    pr,score,drum=setup_project(tmp_path)
    path=pr.root/'mix.mtrack';arr=Arrangement('Demo')
    add_clip(arr,path,score)
    add_clip(arr,path,drum)
    arr.save(path)
    pr.rename('song.jianpu','new_song')
    arr2=Arrangement.load(path)
    assert arr2.tracks[0].clips[0].source=='new_song.jianpu'
    assert len(rendered_events(arr2,path))>0
    sub=pr.new_folder('beats')
    (sub/'beat.drum').write_bytes(drum.read_bytes())
    arr2.tracks[1].clips[0].source='beats/beat.drum';arr2.save(path)
    pr.rename('beats','new_beats')
    arr3=Arrangement.load(path)
    assert arr3.tracks[1].clips[0].source=='new_beats/beat.drum'
    assert len(rendered_events(arr3,path))>0


def test_unicode_track_names_export(tmp_path):
    pr,score,drum=setup_project(tmp_path)
    path=pr.root/'中文编排.mtrack';a=Arrangement('标题')
    n=add_clip(a,path,score);a.tracks[n].name='弦乐旋律'
    n=add_clip(a,path,drum);a.tracks[n].name='节奏鼓点'
    a.save(path)
    from melody_notation.arrangement import export_arrangement_midi
    from melody_notation.drums import export_drum_midi
    midi=export_arrangement_midi(a,path,tmp_path/'unicode.mid')
    assert midi.stat().st_size>100
    other=export_drum_midi(DrumPattern.load(drum),tmp_path/'中文鼓点.mid')
    assert other.stat().st_size>100
