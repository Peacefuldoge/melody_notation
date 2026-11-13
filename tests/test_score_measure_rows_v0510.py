"""v0.5.10: exact measure counts and non-overlapping numbered notation."""
from pathlib import Path
from importlib import resources

import pytest

from melody_notation.core import Note, Score, blank_score_text, parse_text
from melody_notation.png import (
    score_measure_layout, render_score, _duration_lines, _low_octave_dots,
)


def _huang():
    return parse_text(resources.files('melody_notation').joinpath('samples', 'huang.jianpu').read_text(encoding='utf-8'))


@pytest.mark.parametrize('per_row', [2, 3, 4, 5])
def test_requested_bars_per_row_never_wrap_early(per_row):
    score = _huang()
    positions, rows, width = score_measure_layout(score, per_row, 1200)
    assert rows == (len(score.measures) + per_row - 1) // per_row
    assert [row for row, _, _ in positions] == [i // per_row for i in range(len(score.measures))]
    assert width >= 1200
    for i, (row, left, right) in enumerate(positions):
        assert left < right
        if i and row == positions[i-1][0]:
            assert abs(left - positions[i-1][2]) < .001
        elif i:
            assert left == 68
    # Real engraving uses the same row grouping and image width.
    image, hits = render_score(score, bars_per_row=per_row, width=1200)
    assert image.width == width
    assert sum(len(bar) for bar in score.measures) == len(hits)


def test_dense_bars_expand_paper_rather_than_overflow_or_rewrap():
    score = parse_text(blank_score_text(), strict=False)
    score.measures = [[Note(i % 7 + 1, beats=.125) for i in range(32)] for _ in range(4)]
    positions, rows, width = score_measure_layout(score, 4, 1200)
    assert rows == 1
    assert width > 8000  # preserve the space needed for 128 short notes
    _, boxes = render_score(score, bars_per_row=4, width=1200)
    for bar in range(1, 5):
        intervals = [(box[0], box[2]) for bi, _, box in boxes if bi == bar]
        assert all(left_b > right_a for (_,right_a),(left_b,_) in zip(intervals,intervals[1:]))


def test_last_incomplete_row_left_aligned_and_not_stretched():
    score = _huang()  # 41 bars, so final 4-bars-per-row system has one bar.
    positions, rows, width = score_measure_layout(score, 4, 1200)
    assert rows == 11
    assert positions[-1][0] == 10
    assert positions[-1][1] == 68
    assert positions[-1][2] < width - 68


def test_low_octave_dots_are_below_all_duration_underlines():
    underlines = _duration_lines(.125)
    dots = _low_octave_dots(-3)
    assert len(underlines) == 3 and len(dots) == 3
    assert min(dots) - max(underlines) >= 12
    assert max(dots) + 4 < 172  # bar number line is lower still


def test_score_files_not_resegmented():
    score = _huang()
    orig = score.to_dict()
    for count in (2, 3, 4, 5):
        render_score(score, bars_per_row=count, theme='dark')
    assert score.to_dict() == orig
