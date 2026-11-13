"""Headless theme and notation integration tests; Qt is intentionally optional."""
from pathlib import Path
from melody_notation.qt_design import COLORS, THEME_NAMES, EN, translated
from melody_notation.png import SCORE_THEMES, render_score, export_png
from melody_notation.core import parse_text

TEXT='title: Theme test\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 5 |'

def _lum(hexcode):
    rgb=[int(hexcode[i:i+2],16)/255 for i in (1,3,5)]
    r,g,b=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    return .2126*r+.7152*g+.0722*b

def _contrast(a,b):
    x,y=sorted([_lum(a),_lum(b)],reverse=True)
    return (x+.05)/(y+.05)

def test_four_theme_palettes_and_readability():
    assert set(COLORS)==set(SCORE_THEMES)==set(THEME_NAMES)=={'light','dark','beige','olive'}
    for key,c in COLORS.items():
        assert _contrast(c['window'],c['ink'])>=4.5
        assert _contrast(c['accent'],c['on_accent'])>=4.5
        assert _contrast(SCORE_THEMES[key]['paper'],SCORE_THEMES[key]['ink'])>=4.5

def test_score_colors_follow_editor_theme_but_print_export_stays_light(tmp_path):
    score=parse_text(TEXT)
    for key,colors in SCORE_THEMES.items():
        image,hitboxes=render_score(score,theme=key)
        assert len(hitboxes)==4
        assert image.getpixel((0,0))==tuple(bytes.fromhex(colors['paper'][1:]))
    saved=export_png(score,tmp_path/'print.png')
    from PIL import Image
    with Image.open(saved) as image:assert image.getpixel((0,0))==(255,255,255)

def test_translation_dictionary_keeps_note_data_intact():
    assert translated('项目','en')=='Projects'
    assert translated('设置','en')=='Settings'
    assert translated('1 拍','en')=='1 beats'
    assert translated('荒.jianpu','en')=='荒.jianpu'
    assert translated('音色','zh')=='音色'
