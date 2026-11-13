"""Real-time keyboard/MIDI performance capture and editable jianpu transcription.

Time-accurate polyphonic MIDI is kept separately from the monophonic notation
projection, so transcribing a melody never silently destroys chord recordings.
This module has no Qt or audio-device dependency.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from .core import KEYS, SCALE, Note, Score
from .midi import INSTRUMENTS

# These lengths can be rendered by text_from_score without extensions.
LENGTHS = (4.0, 3.0, 2.0, 1.75, 1.5, 1.0, .875, .75, .5, .375, .25, .125)
DEFAULT_KEYS = {
    'A':60, 'W':61, 'S':62, 'E':63, 'D':64, 'F':65, 'T':66,
    'G':67, 'Y':68, 'H':69, 'U':70, 'J':71, 'K':72, 'O':73,
    'L':74, 'P':75, ';':76, "'":77, ']':78, '\\':79,
}
MIN_PITCH, MAX_PITCH = 48, 96


def normalized_key(key: str) -> str:
    """Use a single printable physical key label, without modifiers."""
    if not isinstance(key, str) or len(key) != 1 or not key.isprintable() or key.isspace():
        raise ValueError('键位须为一个可打印的字符（不支持组合快捷键）')
    return key.upper()


def validate_mapping(mapping: dict[str, int], *, min_pitch: int = MIN_PITCH,
                     max_pitch: int = MAX_PITCH) -> dict[str, int]:
    result = {}
    pitches = set()
    for key, pitch in mapping.items():
        name = normalized_key(key)
        pitch = int(pitch)
        if name in result or pitch in pitches:
            raise ValueError('不能重复分配同一个键位或琴键')
        if not min_pitch <= pitch <= max_pitch:
            raise ValueError('键位超出可演奏的钢琴范围')
        result[name] = pitch
        pitches.add(pitch)
    return result


def pitch_to_note(pitch: int, key: str = 'C', beats: float = 1.0) -> Note:
    """Find a diatonic degree and optional accidental matching exact MIDI pitch."""
    if not 0 <= pitch <= 127:
        raise ValueError('Invalid MIDI pitch')
    base = 60 + KEYS[key.upper()]
    candidates = []
    for octave in range(-6, 6):
        for degree, semitone in enumerate(SCALE, 1):
            for accidental in (0, 1, -1):
                if base + 12 * octave + semitone + accidental == pitch:
                    candidates.append((abs(accidental), accidental < 0, abs(octave),
                                       degree, octave, accidental))
    if not candidates:
        raise ValueError(f'MIDI pitch {pitch} is not notatable')
    _, _, _, degree, octave, accidental = min(candidates)
    return Note(degree=degree, octave=octave, accidental=accidental, beats=beats)


@dataclass(frozen=True)
class PerformedNote:
    pitch: int
    velocity: int
    start: float
    end: float
    source: str = 'keyboard'


class PerformanceSession:
    """Record note on/off at monotonic timestamps; project onto score per event."""
    def __init__(self, base: Score, *, quantum: float = .25,
                 clock: Callable[[], float] = perf_counter):
        if quantum != .25:
            raise ValueError('Current notation engine supports 1/4-beat recording grid')
        self.base = deepcopy(base)
        self.quantum = quantum
        self.clock = clock
        # The first played note defines time zero, not the Record-button click.
        self.origin = None
        self.active: dict[tuple[str, int], tuple[int, float]] = {}
        self.notes: list[PerformedNote] = []

    def note_on(self, pitch: int, velocity: int = 90, source: str = 'keyboard',
                now: float | None = None) -> bool:
        if not 0 <= pitch <= 127: return False
        if velocity <= 0: return self.note_off(pitch, source, now)
        stamp = self.clock() if now is None else now
        if self.origin is None:self.origin=stamp
        k = (source, pitch)
        if k in self.active:
            self.note_off(pitch, source, stamp)
        self.active[k] = (min(127, max(1, int(velocity))), max(0., stamp-self.origin))
        return True

    def note_off(self, pitch: int, source: str = 'keyboard',
                 now: float | None = None) -> bool:
        k = (source, pitch)
        v = self.active.pop(k, None)
        if v is None: return False
        stamp = self.clock() if now is None else now
        self.notes.append(PerformedNote(pitch, v[0], v[1],
            max(v[1] + .025, stamp - self.origin), source))
        return True

    def finish(self, now: float | None = None) -> None:
        for source, pitch in list(self.active):
            self.note_off(pitch, source, now)

    def all_notes(self, *, include_active: bool = True, now: float | None = None) -> list[PerformedNote]:
        notes = list(self.notes)
        if include_active and self.origin is not None:
            t = (self.clock() if now is None else now) - self.origin
            for (source, pitch), (vel, start) in self.active.items():
                notes.append(PerformedNote(pitch, vel, start, max(start+.025, t), source))
        return sorted(notes, key=lambda n: (n.start, n.pitch, n.end))

    def notation(self, *, include_active: bool = True, now: float | None = None) -> Score:
        """Project recorded performance into editable, single-voice notation.

        The original MIDI events are *never* quantized. For notation only, a
        densely played passage switches from sixteenth to thirty-second notes.
        Close successive strikes keep distinct note slots, while short key-up
        gaps are joined instead of producing visually noisy 1/16 rests.
        """
        score = deepcopy(self.base)
        played = self.all_notes(include_active=include_active, now=now)
        if not played:
            return score
        beat_seconds = 60.0 / score.bpm
        bar_size = score.beats_per_bar

        # A MIDI chord (onsets within 20ms) projects to one pitch; real
        # arpeggios remain separate even when rounding would merge them.
        melody = []
        for event in played:
            if melody and event.start - melody[-1].start < .020:
                continue
            melody.append(event)
        quantum = self.quantum
        if quantum == .25 and any(
            .020 <= b.start - a.start < beat_seconds * .25
            for a, b in zip(melody, melody[1:])
        ):
            # 1/8 beat = a thirty-second note, supported by .jianpu /8.
            quantum = .125
        bar_ticks = round(bar_size / quantum)
        if bar_ticks <= 0 or abs(bar_ticks * quantum - bar_size) > 1e-7:
            raise ValueError('Time signature cannot be expressed on the recording grid')

        if score.measures and any(score.measures[-1]):
            score.measures.append([])
        if not score.measures:
            score.measures = [[]]
        start_bar = len(score.measures) - 1
        cursor_ticks = 0

        def insert(pitch: int | None, ticks: int):
            nonlocal cursor_ticks
            while ticks > 0:
                current_bar = start_bar + cursor_ticks // bar_ticks
                while len(score.measures) <= current_bar:
                    score.measures.append([])
                room = bar_ticks - cursor_ticks % bar_ticks
                available = min(ticks, room)
                size = next((length for length in LENGTHS
                             if round(length / quantum) <= available
                             and abs(round(length / quantum) * quantum - length) < 1e-7),
                            quantum)
                size_ticks = round(size / quantum)
                current_key = score.key
                for number, new_key in sorted(score.key_changes.items()):
                    if number <= current_bar + 1:
                        current_key = new_key
                note = pitch_to_note(pitch, current_key, size) if pitch is not None else Note(0, beats=size)
                score.measures[current_bar].append(note)
                cursor_ticks += size_ticks
                ticks -= size_ticks

        events = []
        last_tick = -1
        for event in melody:
            ideal_tick = round((event.start / beat_seconds) / quantum)
            # Do not silently drop rapid individual key presses into the same
            # quantized bucket. Notes may shift forward if played faster than
            # the smallest printable duration; raw MIDI stays time-accurate.
            begin_tick = max(last_tick + 1, ideal_tick)
            last_tick = begin_tick
            end_tick = max(begin_tick + 1, round((event.end / beat_seconds) / quantum))
            events.append((begin_tick, end_tick, event))

        close_gap = min(.15, beat_seconds * .30)
        for i, (begin, end, event) in enumerate(events):
            if i + 1 < len(events):
                next_begin, _, next_event = events[i + 1]
                end = min(end, next_begin)
                # A tiny hand-off between keys is not a musical rest.
                if next_event.start - event.end <= close_gap:
                    end = next_begin
            end = max(begin + 1, end)
            if begin > cursor_ticks:
                insert(None, begin - cursor_ticks)
            insert(event.pitch, end - begin)
        remainder = cursor_ticks % bar_ticks
        if remainder:
            insert(None, bar_ticks - remainder)
        score.validate(strict=True)
        return score

    def export_midi(self, path, instrument: str = 'piano', now: float | None = None):
        """Export original timing, velocities and all simultaneous MIDI notes."""
        from pathlib import Path
        import pretty_midi
        if instrument not in INSTRUMENTS:
            raise ValueError(f'Unsupported instrument: {instrument}')
        pm = pretty_midi.PrettyMIDI(initial_tempo=self.base.bpm)
        inst = pretty_midi.Instrument(program=INSTRUMENTS[instrument], name=instrument)
        for item in self.all_notes(now=now):
            inst.notes.append(pretty_midi.Note(
                velocity=item.velocity, pitch=item.pitch, start=item.start, end=item.end))
        pm.instruments.append(inst)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pm.write(str(path))
        return path
