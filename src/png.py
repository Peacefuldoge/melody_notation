"""Editable, hit-testable jianpu renderer shared by PNG export and GUI.

All coordinates are in the original PIL image; GUI scales the image and hitboxes together.
This is intentionally a compact notation layout, not a full music-engraving program.
"""
from __future__ import annotations
from math import sin, pi
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont
from .core import Score

FONTS = [
    'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/System/Library/Fonts/PingFang.ttc',
]

def _font(size: int):
    custom = os.environ.get('MELODY_FONT')
    for path in ([custom] if custom else []) + FONTS:
        if path and Path(path).exists(): return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


# Score paper has a dedicated palette instead of inheriting UI button colors.
# Keep the default renderer print-friendly. The GUI explicitly requests dark
# paper while in dark mode; headless exports and old callers stay light.
SCORE_THEMES = {
    'light': {
        'paper': '#FFFFFF', 'title': '#171F2C', 'ink': '#152238',
        'octave': '#12233A', 'meta': '#475569', 'muted': '#64748B',
        'barline': '#485569', 'bar_number': '#94A3B8',
        'slur': '#54547A', 'ornament': '#2563A6', 'key_change': '#2878A4',
        'selected_fill': '#D7F3FF', 'selected_line': '#1486C8',
        'invalid_fill': '#FFF2F0', 'invalid_ink': '#B42318',
    },
    'dark': {
        'paper': '#293544', 'title': '#F2F6FA', 'ink': '#EBF2FA',
        'octave': '#DAE8F5', 'meta': '#BBCBDD', 'muted': '#AABACC',
        'barline': '#91A3B7', 'bar_number': '#95A9C0',
        'slur': '#A7BCE4', 'ornament': '#97CAFF', 'key_change': '#8BC7EC',
        'selected_fill': '#36536B', 'selected_line': '#8BCBFF',
        'invalid_fill': '#563842', 'invalid_ink': '#FFB1B6',
    },
    'beige': {
        'paper': '#FAF6EB', 'title': '#352E26', 'ink': '#342C24',
        'octave': '#514336', 'meta': '#77644F', 'muted': '#887764',
        'barline': '#786A5A', 'bar_number': '#9B8D7B',
        'slur': '#84694C', 'ornament': '#966F47', 'key_change': '#8D633C',
        'selected_fill': '#EADCC6', 'selected_line': '#9C7652',
        'invalid_fill': '#F7DEDA', 'invalid_ink': '#A43D3A',
    },
    'olive': {
        'paper': '#F1F3E8', 'title': '#30382B', 'ink': '#293529',
        'octave': '#40523A', 'meta': '#61715A', 'muted': '#74826C',
        'barline': '#74816B', 'bar_number': '#8D9A83',
        'slur': '#617B50', 'ornament': '#4E714A', 'key_change': '#557047',
        'selected_fill': '#DDE7CB', 'selected_line': '#64794B',
        'invalid_fill': '#F3DFDA', 'invalid_ink': '#A34842',
    },
}


def _curve(draw, p0, p1, color='#54547a', width=3):
    x0,y0=p0; x1,y1=p1
    if x1-x0<10: return
    xy=[]
    for i in range(41):
        t=i/40
        # Shallow upward arch. Supports phrase marks spanning a score row.
        xy.append((x0+(x1-x0)*t, y0+(y1-y0)*t-17*sin(pi*t)))
    draw.line(xy, fill=color, width=width, joint='curve')


