"""Regression checks for the in-app beginner tutorial."""
from melody_notation.core import parse_text
from melody_notation.help_dialog import EXAMPLE_SCORE, HELP_SECTIONS


def test_tutorial_example_is_valid_4_4_score():
    score = parse_text(EXAMPLE_SCORE)
    assert score.validate() == []
    assert len(score.measures) == 4
    assert score.measures[2][0].slur_start
    assert score.measures[2][3].slur_end


def test_tutorial_coverage_and_invalid_note_explained():
    titles = [section.title for section in HELP_SECTIONS]
    assert len(titles) == len(set(titles))
    joined = '\n'.join(s.content for s in HELP_SECTIONS)
    for topic in ['6/5', 'Ctrl+Enter', 'F1', '连音', 'MIDI', 'MP3', 'PNG', 'DeepSeek Harness']:
        assert topic in joined
