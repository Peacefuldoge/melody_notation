"""v0.4.5 custom drum tracks: legacy v1, v2 round-trip, sound and timeline."""
import json
import numpy as np
import pytest

from melody_notation.drums import DrumPattern, DRUM_VOICES, default_drum_pattern, drum_midi, render_drum_pattern
from melody_notation.arrangement import Arrangement, add_clip, rendered_events, synthesize_arrangement
from melody_notation.workspace import ProjectWorkspace


def test_defaults_and_track_lifecycle(tmp_path):
    p=default_drum_pattern()
    assert [t.id for t in p.tracks]==['kick','snare','hihat']
    assert [t.name for t in p.tracks]==['底鼓 Kick','军鼓 Snare','踩镲 Hi-hat']
    added=p.add_track('snare')
    assert (added.id,added.name,added.sound)==('track_4','新建鼓点 4','snare')
    p.toggle(added.id,3)
    p.rename_track(added.id,'副歌军鼓')
    assert p.hits[added.id]==[3]
    assert p.track(added.id).name=='副歌军鼓'
    p.set_track_sound(added.id,'hihat')
    file=tmp_path/'updated.drum';p.save(file)
    raw=json.loads(file.read_text(encoding='utf-8'))
    assert raw['version']==2 and len(raw['tracks'])==4
    loaded=DrumPattern.load(file)
    assert loaded.to_dict()==p.to_dict()
    loaded.remove_track('snare')
    assert 'snare' not in loaded.hits
    assert loaded.hits[added.id]==[3]
    newer=loaded.add_track()
    assert (newer.id,newer.name)==('track_5','新建鼓点 5')
    loaded.save(file)
    assert len(DrumPattern.load(file).tracks)==4


def test_legacy_v1_drum_files_load():
    original=default_drum_pattern()
    legacy={key:original.to_dict()[key] for key in ('format','title','bpm','bars','kit','hits')}
    legacy['version']=1
    loaded=DrumPattern.from_dict(legacy)
    assert set(loaded.hits)==set(DRUM_VOICES)
    assert len(loaded.tracks)==3
    assert loaded.to_dict()['version']==2


def test_unsupported_and_bad_track_metadata():
    p=default_drum_pattern()
    with pytest.raises(ValueError):p.rename_track('kick',' ')
    with pytest.raises(ValueError):p.add_track('clap')
    with pytest.raises(ValueError):p.remove_track('missing')
    with pytest.raises(ValueError):p.set_track_sound('kick','cowbell')
    data=p.to_dict()
    data['tracks'].append({'id':'kick','name':'duplicate','sound':'kick'})
    with pytest.raises(ValueError):DrumPattern.from_dict(data)


def test_custom_tracks_contribute_to_audio_midi_and_arrangement(tmp_path):
    p=default_drum_pattern()
    # Isolate extra track so no built-in row can account for audible output.
    for key in p.hits:p.hits[key]=[]
    added=p.add_track(sound='snare')
    p.toggle(added.id,0)
    audio=render_drum_pattern(p)
    assert np.max(np.abs(audio))>0.001
    notes=[n for inst in drum_midi(p).instruments for n in inst.notes]
    assert len(notes)==1 and notes[0].pitch==38
    pr=ProjectWorkspace.create(tmp_path,'Music')
    drum=pr.root/'drums.drum';p.save(drum)
    path=pr.root/'music.mtrack'
    arr=Arrangement(bpm=120)
    add_clip(arr,path,drum)
    events=rendered_events(arr,path)
    assert len(events)==1 and events[0][3]==38 and events[0][5]=='snare'
    mixed=synthesize_arrangement(arr,path)
    assert np.max(np.abs(mixed))>0.001


def test_empty_track_set_and_deleted_rows_do_not_crash():
    p=default_drum_pattern()
    for track_id in list(p.hits):p.remove_track(track_id)
    assert p.tracks==[] and p.hits=={}
    assert not np.any(render_drum_pattern(p))
    assert not [note for inst in drum_midi(p).instruments for note in inst.notes]
    new=p.add_track()
    assert new.name=='新建鼓点 4'


def test_limit_is_64():
    p=DrumPattern()
    for _ in range(61):p.add_track()
    assert len(p.tracks)==64
    with pytest.raises(ValueError):p.add_track()
