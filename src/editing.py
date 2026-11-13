"""Pure score mutations shared by GUI, Codex and DeepSeek Harness MCP tools."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from .core import Score, ORNAMENTS, parse_text, text_from_score

DURATIONS = (0.125, 0.25, 0.375, 0.5, 0.75, 0.875, 1, 1.5, 1.75, 2, 3, 4)


def get_note(score: Score, bar: int, index: int):
    """Return a note at a **one-indexed** measure/note position."""
    if not 1 <= bar <= len(score.measures):
        raise IndexError(f'Measure {bar} out of range (1..{len(score.measures)})')
    notes = score.measures[bar - 1]
    if not 1 <= index <= len(notes):
        raise IndexError(f'Note {index} out of range in measure {bar}')
    return notes[index - 1]


def update_note(score: Score, bar: int, index: int, *, degree: int | None = None,
                octave: int | None = None, beats: float | None = None,
                accidental: int | None = None, ornament: str | None = None) -> Score:
    """Return new score with a changed note; temporarily incomplete bars are allowed."""
    s = deepcopy(score)
    n = get_note(s, bar, index)
    values = dict(degree=n.degree if degree is None else int(degree),
                  octave=n.octave if octave is None else int(octave),
                  beats=n.beats if beats is None else float(beats),
                  accidental=n.accidental if accidental is None else int(accidental),
                  ornament=n.ornament if ornament is None else str(ornament))
    if values['degree'] not in range(8): raise ValueError('Degree must be 0..7')
    if not -3 <= values['octave'] <= 3: raise ValueError('Octave must be between -3 and +3')
    if values['beats'] not in DURATIONS: raise ValueError(f'Beats must be one of {DURATIONS}')
    if values['accidental'] not in (-1,0,1): raise ValueError('Accidental must be -1, 0 or 1')
    if values['ornament'] not in ORNAMENTS: raise ValueError(f'Unsupported ornament {values["ornament"]}')
    if values['degree'] == 0:
        if ornament is None: values['ornament'] = ''
        if values['ornament']: raise ValueError('Rest cannot carry an ornament')
        if octave is None: values['octave'] = 0
        if accidental is None: values['accidental'] = 0
        if values['accidental'] != 0 or values['octave'] != 0:
            raise ValueError('Rest must be in base octave with no accidental')
        if n.slur_start or n.slur_end:
            raise ValueError('Remove the slur before changing its endpoint to a rest')
    s.measures[bar-1][index-1] = replace(n, **values, token='', dotted=0)
    return parse_text(text_from_score(s), strict=False)


def _positions(score: Score):
    return [(bi,ni) for bi,notes in enumerate(score.measures,1)
            for ni,_ in enumerate(notes,1)]


def existing_slurs(score: Score):
    start = None
    spans = []
    for pos in _positions(score):
        n = get_note(score,*pos)
        if n.slur_start:
            if start is not None: raise ValueError('Nested slurs are unsupported')
            start = pos
        if n.slur_end:
            if start is None: raise ValueError('Slur end without start')
            spans.append((start,pos))
            start = None
    if start is not None: raise ValueError('Unclosed slur')
    return spans


def add_slur(score: Score, start_bar: int, start_note: int, end_bar: int, end_note: int) -> Score:
    """Add a notation slur, allowing it to extend across bars and score rows."""
    start, end = (start_bar,start_note),(end_bar,end_note)
    allpos = _positions(score)
    if start not in allpos or end not in allpos: raise IndexError('Slur endpoint out of range')
    a,b = allpos.index(start),allpos.index(end)
    if b <= a: raise ValueError('Slur end must be later than its start')
    for pos in allpos[a:b+1]:
        if get_note(score,*pos).degree == 0: raise ValueError('Slur cannot include rests')
    for old_start,old_end in existing_slurs(score):
        oa,ob = allpos.index(old_start),allpos.index(old_end)
        if not (b < oa or a > ob): raise ValueError('Slur overlaps an existing slur')
    s=deepcopy(score)
    get_note(s,*start).slur_start=True
    get_note(s,*end).slur_end=True
    return s


def clear_slur(score: Score, bar: int, index: int) -> Score:
    """Remove the slur containing a note. Unrelated slurs stay untouched."""
    pos=(bar,index)
    allpos=_positions(score)
    if pos not in allpos: raise IndexError('Note out of range')
    at=allpos.index(pos)
    for start,end in existing_slurs(score):
        if allpos.index(start)<=at<=allpos.index(end):
            s=deepcopy(score)
            get_note(s,*start).slur_start=False
            get_note(s,*end).slur_end=False
            return s
    raise ValueError('Selected note is not part of a slur')


def insert_note(score:Score, bar:int, index:int, degree:int=1, beats:float=1) -> Score:
    """Insert before one-indexed position; bar may be overfull until user fixes timing."""
    s=deepcopy(score)
    if not 1<=bar<=len(s.measures): raise IndexError('Measure out of range')
    if not 1<=index<=len(s.measures[bar-1])+1: raise IndexError('Insert position out of range')
    from .core import Note
    if degree not in range(8) or beats not in DURATIONS: raise ValueError('Invalid note')
    s.measures[bar-1].insert(index-1,Note(degree=degree,beats=beats))
    return parse_text(text_from_score(s), strict=False)


def delete_note(score:Score, bar:int, index:int) -> Score:
    s=deepcopy(score)
    n=get_note(s,bar,index)
    if n.slur_start or n.slur_end: raise ValueError('Remove slur before deleting endpoint')
    # Empty measures are valid editing canvases in v0.4.7; removing the
    # final note returns to the blank state rather than blocking deletion.
    del s.measures[bar-1][index-1]
    return s
