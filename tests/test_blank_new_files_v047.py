"""v0.4.7 new documents must be genuinely empty without damaging saved examples."""
import json

import numpy as np
import pytest

from melody_notation.core import blank_score_text, parse_text, text_from_score
from melody_notation.drums import DrumPattern, default_drum_pattern, sample_drum_pattern, drum_midi, render_drum_pattern
from melody_notation.editing import insert_note, delete_note
from melody_notation.png import render_score
from melody_notation.workspace import ProjectWorkspace


def test_new_score_one_blank_bar_without_notes_or_rests(tmp_path):
    project = ProjectWorkspace.create(tmp_path, 'Music')
    path = project.new_score('空白.jianpu', blank_score_text('空白'))
    score = parse_text(path.read_text(encoding='utf-8'))
    assert score.title == '空白'
    assert score.measures == [[]]
    assert score.validate(strict=True) == []
    assert parse_text(text_from_score(score)).to_dict() == score.to_dict()
    image, hitboxes = render_score(score)
    assert image.width >= 800 and hitboxes == []
    # Editable immediately after creation; the first note is not prefilled.
    edited = insert_note(score, 1, 1)
    assert edited.measures[0][0].degree == 1
    assert sum(len(m) for m in edited.measures) == 1
    assert delete_note(edited, 1, 1).measures == [[]]


def test_blank_score_not_a_hidden_rest():
    blank = parse_text(blank_score_text('无音符'))
    assert not [note for measure in blank.measures for note in measure]
    assert not blank.validate(strict=True)
    assert not list(__import__('melody_notation.core', fromlist=['timeline']).timeline(blank))


def test_new_drum_keeps_three_empty_tracks_and_roundtrips(tmp_path):
    project = ProjectWorkspace.create(tmp_path, 'Session')
    path = project.new_asset('节奏.drum', 'drum')
    drum = DrumPattern.load(path)
    assert [t.id for t in drum.tracks] == ['kick', 'snare', 'hihat']
    assert [t.name for t in drum.tracks] == ['底鼓 Kick', '军鼓 Snare', '踩镲 Hi-hat']
    assert drum.hits == {'kick': [], 'snare': [], 'hihat': []}
    assert drum.to_dict()['version'] == 2
    assert not [n for instrument in drum_midi(drum).instruments for n in instrument.notes]
    assert np.count_nonzero(render_drum_pattern(drum)) == 0
    drum.toggle('kick', 0)
    drum.save(path)
    assert DrumPattern.load(path).hits == {'kick': [0], 'snare': [], 'hihat': []}


def test_new_drum_api_is_blank_but_sample_is_explicit():
    new = default_drum_pattern()
    assert len(new.tracks) == 3
    assert all(not steps for steps in new.hits.values())
    example = sample_drum_pattern()
    assert any(example.hits.values())
    assert all(not steps for steps in new.hits.values())


def test_existing_drum_file_not_overwritten_when_creating_new(tmp_path):
    project = ProjectWorkspace.create(tmp_path, 'Project')
    existing = project.new_asset('old.drum', 'drum')
    pattern = DrumPattern.load(existing)
    pattern.toggle('snare', 12)
    pattern.save(existing)
    with pytest.raises(FileExistsError):
        project.new_asset('old.drum', 'drum')
    assert DrumPattern.load(existing).hits['snare'] == [12]
