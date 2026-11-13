from pathlib import Path
import pretty_midi
from .core import Score, timeline_events

INSTRUMENTS = {
    'piano': 0, 'music_box': 10, 'guitar': 24, 'violin': 40,
    'strings': 48, 'flute': 73, 'clarinet': 71,
    'gameboy': 80,  # GM Lead 1 (square), approximate chiptune sound on MIDI devices
}

def make_midi(score: Score, instrument: str = 'piano') -> pretty_midi.PrettyMIDI:
    score.validate(strict=True)
    if instrument not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument: {instrument}; choose {list(INSTRUMENTS)}")
    pm = pretty_midi.PrettyMIDI(initial_tempo=score.bpm)
    inst = pretty_midi.Instrument(program=INSTRUMENTS[instrument], name=instrument)
    for t, end, pitch, velocity in timeline_events(score):
        inst.notes.append(pretty_midi.Note(velocity=velocity, pitch=pitch, start=t, end=end))
    pm.instruments.append(inst)
    return pm

def export_midi(score: Score, path: str | Path, instrument: str = 'piano') -> Path:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    make_midi(score, instrument).write(str(p))
    return p
