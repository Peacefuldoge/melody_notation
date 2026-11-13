"""Non-destructive .mtrack arrangements with beat-locked score/drum clips.

Each clip references an existing .jianpu/.drum inside its Melody project.
Trim and reverse transform the arrangement only, never the source files.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
import pretty_midi
import soundfile as sf

from .core import parse_text, timeline_events
from .midi import INSTRUMENTS
from .audio import _tone, _comb_reverb, SAMPLE_RATE
from .drums import DrumPattern, DRUM_VOICES, render_drum_hit
from .workspace import MANIFEST


@dataclass
class Clip:
    source: str
    start_beat: float = 0.0
    trim_start: float = 0.0
    trim_end: float | None = None
    reversed: bool = False
    gain: float = 1.0


@dataclass
class Track:
    name: str
    kind: str = 'melody'  # melody or drum
    instrument: str = 'piano'
    muted: bool = False
    solo: bool = False
    clips: list[Clip] = field(default_factory=list)


@dataclass
class Arrangement:
    title: str = '新音轨工程'
    bpm: int = 120
    tracks: list[Track] = field(default_factory=list)

    def validate(self) -> None:
        if not self.title.strip() or not 20 <= self.bpm <= 400:
            raise ValueError('工程需要标题，BPM 必须为 20–400')
        if len(self.tracks) > 64:
            raise ValueError('最多支持 64 条音轨')
        for track in self.tracks:
            if not track.name.strip() or track.kind not in ('melody', 'drum'):
                raise ValueError('音轨名称或类型无效')
            if track.kind == 'melody' and track.instrument not in INSTRUMENTS:
                raise ValueError('未知音轨音色：' + track.instrument)
            for clip in track.clips:
                if (clip.start_beat < 0 or clip.trim_start < 0 or
                    (clip.trim_end is not None and clip.trim_end <= clip.trim_start) or
                    not 0 <= clip.gain <= 2):
                    raise ValueError('片段位置、裁剪范围或音量不合法')
                if Path(clip.source).is_absolute() or not clip.source.strip():
                    raise ValueError('片段来源必须使用项目内相对路径')
                ext = '.jianpu' if track.kind == 'melody' else '.drum'
                if Path(clip.source).suffix.lower() != ext:
                    raise ValueError(f'{track.name} 的片段需要 {ext} 文件')

    def to_dict(self) -> dict:
        return {'format': 'melody-mtrack', 'version': 1, **asdict(self)}

    @classmethod
    def from_dict(cls, data: dict) -> 'Arrangement':
        if data.get('format') != 'melody-mtrack' or data.get('version') != 1:
            raise ValueError('不支持的音轨工程格式或版本')
        tracks = []
        for item in data['tracks']:
            tracks.append(Track(name=item['name'], kind=item.get('kind','melody'),
                                instrument=item.get('instrument','piano'),
                                muted=bool(item.get('muted',False)),solo=bool(item.get('solo',False)),
                                clips=[Clip(**c) for c in item.get('clips',[])]))
        obj = cls(str(data['title']), int(data['bpm']), tracks)
        obj.validate()
        return obj

    def save(self, path: str | Path) -> Path:
        self.validate()
        path = Path(path)
        if path.suffix.lower() != '.mtrack':
            raise ValueError('音轨工程必须保存为 .mtrack')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return path

    @classmethod
    def load(cls, path: str | Path) -> 'Arrangement':
        return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))

    def move_track(self, index: int, delta: int) -> None:
        new = index + delta
        if not 0 <= index < len(self.tracks) or not 0 <= new < len(self.tracks):
            raise IndexError('音轨移动超出范围')
        item = self.tracks.pop(index)
        self.tracks.insert(new,item)


def find_project_root(arrangement_path: str | Path) -> Path:
    path = Path(arrangement_path).resolve()
    for folder in (path.parent, *path.parents):
        if (folder / MANIFEST).is_file():
            return folder
    return path.parent


def resolve_source(arrangement_path: str | Path, relative: str, project_root: str | Path | None = None) -> Path:
    root = Path(project_root).resolve() if project_root else find_project_root(arrangement_path)
    rel = Path(relative)
    if rel.is_absolute():
        raise ValueError('片段来源不得使用绝对路径')
    source = (root / rel).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError('片段来源必须是项目内存在的文件：'+relative)
    if source.suffix.lower() not in ('.jianpu','.drum'):
        raise ValueError('片段只能引用 .jianpu 或 .drum 文件')
    return source


def source_beats(source: Path) -> float:
    if source.suffix.lower() == '.jianpu':
        s = parse_text(source.read_text(encoding='utf-8'),strict=True)
        return sum(n.beats for bar in s.measures for n in bar)
    return DrumPattern.load(source).beats


def add_clip(arr: Arrangement, arrangement_path: str | Path, source_path: str | Path,
             track_index: int | None = None, start_beat: float = 0.,
             project_root: str | Path | None = None) -> int:
    """Add a source file as a clip; create a new track unless index specified."""
    root = Path(project_root).resolve() if project_root else find_project_root(arrangement_path)
    path = Path(source_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('只能加入项目目录内的简谱和鼓点')
    rel = str(path.relative_to(root)).replace('\\','/')
    resolve_source(arrangement_path, rel, root)
    kind = 'melody' if path.suffix.lower() == '.jianpu' else 'drum'
    if track_index is None:
        arr.tracks.append(Track(name=path.stem, kind=kind))
        track_index = len(arr.tracks)-1
    elif not 0 <= track_index < len(arr.tracks) or arr.tracks[track_index].kind != kind:
        raise ValueError('只能向同类型音轨插入片段')
    arr.tracks[track_index].clips.append(Clip(source=rel,start_beat=float(start_beat)))
    arr.validate()
    return track_index


def rendered_events(arr: Arrangement, arrangement_path: str | Path, project_root: str | Path | None = None):
    """Return (track index, beat start, beat end, midi pitch, velocity, voice|None, kit).

    A reversed clip reverses note/hit chronology (not PCM sample polarity).
    Different source tempos are beat-aligned to the arrangement BPM.
    """
    arr.validate()
    solo = any(t.solo for t in arr.tracks)
    cache = {}
    result = []
    for ti, track in enumerate(arr.tracks):
        if track.muted or (solo and not track.solo):
            continue
        for clip in track.clips:
            source = resolve_source(arrangement_path,clip.source,project_root)
            if source not in cache:
                if track.kind == 'melody':
                    score = parse_text(source.read_text(encoding='utf-8'),strict=True)
                    beats = sum(n.beats for bar in score.measures for n in bar)
                    events = [(start * score.bpm / 60, end * score.bpm / 60,pitch,vel,None,'')
                              for start,end,pitch,vel in timeline_events(score)]
                else:
                    drum = DrumPattern.load(source)
                    beats = drum.beats
                    events = [(i/4, i/4 + .22, DRUM_VOICES[track.sound], 100, track.sound, drum.kit)
                              for track in drum.tracks for i in drum.hits[track.id]]
                cache[source] = (beats, events)
            beats, events = cache[source]
            end = beats if clip.trim_end is None else clip.trim_end
            if end > beats + 1e-6 or clip.trim_start >= end:
                raise ValueError(f'{source.name} 的裁剪超过音频长度（{beats:g} 拍）')
            for st, ed, pitch, velocity, voice, kit in events:
                trimmed_start=max(st,clip.trim_start)
                trimmed_end=min(ed,end)
                if trimmed_end <= trimmed_start:continue
                if clip.reversed:
                    local_start = end - trimmed_end
                    local_end = end - trimmed_start
                else:
                    local_start = trimmed_start - clip.trim_start
                    local_end = trimmed_end - clip.trim_start
                result.append((ti,clip.start_beat+local_start,clip.start_beat+local_end,
                               pitch,min(127,round(velocity*clip.gain)),voice,kit))
    return sorted(result,key=lambda e:(e[1],e[0],e[3]))


def make_arrangement_midi(arr: Arrangement, path: str | Path) -> pretty_midi.PrettyMIDI:
    pm = pretty_midi.PrettyMIDI(initial_tempo=arr.bpm)
    events = rendered_events(arr,path)
    for index, track in enumerate(arr.tracks):
        # mido uses latin-1 for MIDI track-name meta events. Preserve Unicode
        # names in .mtrack JSON, but use a portable fallback for MIDI export.
        try:
            track.name.encode('latin-1')
            midi_name=track.name
        except UnicodeEncodeError:
            midi_name=f'Track {index+1} - {track.kind}'
        if track.kind=='drum':
            inst=pretty_midi.Instrument(program=0,is_drum=True,name=midi_name)
        else:
            inst=pretty_midi.Instrument(program=INSTRUMENTS[track.instrument],name=midi_name)
        for ti,st,ed,pitch,vel,_,_ in events:
            if ti!=index or vel==0:continue
            inst.notes.append(pretty_midi.Note(velocity=max(1,vel),pitch=pitch,
                               start=st*60/arr.bpm,end=max(ed,st+.015)*60/arr.bpm))
        pm.instruments.append(inst)
    return pm


def export_arrangement_midi(arr: Arrangement, arrangement_path: str | Path, output: str | Path) -> Path:
    target=Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    make_arrangement_midi(arr,arrangement_path).write(str(target))
    return target


def synthesize_arrangement(arr: Arrangement, arrangement_path: str | Path,
                           sr: int = SAMPLE_RATE) -> np.ndarray:
    events=rendered_events(arr,arrangement_path)
    # Include silent clips in the composition duration; silence is still timing.
    end_beats=0.
    for track in arr.tracks:
        for clip in track.clips:
            source=resolve_source(arrangement_path,clip.source)
            end=source_beats(source) if clip.trim_end is None else clip.trim_end
            end_beats=max(end_beats,clip.start_beat+end-clip.trim_start)
    duration=end_beats*60/arr.bpm
    if duration>600:
        raise ValueError('预览音频最长支持 10 分钟')
    audio=np.zeros(max(1,round((duration+.45)*sr)),dtype=np.float32)
    for ti,st,ed,pitch,vel,voice,kit in events:
        start=round(st*60/arr.bpm*sr)
        if voice:
            sample=render_drum_hit(voice,kit,sr=sr)
        else:
            inst=arr.tracks[ti].instrument
            sample=_tone(pitch,(ed-st)*60/arr.bpm,inst,sr)
        sample=sample*(vel/100)
        n=min(len(sample),len(audio)-start)
        if n>0: audio[start:start+n]+=sample[:n]
    audio=_comb_reverb(audio,sr,.09)
    peak=float(np.max(np.abs(audio)))
    if peak>.96: audio*=.96/peak
    return audio


def export_arrangement_audio(arr: Arrangement, arrangement_path: str | Path, output: str | Path) -> Path:
    out=Path(output)
    if out.suffix.lower() not in ('.wav','.mp3'):
        raise ValueError('支持 WAV 或 MP3 输出')
    out.parent.mkdir(parents=True,exist_ok=True)
    audio=synthesize_arrangement(arr,arrangement_path)
    if out.suffix.lower()=='.wav':
        sf.write(out,audio,SAMPLE_RATE,subtype='PCM_16')
    else:
        if not shutil.which('ffmpeg'):
            raise RuntimeError('MP3 导出需要安装 FFmpeg')
        with tempfile.TemporaryDirectory() as folder:
            wav=Path(folder)/'mix.wav'
            sf.write(wav,audio,SAMPLE_RATE,subtype='PCM_16')
            subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(wav),
                            '-codec:a','libmp3lame','-b:a','192k',str(out)],check=True)
    return out
