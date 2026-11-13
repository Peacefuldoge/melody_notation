"""Responsive piano range for the score editor (no Qt dependency).

A 2-octave C-to-C keyboard is the minimum visible range. At normal key
width, extra keys appear one by one on the right until a third C is reached.
The user can shift the entire range by octaves without changing MIDI input.
"""
from __future__ import annotations

DEFAULT_START_OCTAVE = 3
MIN_START_OCTAVE = 1
MAX_START_OCTAVE = 5
LOW_PITCH = 60      # C4 reference range for legacy key mappings
BASE_HIGH = 84      # C6, transposed to C5 for the C3 default
MAX_HIGH = 96       # C7, transposed to C6 for the C3 default
DEFAULT_WHITE_WIDTH = 57
MIN_WHITE_WIDTH = 33
WHITE_STEPS = frozenset((0, 2, 4, 5, 7, 9, 11))
WHITE_PITCHES = tuple(p for p in range(LOW_PITCH, MAX_HIGH + 1)
                      if p % 12 in WHITE_STEPS)
BASE_WHITE_COUNT = 15


def octave_offset(start_octave: int) -> int:
    """Semitone translation relative to the original C4-based key mappings."""
    if isinstance(start_octave, bool) or not isinstance(start_octave, int):
        raise ValueError('起始八度必须为整数')
    if not MIN_START_OCTAVE <= start_octave <= MAX_START_OCTAVE:
        raise ValueError(f'起始八度应在 C{MIN_START_OCTAVE}–C{MAX_START_OCTAVE} 之间')
    return 12 * (start_octave - 4)


def visible_note_range(start_octave: int, count: int) -> tuple[int, int]:
    """Return inclusive MIDI bounds for an expanding white-key layout."""
    shift = octave_offset(start_octave)
    notes = WHITE_PITCHES[:count]
    return notes[0] + shift, notes[-1] + shift


def piano_key_layout(available: int, start_octave: int = DEFAULT_START_OCTAVE
                     ) -> tuple[tuple[int, ...], int]:
    """Visible white MIDI notes and key width for the available pixels.

    The base 2 octaves shrink to a minimum key width on small screens;
    additional notes become visible at normal key width when room allows.
    At most one additional octave is shown on wide screens.
    """
    shift = octave_offset(start_octave)
    usable = max(0, int(available) - 2)  # edge/border allowance
    if usable < BASE_WHITE_COUNT * DEFAULT_WHITE_WIDTH:
        width = max(MIN_WHITE_WIDTH, usable // BASE_WHITE_COUNT)
        return tuple(p + shift for p in WHITE_PITCHES[:BASE_WHITE_COUNT]), width
    visible = max(BASE_WHITE_COUNT, min(len(WHITE_PITCHES), usable // DEFAULT_WHITE_WIDTH))
    return tuple(p + shift for p in WHITE_PITCHES[:visible]), DEFAULT_WHITE_WIDTH


def toolbar_row_groups(available: int, widths, spacing: int = 8) -> tuple[tuple[int, ...], ...]:
    """Pack atomic control groups into rows with no horizontal overlap.

    The last group (the settings action in the compact v0.5.8 toolbar)
    comes last; complete groups flow to the next row on narrow panes.
    """
    if not widths:
        return ()
    limit = max(1, int(available))
    gap = max(0, int(spacing))
    rows = []
    row = []
    used = 0
    for index, raw in enumerate(widths):
        wanted = max(1, int(raw))
        needed = wanted + (gap if row else 0)
        if row and used + needed > limit:
            rows.append(tuple(row))
            row = []
            used = 0
            needed = wanted
        row.append(index)
        used += needed
    if row:
        rows.append(tuple(row))
    return tuple(rows)
