"""Regression for v0.4.5 bug: custom IDs were treated as drum voice names."""
from pathlib import Path

import numpy as np
import soundfile as sf
import pytest

from melody_notation.drums import DrumPattern, default_drum_pattern
from melody_notation.preview_engine import render_preview


def _preview(pattern, target: Path, speed=1.0):
    render_preview('drum', pattern, None, 'piano', speed, target)
    audio, sr = sf.read(target)
    assert sr == 22050
    assert np.isfinite(audio).all()
    return audio


@pytest.mark.parametrize('sound', ['kick', 'snare', 'hihat'])
def test_custom_named_track_uses_sound_instead_of_id(tmp_path, sound):
    pattern = default_drum_pattern('Custom', 'gameboy')
    for track_id in pattern.hits:
        pattern.hits[track_id].clear()
    track = pattern.add_track(sound)
    pattern.rename_track(track.id, '卡卡 · 任意自定义名称')
    pattern.toggle(track.id, 0)
    pattern.toggle(track.id, 5)
    saved = tmp_path / 'custom.drum'
    pattern.save(saved)
    loaded = DrumPattern.load(saved)
    assert loaded.tracks[-1].id == 'track_4'
    assert loaded.tracks[-1].name == '卡卡 · 任意自定义名称'
    assert loaded.tracks[-1].sound == sound
    audio = _preview(loaded, tmp_path / f'{sound}.wav')
    assert np.max(np.abs(audio)) > 0.02


def test_changing_voice_deleting_defaults_and_speed(tmp_path):
    pattern = default_drum_pattern()
    new = pattern.add_track()
    pattern.set_track_sound(new.id, 'snare')
    pattern.toggle(new.id, 6)
    for old_id in ('kick', 'snare', 'hihat'):
        pattern.remove_track(old_id)
    pattern.rename_track(new.id, '我的唯一鼓轨')
    target = tmp_path / 'single.drum'
    pattern.save(target)
    loaded = DrumPattern.load(target)
    normal = _preview(loaded, tmp_path / 'normal.wav', 1.0)
    fast = _preview(loaded, tmp_path / 'fast.wav', 1.5)
    assert np.max(np.abs(normal)) > 0.01
    assert np.max(np.abs(fast)) > 0.01
    assert len(fast) < len(normal)


def test_empty_custom_track_and_legacy_pattern_remain_playable(tmp_path):
    pattern = default_drum_pattern()
    untouched = _preview(pattern, tmp_path / 'original.wav')
    pattern.add_track('snare')  # empty custom track must not crash or alter sound
    extended = _preview(pattern, tmp_path / 'extended.wav')
    assert np.array_equal(untouched, extended)
    for track in list(pattern.tracks):
        pattern.remove_track(track.id)
    silence = _preview(pattern, tmp_path / 'silence.wav')
    assert np.max(np.abs(silence)) == 0
