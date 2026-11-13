"""Preview dark mode must never change print exports or score data."""
from pathlib import Path
from PIL import Image
import pytest
from melody_notation.core import parse_text
from melody_notation.editing import add_slur
from melody_notation.png import SCORE_THEMES, render_score, export_png


def score():
    base = parse_text('title: 深色谱面测试\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2/2 3/2 4 5 |')
    return add_slur(base, 1, 1, 1, 4)


def test_dark_score_paper_and_ink_including_selection_and_slur():
    s = score()
    light, hits_light = render_score(s, selected=(1, 2), width=1000)
    dark, hits_dark = render_score(s, selected=(1, 2), width=1000, theme='dark')
    assert hits_light == hits_dark  # hit testing is theme independent
    assert light.size == dark.size
    assert light.getpixel((3, 3)) == (255, 255, 255)
    assert dark.getpixel((3, 3)) == tuple(bytes.fromhex(SCORE_THEMES['dark']['paper'][1:]))
    palette = {f'#{r:02X}{g:02X}{b:02X}' for count, (r,g,b) in dark.getcolors(dark.width * dark.height)}
    for part in ('ink', 'slur', 'selected_fill', 'selected_line', 'barline'):
        assert SCORE_THEMES['dark'][part] in palette
    assert light.tobytes() != dark.tobytes()


def test_invalid_bar_uses_dark_warning_palette():
    s = parse_text('title: 错误示例\nnotes:\n| 1 2 3 |', strict=False)
    image, _ = render_score(s, theme='dark')
    palette = {f'#{r:02X}{g:02X}{b:02X}' for count, (r,g,b) in image.getcolors(image.width * image.height)}
    assert SCORE_THEMES['dark']['invalid_fill'] in palette
    assert SCORE_THEMES['dark']['invalid_ink'] in palette


def test_export_png_default_remains_printable_light(tmp_path):
    s = score()
    # Preview dark mode does not change any global theme state.
    render_score(s, theme='dark')
    a = export_png(s, tmp_path/'default.png')
    with Image.open(a) as im:
        assert im.getpixel((3, 3)) == (255, 255, 255)
    dark = export_png(s, tmp_path/'dark.png', theme='dark')
    with Image.open(dark) as im:
        assert im.getpixel((3, 3)) == tuple(bytes.fromhex(SCORE_THEMES['dark']['paper'][1:]))


def test_bad_theme_rejected():
    with pytest.raises(ValueError, match='Unknown score theme'):
        render_score(score(), theme='black')