def score_measure_layout(score: Score, bars_per_row: int, width: int,
                         margin: int = 68) -> tuple[list[tuple[int, float, float]], int, int]:
    """Lay out exactly ``bars_per_row`` measures on each full score system.

    The dropdown represents an explicit number of measures per row, not an
    upper bound.  If the requested measures need more horizontal space than
    ``width``, widen the score paper instead of silently wrapping early or
    squeezing notes until the glyphs overlap.  The viewer can scroll or zoom.

    An incomplete last system is left-aligned rather than stretching its
    remaining one or two measures across the entire paper.
    """
    if not 1 <= bars_per_row <= 8:
        raise ValueError('bars_per_row should be 1..8')
    # 62px per note provides a readable minimum for accidentals, ornaments,
    # dots and note-selection hotspots at the renderer's 36px font size.
    widths = [max(215.0, 36.0 + 62.0 * len(bar)) for bar in score.measures]
    systems = [list(range(start, min(start + bars_per_row, len(widths))))
               for start in range(0, len(widths), bars_per_row)]
    # There can be no empty systems even when drawing an empty new score.
    inside = max(float(width - 2 * margin),
                 max((sum(widths[i] for i in system) for system in systems),
                     default=0.0))
    render_width = int(round(inside + 2 * margin))
    positions: list[tuple[int, float, float]] = [(0, 0.0, 0.0)] * len(widths)
    for row_no, system in enumerate(systems):
        used = sum(widths[i] for i in system)
        # Full systems are justified.  The last incomplete system keeps a
        # normal measure width and is ragged-right (standard score engraving).
        if len(system) == bars_per_row or len(systems) == 1:
            available = inside
        else:
            available = min(inside, max(used, inside * len(system) / bars_per_row))
        extra = max(0.0, available - used)
        weights = [max(1, len(score.measures[i])) for i in system]
        weight_total = sum(weights)
        x = float(margin)
        for k, index in enumerate(system):
            # Give surplus width in proportion to the number of notes, so
            # neighboring bars have a comparable amount of room per note.
            measure_width = widths[index] + extra * weights[k] / weight_total
            right = x + measure_width
            positions[index] = (row_no, x, right)
            x = right
    return positions, max(1, len(systems)), render_width


def _duration_lines(beats: float) -> tuple[int, ...]:
    """Vertical positions of underlines relative to the top of a system."""
    count = 0 if beats >= 1 else (1 if beats >= .5 else (2 if beats >= .25 else 3))
    return tuple(92 + 7 * i for i in range(count))


def _low_octave_dots(octave: int) -> tuple[int, ...]:
    """Low-octave dots always sit *below* even three duration underlines."""
    return tuple(122 + 11 * i for i in range(min(3, max(0, -octave))))

