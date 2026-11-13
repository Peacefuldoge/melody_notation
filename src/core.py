"""Single source of truth for a score. Text syntax <-> JSON model."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import json
import re

TOKEN = re.compile(r"^(?P<acc>[#b]?)(?P<degree>[0-7])(?P<oct>[',]*)(?P<dots>\.{0,2})(?:/(?P<divisor>2|4|8))?(?:\{(?P<ornament>[a-z_]+)\})?$", re.ASCII)
ORNAMENTS = ("", "tr", "mordent", "lower_mordent", "turn", "staccato", "accent", "tenuto", "tremolo")
KEYS = {"C": 0, "C#": 1, "DB": 1, "D": 2, "EB": 3, "D#": 3, "E": 4, "F": 5,
        "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "BB": 10, "A#": 10, "B": 11}
SCALE = (0, 2, 4, 5, 7, 9, 11)

@dataclass
class Note:
    degree: int
    octave: int = 0
    beats: float = 1.0
    accidental: int = 0
    dotted: int = 0
    token: str = ""
    slur_start: bool = False
    slur_end: bool = False
    ornament: str = ""

    def midi_pitch(self, key: str) -> int | None:
        if self.degree == 0:
            return None
        key_offset = KEYS.get(key.upper())
        if key_offset is None:
            raise ValueError(f"Unsupported key {key!r}; examples: C, D, Bb, F#")
        pitch = 60 + key_offset + SCALE[self.degree-1] + 12*self.octave + self.accidental
        if not 0 <= pitch <= 127:
            raise ValueError(f"Pitch out of MIDI range: {pitch}")
        return pitch

@dataclass
class Score:
    title: str
    key: str
    bpm: int
    numerator: int
    denominator: int
    measures: list[list[Note]]
    # 1-based bar number -> new tonic, e.g. {25: "Bb"}
    key_changes: dict[int, str] = field(default_factory=dict)

    @property
    def beats_per_bar(self) -> float:
        return self.numerator * 4 / self.denominator

    def validate(self, strict: bool = False) -> list[str]:
        issues = []
        if not 20 <= self.bpm <= 400:
            issues.append("BPM must be 20..400")
        if self.key.upper() not in KEYS:
            issues.append(f"Unsupported key: {self.key}")
        if not self.measures:
            issues.append("Score has no measures")
        for bar_number, key_name in self.key_changes.items():
            if not isinstance(bar_number, int) or bar_number <= 1 or bar_number > len(self.measures):
                issues.append(f"Invalid key change measure: {bar_number}")
            if key_name.upper() not in KEYS:
                issues.append(f"Unsupported key change: {key_name}")
        open_slur = None
        for bi, bar in enumerate(self.measures, 1):
            for ni, n in enumerate(bar, 1):
                if n.degree not in range(8) or n.beats <= 0 or n.accidental not in (-1, 0, 1):
                    issues.append(f"Measure {bi} note {ni}: invalid note attributes")
                if n.ornament not in ORNAMENTS:
                    issues.append(f"Measure {bi} note {ni}: unsupported ornament {n.ornament!r}")
                if n.degree == 0 and n.ornament:
                    issues.append(f"Measure {bi} note {ni}: rest cannot carry an ornament")
                if n.slur_start:
                    if n.degree == 0: issues.append(f"Measure {bi} note {ni}: a rest cannot start a slur")
                    if open_slur is not None: issues.append(f"Measure {bi} note {ni}: nested slurs are unsupported")
                    open_slur = (bi, ni)
                if open_slur is not None and n.degree == 0:
                    issues.append(f"Measure {bi} note {ni}: a slur cannot contain a rest")
                if n.slur_end:
                    if n.degree == 0: issues.append(f"Measure {bi} note {ni}: a rest cannot end a slur")
                    if open_slur is None: issues.append(f"Measure {bi} note {ni}: slur end without start")
                    elif open_slur == (bi, ni): issues.append(f"Measure {bi} note {ni}: slur needs at least two notes")
                    open_slur = None
        if open_slur is not None:
            issues.append(f"Unclosed slur starting at measure {open_slur[0]} note {open_slur[1]}")
        for i, bar in enumerate(self.measures, 1):
            # An intentionally empty measure is valid in an unwritten score.
            # It must not be mistaken for an incomplete/incorrectly timed bar.
            if not bar:
                continue
            got = sum(n.beats for n in bar)
            if abs(got-self.beats_per_bar) > 1e-5:
                issues.append(f"Measure {i}: {got:g} beats; expected {self.beats_per_bar:g}")
        if strict and issues:
            raise ValueError("; ".join(issues))
        return issues

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict, strict: bool = True) -> "Score":
        result = cls(d['title'], d['key'], int(d['bpm']), int(d['numerator']),
                     int(d['denominator']), [[Note(**n) for n in bar] for bar in d['measures']],
                     {int(k): v for k, v in d.get('key_changes', {}).items()})
        result.validate(strict=strict)
        return result

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def load_json(cls, path: str | Path) -> "Score":
        return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))


def blank_score_text(title: str = '新简谱') -> str:
    """One empty 4/4 measure, no preset notes or rests."""
    return f'title: {title}\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| |\n'


def parse_note(token: str) -> Note:
    m = TOKEN.fullmatch(token)
    if not m:
        raise ValueError(f"Invalid note {token!r}. Use 1, 1', 5,, 3/2, 6'./2, 0 or -")
    d = int(m.group('degree'))
    octave_symbols = m.group('oct')
    if octave_symbols and ("'" in octave_symbols and ',' in octave_symbols):
        raise ValueError(f"Mixed octave markers in {token!r}")
    acc = {'#': 1, 'b': -1, '': 0}[m.group('acc')]
    ornament = m.group("ornament") or ""
    if ornament not in ORNAMENTS:
        raise ValueError(f"Unsupported ornament: {ornament}")
    if d == 0 and ornament:
        raise ValueError("Rest cannot have an ornament")
    if d == 0 and (acc or octave_symbols):
        raise ValueError('Rest cannot have accidentals or octave marks')
    dots = len(m.group('dots'))
    divisor = int(m.group('divisor') or '1')
    beat = sum(.5**i for i in range(dots+1)) / divisor
    return Note(degree=d, octave=octave_symbols.count("'")-octave_symbols.count(','),
                beats=beat, accidental=acc, dotted=dots, token=token, ornament=ornament)


def parse_text(src: str, strict: bool = True) -> Score:
    meta = {'title': '未命名', 'key': 'C', 'bpm': '120', 'time': '4/4', 'key_changes': ''}
    note_lines = []
    in_notes = False
    for line in src.splitlines():
        line = line.split('//', 1)[0].strip()
        if not line or line.startswith('# '):
            continue
        if not in_notes and re.match(r'^(title|key|bpm|time|key_changes|notes)\s*:', line, re.I):
            k,v = line.split(':', 1)
            if k.lower() == 'notes':
                in_notes = True
                if v.strip(): note_lines.append(v.strip())
            else:
                meta[k.lower()] = v.strip()
        elif in_notes:
            note_lines.append(line)
        else:
            raise ValueError(f"Expected title/key/bpm/time/notes header, got {line!r}")
    sig = re.fullmatch(r'(\d+)\s*/\s*(1|2|4|8|16)', meta['time'])
    if not sig:
        raise ValueError("Invalid time signature; example time: 4/4")
    # Preserve the original flexible delimiter behavior: a trailing barline
    # followed by a leading barline on the next line is not an empty measure.
    # A score with no note tokens, however, has one intentional blank bar.
    parts = ' '.join(note_lines).split('|')
    measures = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        events = []
        if part.upper() == 'R':
            events.append(Note(0, beats=int(sig[1])*4/int(sig[2]), token='R'))
        else:
            pending_start = False
            for t in part.split():
                if t == '(':
                    if pending_start: raise ValueError('Nested slurs are not supported')
                    pending_start = True
                elif t == ')':
                    if not events: raise ValueError('Slur end needs an earlier note')
                    events[-1].slur_end = True
                elif t == '-':
                    if not events:
                        raise ValueError(f"Measure {len(measures)+1}: '-' needs a previous note")
                    events[-1].beats += 1
                    events[-1].token += ' -'
                else:
                    n = parse_note(t)
                    if pending_start:
                        n.slur_start = True
                        pending_start = False
                    events.append(n)
            if pending_start: raise ValueError('Slur start must precede a note')
        measures.append(events)
    if not measures:
        measures = [[]]
    changes = {}
    if meta['key_changes']:
        for item in meta['key_changes'].split(','):
            m = re.fullmatch(r'\s*(\d+)\s*=\s*([A-Ga-g][#bB]?)\s*', item)
            if m is None:
                raise ValueError('Invalid key_changes syntax; example: key_changes: 25=Bb')
            bar_index = int(m[1])
            if bar_index in changes:
                raise ValueError(f'Duplicate key change at measure {bar_index}')
            changes[bar_index] = m[2]
    score = Score(meta['title'], meta['key'], int(meta['bpm']), int(sig[1]), int(sig[2]), measures, changes)
    score.validate(strict=strict)
    return score


def text_from_score(s: Score) -> str:
    bars = []
    for bar in s.measures:
        tokens = []
        for n in bar:
            if n.token:
                token_text = n.token
            elif n.degree == 0 and n.beats == s.beats_per_bar and len(bar) == 1:
                token_text = 'R'
            else:
                octaves = "'"*max(n.octave, 0) + ','*max(-n.octave, 0)
                accidental = '#' if n.accidental == 1 else ('b' if n.accidental == -1 else '')
                beats = n.beats
                # Editable JSON without an original token: reconstruct common note values.
                rhythms = {1: '', 1.5: '.', 1.75: '..', .5: '/2', .75: './2',
                           .875: '../2', .25: '/4', .375: './4', .125: '/8'}
                pattern = rhythms.get(round(beats, 4))
                if pattern is None and beats >= 2 and beats == int(beats):
                    pattern = ' -' * (int(beats)-1)
                if pattern is None:
                    raise ValueError(f'Cannot format note with {beats:g} beats as simple jianpu')
                token_text = f'{accidental}{n.degree}{octaves}{pattern}'
            if n.ornament and "{" not in token_text:
                token_text += "{" + n.ornament + "}"
            if n.slur_start: tokens.append('(')
            tokens.append(token_text)
            if n.slur_end: tokens.append(')')
        bars.append(' '.join(tokens))
    changes = ''
    if s.key_changes:
        changes = 'key_changes: ' + ', '.join(f'{k}={v}' for k,v in sorted(s.key_changes.items())) + '\n'
    return (f"title: {s.title}\nkey: {s.key}\ntime: {s.numerator}/{s.denominator}\n"
            f"bpm: {s.bpm}\n{changes}notes:\n| " + " | ".join(bars) + " |\n")


def timeline_events(score: Score, speed: float = 1.0):
    """Yield (start, end, MIDI pitch, velocity) with rendered ornaments.

    Ornaments consume the parent note's existing rhythmic duration; they never
    alter bar lengths. Neighbor tones are diatonic to the written major key.
    """
    if not .25 <= speed <= 4.0:
        raise ValueError("Playback speed must be between 0.25 and 4.0")
    seconds_per_beat = 60 / (score.bpm * speed)
    pos = 0.0
    current_key = score.key
    for bar_index, bar in enumerate(score.measures, 1):
        current_key = score.key_changes.get(bar_index, current_key)
        for n in bar:
            duration = n.beats * seconds_per_beat
            pitch = n.midi_pitch(current_key)
            if pitch is not None:
                next_degree = n.degree + 1
                upper = Note(degree=next_degree if next_degree <= 7 else 1,
                             octave=n.octave + (1 if next_degree > 7 else 0)).midi_pitch(current_key)
                prev_degree = n.degree - 1
                lower = Note(degree=prev_degree if prev_degree >= 1 else 7,
                             octave=n.octave - (1 if prev_degree < 1 else 0)).midi_pitch(current_key)
                if n.ornament == 'tr':
                    count = max(2, min(64, round(n.beats * 8)))
                    pitches = [pitch if i % 2 == 0 else upper for i in range(count)]
                    portions = [duration / count] * count
                elif n.ornament in ('mordent', 'lower_mordent'):
                    middle = upper if n.ornament == 'mordent' else lower
                    quick = duration * .125
                    pitches = [pitch, middle, pitch]
                    portions = [quick, quick, duration - 2 * quick]
                elif n.ornament == 'turn':
                    pitches = [upper, pitch, lower, pitch]
                    portions = [duration * .2, duration * .2, duration * .2, duration * .4]
                elif n.ornament == 'tremolo':
                    count = max(2, min(64, round(n.beats * 8)))
                    pitches = [pitch] * count
                    portions = [duration / count] * count
                else:
                    pitches = [pitch]
                    portions = [duration]
                offset = 0.0
                for i, (sub_pitch, length) in enumerate(zip(pitches, portions)):
                    gate = .55 if n.ornament == 'staccato' else (.96 if n.ornament == 'tenuto' else .93)
                    velocity = 116 if n.ornament == 'accent' else 92
                    yield pos + offset, pos + offset + length * gate, sub_pitch, velocity
                    offset += length
            pos += duration


def timeline(score: Score, speed: float = 1.0):
    """Backwards compatible 3-tuple API; expanded ornament performances."""
    for start, end, pitch, _velocity in timeline_events(score, speed=speed):
        yield start, end, pitch
