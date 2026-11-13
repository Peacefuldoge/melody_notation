"""Portable, editable .drum patterns (4 subdivisions per quarter beat).

Each file starts with three tracks but v2 supports user-defined rows, each
mapped to kick, snare, or closed hi-hat. Drum sounds use GM 36/38/42 on
percussion channel 10; the local synth has acoustic/electronic/chiptune kits.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math
import numpy as np

DRUM_VOICES = {'kick': 36, 'snare': 38, 'hihat': 42}
DRUM_LABELS = {'kick': '底鼓 Kick', 'snare': '军鼓 Snare', 'hihat': '踩镲 Hi-hat'}
DRUM_KITS = ('acoustic', 'electronic', 'gameboy')
KIT_LABELS = {'acoustic': '原声鼓', 'electronic': '电子鼓 / 808', 'gameboy': '8-bit 芯片鼓'}
STEPS_PER_BEAT = 4


@dataclass
class DrumTrack:
    """One independently named row; sound selects a supported GM drum voice."""
    id: str
    name: str
    sound: str


def default_drum_tracks() -> list[DrumTrack]:
    return [DrumTrack(key, DRUM_LABELS[key], key) for key in DRUM_VOICES]


@dataclass
class DrumPattern:
    title: str = '新鼓点'
    bpm: int = 120
    bars: int = 2
    kit: str = 'acoustic'
    # Keys are persistent row IDs, NOT display names or sound categories.
    hits: dict[str, list[int]] = field(default_factory=lambda: {v: [] for v in DRUM_VOICES})
    tracks: list[DrumTrack] = field(default_factory=default_drum_tracks)
    next_track_number: int = 4

    @property
    def steps(self) -> int:
        return self.bars * 16

    @property
    def beats(self) -> float:
        return self.bars * 4.0

    def validate(self) -> None:
        if not self.title.strip():
            raise ValueError('鼓点标题不能为空')
        if not 20 <= self.bpm <= 400 or not 1 <= self.bars <= 64:
            raise ValueError('鼓点 BPM 应为 20–400，小节数应为 1–64')
        if self.kit not in DRUM_KITS:
            raise ValueError(f'未知鼓组：{self.kit}')
        if len(self.tracks) > 64:
            raise ValueError('最多支持 64 条鼓点音轨')
        if not isinstance(self.next_track_number, int) or self.next_track_number < 4:
            raise ValueError('鼓点音轨编号无效')
        ids = [track.id for track in self.tracks]
        if any(not isinstance(track, DrumTrack) or not isinstance(track.id, str)
               or not track.id or not track.id.isascii() or not track.id.replace('_','').isalnum()
               or not isinstance(track.name, str) or not track.name.strip()
               or track.sound not in DRUM_VOICES for track in self.tracks):
            raise ValueError('鼓点音轨必须具有有效 ID、名称与鼓声类型')
        if len(ids) != len(set(ids)) or set(self.hits) != set(ids):
            raise ValueError('鼓点音轨 ID 重复，或节奏数据与音轨不匹配')
        for voice, indices in self.hits.items():
            if not isinstance(indices, list) or any(type(i) is not int or i < 0 or i >= self.steps for i in indices):
                raise ValueError(f'{voice} 存在超出范围的步进位置')
            if len(set(indices)) != len(indices):
                raise ValueError(f'{voice} 存在重复的鼓点位置')

    def to_dict(self) -> dict:
        """v2 adds user-manageable rows; v1 files are still accepted on load."""
        self.validate()
        return {'format': 'melody-drum', 'version': 2, **asdict(self)}

    @classmethod
    def from_dict(cls, data: dict) -> 'DrumPattern':
        if data.get('format') != 'melody-drum' or data.get('version') not in (1, 2):
            raise ValueError('不支持的鼓点格式或版本')
        if data['version'] == 1:
            # Old fixed three-row files remain usable without modification.
            obj = cls(str(data['title']), int(data['bpm']), int(data['bars']), str(data['kit']),
                      {v: list(data['hits'].get(v, [])) for v in DRUM_VOICES})
        else:
            tracks = [DrumTrack(str(t['id']), str(t['name']), str(t['sound']))
                      for t in data['tracks']]
            obj = cls(str(data['title']), int(data['bpm']), int(data['bars']), str(data['kit']),
                      {k: list(v) for k, v in data['hits'].items()}, tracks,
                      int(data.get('next_track_number', 4)))
        obj.validate()
        return obj

    def save(self, path: str | Path) -> Path:
        self.validate()
        path = Path(path)
        if path.suffix.lower() != '.drum':
            raise ValueError('鼓点必须保存为 .drum')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return path

    @classmethod
    def load(cls, path: str | Path) -> 'DrumPattern':
        return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))

    def toggle(self, track_id: str, step: int) -> None:
        if track_id not in self.hits or not 0 <= step < self.steps:
            raise ValueError('无效鼓声部或步进位置')
        if step in self.hits[track_id]:
            self.hits[track_id].remove(step)
        else:
            self.hits[track_id].append(step)
        self.hits[track_id].sort()

    def add_track(self, sound: str = 'kick') -> DrumTrack:
        if sound not in DRUM_VOICES:
            raise ValueError('新增鼓点音轨的音色无效')
        if len(self.tracks) >= 64:
            raise ValueError('最多支持 64 条鼓点音轨')
        number = self.next_track_number
        while f'track_{number}' in self.hits:
            number += 1
        new = DrumTrack(f'track_{number}', f'新建鼓点 {number}', sound)
        self.tracks.append(new)
        self.hits[new.id] = []
        self.next_track_number = number + 1
        self.validate()
        return new

    def rename_track(self, track_id: str, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError('音轨名称不能为空')
        self.track(track_id).name = name
        self.validate()

    def set_track_sound(self, track_id: str, sound: str) -> None:
        if sound not in DRUM_VOICES:
            raise ValueError('仅支持底鼓、军鼓和踩镲三类鼓声')
        self.track(track_id).sound = sound
        self.validate()

    def remove_track(self, track_id: str) -> None:
        self.track(track_id)  # Raise before mutating on invalid ID.
        self.tracks = [t for t in self.tracks if t.id != track_id]
        del self.hits[track_id]
        self.validate()

    def track(self, track_id: str) -> DrumTrack:
        for track in self.tracks:
            if track.id == track_id:
                return track
        raise ValueError(f'不存在的鼓点音轨：{track_id}')

    def resize_bars(self, bars: int) -> None:
        if not 1 <= bars <= 64:
            raise ValueError('小节数必须是 1–64')
        self.bars = bars
        for track_id in self.hits:
            self.hits[track_id] = [i for i in self.hits[track_id] if i < self.steps]


def default_drum_pattern(title: str = '新鼓点', kit: str = 'acoustic') -> DrumPattern:
    """New drum files start with Kick/Snare/Hi-hat rows, all silent."""
    p = DrumPattern(title=title, kit=kit)
    p.validate()
    return p


def sample_drum_pattern(title: str = '节奏示例', kit: str = 'acoustic') -> DrumPattern:
    """An explicit demonstration beat; never used by New File actions."""
    p = default_drum_pattern(title=title, kit=kit)
    p.hits.update({
        'kick': [0, 8, 16, 24],
        'snare': [4, 12, 20, 28],
        'hihat': list(range(0, 32, 2)),
    })
    p.validate()
    return p


def render_drum_hit(voice: str, kit: str, duration: float = .25, sr: int = 22050) -> np.ndarray:
    """Deterministic self-contained one-shot drum synthesis, no external assets."""
    if voice not in DRUM_VOICES or kit not in DRUM_KITS:
        raise ValueError('未知鼓声或音色')
    n = max(1, round(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    rng = np.random.default_rng({'kick': 10, 'snare': 20, 'hihat': 30}[voice])
    noise = rng.standard_normal(n)
    if voice == 'kick':
        freq = (155 if kit == 'electronic' else 135) * np.exp(-t * 36) + (46 if kit == 'electronic' else 52)
        phase = np.cumsum(freq) * (2 * np.pi / sr)
        wave = np.sin(phase) * np.exp(-t * (9 if kit == 'electronic' else 15))
        if kit == 'gameboy':
            wave = np.where(wave >= 0, 1, -1) * np.exp(-t * 20)
    elif voice == 'snare':
        if kit == 'gameboy':
            stepped = np.repeat(noise[::8], 8)[:n]
            wave = np.sign(stepped + .16 * np.sin(2*np.pi*205*t)) * np.exp(-t*27)
        else:
            decay = 16 if kit == 'electronic' else 22
            wave = (.78*noise + .26*np.sin(2*np.pi*(175 if kit == 'electronic' else 205)*t)) * np.exp(-t*decay)
    else:
        # Differentiated high-frequency noise, a compact closed hat.
        high = noise - np.convolve(noise, np.ones(16) / 16, mode='same')
        if kit == 'gameboy':
            wave = np.sign(np.repeat(high[::5], 5)[:n]) * np.exp(-t*58)
        else:
            wave = high * np.exp(-t * (54 if kit == 'electronic' else 68))
    attack = np.minimum(1., t / .002)
    return (.28 * wave * attack).astype(np.float32)


def drum_midi(pattern: DrumPattern):
    """General MIDI channel 10 drum instrument (36/38/42)."""
    import pretty_midi
    pattern.validate()
    pm = pretty_midi.PrettyMIDI(initial_tempo=pattern.bpm)
    try:
        pattern.title.encode('latin-1')
        midi_name=pattern.title
    except UnicodeEncodeError:
        midi_name='Drum Pattern'
    inst = pretty_midi.Instrument(program=0, is_drum=True, name=f'{midi_name} | {pattern.kit}')
    for track in pattern.tracks:
        pitch = DRUM_VOICES[track.sound]
        for step in pattern.hits[track.id]:
            start = step / 4 * 60 / pattern.bpm
            inst.notes.append(pretty_midi.Note(velocity=105 if track.sound=='kick' else 96,
                              pitch=pitch, start=start, end=start+.12))
    pm.instruments.append(inst)
    return pm


def render_drum_pattern(pattern: DrumPattern, sr: int = 22050) -> np.ndarray:
    pattern.validate()
    duration = pattern.beats * 60 / pattern.bpm
    audio = np.zeros(round((duration+.3)*sr), dtype=np.float32)
    for track in pattern.tracks:
        hit = render_drum_hit(track.sound,pattern.kit,sr=sr)
        for step in pattern.hits[track.id]:
            st=round((step/4)*60/pattern.bpm*sr)
            n=min(len(hit),len(audio)-st)
            audio[st:st+n]+=hit[:n]
    peak=float(np.max(np.abs(audio)))
    if peak>.96:audio*=.96/peak
    return audio


def export_drum_midi(pattern: DrumPattern, path: str | Path) -> Path:
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    drum_midi(pattern).write(str(p))
    return p


def export_drum_audio(pattern: DrumPattern, path: str | Path) -> Path:
    from .audio import _convert_mp3, SAMPLE_RATE
    import soundfile as sf
    import tempfile
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix.lower() not in ('.wav','.mp3'):
        raise ValueError('鼓点输出需要 .wav 或 .mp3')
    audio=render_drum_pattern(pattern,SAMPLE_RATE)
    if p.suffix.lower()=='.wav':
        sf.write(p,audio,SAMPLE_RATE,subtype='PCM_16')
    else:
        with tempfile.TemporaryDirectory() as d:
            wav=Path(d)/'drum.wav'
            sf.write(wav,audio,SAMPLE_RATE,subtype='PCM_16')
            _convert_mp3(wav,p)
    return p