def render_score(score: Score, bars_per_row: int = 3, selected: tuple[int,int] | None = None,
                 width: int = 1440, theme: str = 'light'):
    """Return (PIL Image, [(bar_no, note_no, (x0,y0,x1,y1)), ...]).

    Invalid beat totals remain renderable while the user edits a bar. Export is strict.
    """
    if theme not in SCORE_THEMES:
        raise ValueError(f'Unknown score theme: {theme!r}')
    colors = SCORE_THEMES[theme]
    if not 1 <= bars_per_row <= 8: raise ValueError('bars_per_row should be 1..8')
    if width < 800: raise ValueError('width must be >= 800')
    margin=68
    row_h=207
    measure_positions, total_rows, width = score_measure_layout(score, bars_per_row, width, margin)
    height=192+total_rows*row_h+35
    im=Image.new('RGB',(width,height),colors['paper'])
    draw=ImageDraw.Draw(im)
    title_font, body, meta, small = _font(46),_font(36),_font(24),_font(18)
    draw.text((width//2,42),score.title,font=title_font,anchor='mt',fill=colors['title'])
    draw.text((margin,114),f'1={score.key.upper()}     {score.numerator}/{score.denominator}     ♩={score.bpm}',font=meta,fill=colors['meta'])
    draw.text((width-margin,119),'● 点击音符编辑     ⌒ 连音线',font=small,anchor='ra',fill=colors['muted'])
    hitboxes=[]
    locs={}
    invalid_bars=set()
    for mi,bar in enumerate(score.measures):
        if bar and abs(sum(n.beats for n in bar)-score.beats_per_bar)>1e-5:invalid_bars.add(mi+1)
        row,left,right = measure_positions[mi]
        cw=right-left
        top=184+row*row_h
        if mi+1 in score.key_changes:
            draw.text((left+8,top-17),f'转 1={score.key_changes[mi+1]}',
                      font=small,fill=colors['key_change'])
        if mi+1 in invalid_bars:
            draw.rounded_rectangle((left+4,top+16,right-4,top+154),radius=10,fill=colors['invalid_fill'])
        # A system's start/end barlines share the same vertical extent.
        draw.line((left,top+27,left,top+147),fill=colors['barline'],width=2)
        draw.line((right,top+27,right,top+147),fill=colors['barline'],width=2)
        total=max(1,len(bar)); step=(cw-36)/total
        for ni,n in enumerate(bar,1):
            cx=left+18+step*(ni-.5)
            boxw=max(32,min(52,step*.89))
            bounds=(cx-boxw*.5,top+29,cx+boxw*.5,top+149)
            if selected==(mi+1,ni):
                draw.rounded_rectangle((bounds[0]-3,bounds[1]-4,bounds[2]+3,bounds[3]+4),
                                       radius=8,fill=colors['selected_fill'],outline=colors['selected_line'],width=3)
            # Compact ornament label in the upper-right corner of a selected note.
            # The melody and octave marks remain visually primary.
            ornament_symbols = {'tr':'tr', 'mordent':'m', 'lower_mordent':'m↓',
                                'turn':'∽', 'staccato':'·', 'accent':'>',
                                'tenuto':'—', 'tremolo':'///'}
            if n.ornament:
                draw.text((cx+19,top+12),ornament_symbols.get(n.ornament,n.ornament),
                          font=small,anchor='lt',fill=colors['ornament'])
            label=str(n.degree)
            if n.accidental==1:label='#'+label
            if n.accidental==-1:label='b'+label
            draw.text((cx,top+46),label,font=body,anchor='mt',fill=colors['ink'])
            if n.octave>0:
                for i in range(min(3,n.octave)):
                    draw.ellipse((cx-3,top+31-10*i,cx+3,top+37-10*i),fill=colors['octave'])
            elif n.octave<0:
                for y in _low_octave_dots(n.octave):
                    draw.ellipse((cx-3,top+y-3,cx+3,top+y+3),fill=colors['octave'])
            # Underline indicates eighth/sixteenth/thirty-second in jianpu.
            beats=n.beats
            for y in _duration_lines(beats):
                draw.line((cx-13,top+y,cx+13,top+y),fill=colors['ink'],width=2)
            if beats in (.375,.75,1.5,1.75,.875):
                draw.ellipse((cx+17,top+66,cx+23,top+72),fill=colors['ink'])
            if beats>=2:
                draw.text((cx+19,top+77),f'×{beats:g}',font=small,fill=colors['muted'])
            locs[(mi+1,ni)]=(cx,top+18,row)
            hitboxes.append((mi+1,ni,bounds))
        # Put bar numbers below the low-octave dots and time-value lines.
        draw.text((right-10,top+172),f'{mi+1}',font=small,anchor='ra',fill=colors['bar_number'])
        if mi+1 in invalid_bars:
            draw.text((left+9,top+173),'节拍不匹配',font=small,fill=colors['invalid_ink'])
    # Slur rendering after all note positions are known. Split phrase marks at row changes.
    slur_start=None
    for pos in locs:
        n=score.measures[pos[0]-1][pos[1]-1]
        if n.slur_start: slur_start=pos
        if n.slur_end and slur_start is not None:
            x0,y0,r0=locs[slur_start];x1,y1,r1=locs[pos]
            if r0==r1:
                _curve(draw,(x0-8,y0),(x1+8,y1),color=colors['slur'])
            else:
                for row in range(r0,r1+1):
                    y=184+row*row_h+18
                    start_x=x0-8 if row==r0 else margin+15
                    end_x=x1+8 if row==r1 else width-margin-15
                    _curve(draw,(start_x,y),(end_x,y),color=colors['slur'])
            slur_start=None
    if invalid_bars:
        draw.text((margin,height-29),'红色小节表示拍数未对齐：请调整音符时值后再导出。',font=small,fill=colors['invalid_ink'])
    return im,hitboxes


def export_png(score: Score, path: str | Path, bars_per_row: int = 4,
               theme: str = 'light') -> Path:
    """Export a printable light PNG by default, regardless of the GUI theme.

    Callers may explicitly request theme='dark' for a dark-background image.
    """
    score.validate(strict=True)
    image,_=render_score(score,bars_per_row=bars_per_row,theme=theme)
    out=Path(path);out.parent.mkdir(parents=True,exist_ok=True)
    image.save(out)
    return out
