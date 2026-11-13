"""Codex MCP tools. Run with python -m melody_notation.mcp_server."""
from __future__ import annotations
from pathlib import Path
import os
import json
# MCP Python SDK 2.x only; legacy SDK 1.x is intentionally unsupported.
from mcp.server.mcpserver import MCPServer

from .core import Score, parse_text, text_from_score
from .editing import update_note, add_slur as do_add_slur, clear_slur as do_clear_slur, insert_note as do_insert_note, delete_note as do_delete_note
from .audio import export_audio as do_audio
from .midi import INSTRUMENTS, export_midi as do_midi
from .png import export_png as do_png
from .vision import transcribe_image as do_vision
from .harmony import TOPICS as HARMONY_TOPICS, read_topic as read_harmony_topic
from .drums import (DRUM_KITS, DRUM_VOICES, default_drum_pattern, DrumPattern,
                    export_drum_midi as do_drum_midi, export_drum_audio as do_drum_audio)
from .arrangement import (Arrangement, add_clip as add_music_clip, rendered_events,
                          resolve_source as resolve_clip_source,
                          export_arrangement_midi as do_arr_midi,
                          export_arrangement_audio as do_arr_audio)

mcp = MCPServer('Melody Notation', instructions='Edit numbered notation in a project workspace, validate every bar, and render MIDI, audio or PNG. For chord/harmony tasks, first call list_harmony_topics and read_harmony_guide. Chord moods are contextual. The .jianpu editor is monophonic; .mtrack arrangements mix multiple score and drum tracks. Vision OCR is uncertain; return a draft and request human review. Never overwrite user files silently.')
ROOT = Path(os.environ.get('MELODY_WORKSPACE') or os.getcwd()).resolve()


def file_path(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError('File path must stay inside MELODY_WORKSPACE')
    return p


def load_score(path: str) -> Score:
    p = file_path(path)
    if p.suffix.lower() == '.json':
        return Score.from_dict(json.loads(p.read_text(encoding='utf-8')), strict=False)
    return parse_text(p.read_text(encoding='utf-8'),strict=False)


def protected_save(p: Path, content: str, overwrite: bool) -> None:
    if p.exists() and not overwrite:
        raise FileExistsError(f'{p} already exists. Set overwrite=true only after confirmation.')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content,encoding='utf-8')

@mcp.tool()
def list_instruments() -> dict[str,int]:
    """List sound presets and their nearest GM patches (gameboy is an approximation)."""
    return INSTRUMENTS

@mcp.tool()
def list_harmony_topics() -> dict[str, str]:
    """List built-in read-only music theory/harmony topics for an AI composing assistant."""
    return dict(HARMONY_TOPICS)

@mcp.tool()
def read_harmony_guide(topic: str = 'overview') -> dict[str, str]:
    """Read chord spellings, contextual emotional colors, progression templates or harmonization workflow.
    Allowed topics: overview, chords, progressions, workflow, sources.
    This is a knowledge reference, not a multitrack audio-generation operation.
    """
    return {'topic': topic, 'content': read_harmony_topic(topic)}

@mcp.tool()
def create_score(text: str, path: str = 'score.jianpu', overwrite: bool = False) -> dict:
    """Create a validated editable .jianpu score from a text header + bar lines.
    Example: title: Demo\\nkey: C\\ntime: 4/4\\nbpm: 120\\nnotes:\\n| 1 2 3 4 | 5 - - - |
    """
    score = parse_text(text)
    p = file_path(path)
    protected_save(p, text_from_score(score), overwrite)
    return {'path':str(p),'measures':len(score.measures),'issues':[]}

@mcp.tool()
def inspect_score(path: str) -> dict:
    """Read and validate a .jianpu text or score JSON file."""
    score = load_score(path)
    return {'score':score.to_dict(),'text':text_from_score(score),'issues':score.validate()}

@mcp.tool()
def replace_measure(path: str, measure_number: int, notes: str, overwrite: bool = False) -> dict:
    """Replace one 1-indexed measure. Requires overwrite=true; changes source file."""
    if not overwrite: raise ValueError('Set overwrite=true after review before changing a score')
    score = load_score(path)
    if not 1<=measure_number<=len(score.measures): raise IndexError('measure_number out of range')
    # Validate the new bar using the current meter.
    raw = (f'title: {score.title}\nkey: {score.key}\ntime: {score.numerator}/{score.denominator}\n'
           f'bpm: {score.bpm}\nnotes:\n| {notes} |')
    bar = parse_text(raw).measures[0]
    score.measures[measure_number-1] = bar
    p = file_path(path)
    if p.suffix.lower()=='.json': score.save_json(p)
    else: protected_save(p,text_from_score(score),True)
    return {'path':str(p),'measure_number':measure_number,'notes':notes}

def write_score(path: str, score: Score) -> str:
    """Persist a score, including temporary bar-duration errors during iterative editing."""
    p = file_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == '.json':
        p.write_text(json.dumps(score.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        protected_save(p, text_from_score(score), True)
    return str(p)

@mcp.tool()
def edit_note(path: str, measure_number: int, note_number: int,
              degree: int | None = None, octave: int | None = None,
              beats: float | None = None, accidental: int | None = None,
              ornament: str | None = None, overwrite: bool = False) -> dict:
    """Change one note (1-indexed) without touching others. Requires overwrite=true.
    degree=0 means rest; octave=-3..3; ornament=tr/mordent/lower_mordent/turn/staccato/accent/tenuto/tremolo/empty.
    Incomplete bars are saved as drafts; check issues before exporting.
    """
    if not overwrite: raise ValueError('Set overwrite=true only after approval to modify the score')
    score = update_note(load_score(path), measure_number, note_number,
                        degree=degree, octave=octave, beats=beats, accidental=accidental, ornament=ornament)
    return {'path':write_score(path,score),'issues':score.validate()}

@mcp.tool()
def create_slur(path: str, start_measure: int, start_note: int,
                end_measure: int, end_note: int, overwrite: bool = False) -> dict:
    """Draw a notation slur across a note range, including across measures.
    Slur is a phrase mark; it does not merge MIDI notes or increase their duration.
    """
    if not overwrite: raise ValueError('Set overwrite=true only after approval to modify the score')
    score = do_add_slur(load_score(path),start_measure,start_note,end_measure,end_note)
    return {'path':write_score(path,score),'issues':score.validate()}

@mcp.tool()
def remove_slur(path: str, measure_number: int, note_number: int, overwrite: bool = False) -> dict:
    """Remove the slur containing one selected note; preserve all unrelated slurs."""
    if not overwrite: raise ValueError('Set overwrite=true only after approval to modify the score')
    score = do_clear_slur(load_score(path),measure_number,note_number)
    return {'path':write_score(path,score),'issues':score.validate()}

@mcp.tool()
def insert_note(path: str, measure_number: int, insert_before: int,
                degree: int = 1, beats: float = 1, overwrite: bool = False) -> dict:
    """Insert an event before a one-indexed position (or at end=length+1)."""
    if not overwrite: raise ValueError('Set overwrite=true only after approval to modify the score')
    score=do_insert_note(load_score(path),measure_number,insert_before,degree,beats)
    return {'path':write_score(path,score),'issues':score.validate()}

@mcp.tool()
def delete_note(path: str, measure_number: int, note_number: int, overwrite: bool = False) -> dict:
    """Delete an event, requiring slur endpoint removal first when applicable."""
    if not overwrite: raise ValueError('Set overwrite=true only after approval to modify the score')
    score=do_delete_note(load_score(path),measure_number,note_number)
    return {'path':write_score(path,score),'issues':score.validate()}

@mcp.tool()
def export_midi(path: str, output: str = 'output/score.mid', instrument: str = 'piano', overwrite: bool = False) -> str:
    """Render a score into a MIDI file with named instrument/program."""
    p=file_path(output)
    if p.exists() and not overwrite: raise FileExistsError('Output exists; set overwrite=true')
    return str(do_midi(load_score(path), p, instrument))

@mcp.tool()
def export_audio(path: str, output: str = 'output/score.wav', instrument: str = 'piano', sf2: str = '', overwrite: bool = False) -> str:
    """Render audio WAV/MP3; optional sf2 file for higher-quality FluidSynth playback."""
    p=file_path(output)
    if p.exists() and not overwrite: raise FileExistsError('Output exists; set overwrite=true')
    soundfont = str(file_path(sf2)) if sf2 else None
    return str(do_audio(load_score(path),p,instrument,soundfont))

@mcp.tool()
def export_png(path: str, output: str = 'output/score.png', bars_per_row: int = 4, overwrite: bool = False) -> str:
    """Render a basic printable image of the numbered notation."""
    p=file_path(output)
    if p.exists() and not overwrite: raise FileExistsError('Output exists; set overwrite=true')
    return str(do_png(load_score(path),p,bars_per_row))

@mcp.tool()
def transcribe_image(image: str, output: str = 'output/vision_draft.jianpu', model: str = '', overwrite: bool = False) -> dict:
    """VISION-BETA. Extract editable jianpu from an image with a vision LLM.
    Requires configured API key or vision-compatible local endpoint. Humans must check.
    """
    p=file_path(output)
    if p.exists() and not overwrite: raise FileExistsError('Output exists; set overwrite=true')
    score,uncertainty=do_vision(file_path(image),model=model or None)
    protected_save(p,text_from_score(score),overwrite)
    return {'draft':str(p),'issues':score.validate(),'uncertainty':uncertainty,
            'warning':'Visual notation extraction is fallible. Verify every measure against the image.'}


def load_arrangement_scoped(path: str):
    """Prevent an arrangement inside MCP workspace from reading outside it."""
    p=file_path(path)
    arr=Arrangement.load(p)
    for track in arr.tracks:
        for clip in track.clips:
            source=resolve_clip_source(p,clip.source)
            if not source.is_relative_to(ROOT):
                raise ValueError('Arrangement clip references a file outside MELODY_WORKSPACE')
    return p,arr


# ---- v0.3 multi-track and drum editing; requires same workspace permissions ----
@mcp.tool()
def list_drum_kits() -> dict:
    """Three local drum kits plus GM percussion key numbers."""
    return {'kits':list(DRUM_KITS),'voices':DRUM_VOICES}

@mcp.tool()
def create_drum_pattern(path: str, title: str = '新鼓点',
                        kit: str = 'acoustic', bars: int = 2,
                        bpm: int = 120, overwrite: bool = False) -> dict:
    """Create an editable 16-step-per-bar .drum file, 3 drum voices, 3 kits."""
    p=file_path(path)
    if p.suffix.lower()!='.drum':raise ValueError('Use a .drum path')
    pattern=default_drum_pattern(title=title,kit=kit)
    pattern.resize_bars(bars);pattern.bpm=bpm;pattern.validate()
    protected_save(p,json.dumps(pattern.to_dict(),ensure_ascii=False,indent=2),overwrite)
    return {'path':str(p),'bars':bars,'kit':kit,'voices':DRUM_VOICES}

@mcp.tool()
def inspect_drum_pattern(path: str) -> dict:
    """Read a drum pattern without modifying it."""
    return DrumPattern.load(file_path(path)).to_dict()

@mcp.tool()
def toggle_drum_hit(path: str, voice: str, step: int, overwrite: bool = False) -> dict:
    """Toggle a step by stable drum track ID (legacy: kick/snare/hihat). Requires approval."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    p=file_path(path);d=DrumPattern.load(p)
    d.toggle(voice,step);d.save(p)
    return {'path':str(p),'voice':voice,'step':step,'active':step in d.hits[voice]}

@mcp.tool()
def add_drum_track(path: str, sound: str = 'kick', overwrite: bool = False) -> dict:
    """Add an editable named drum row; sound is kick/snare/hihat. Approval required."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    p=file_path(path);pattern=DrumPattern.load(p)
    track=pattern.add_track(sound)
    pattern.save(p)
    return {'path':str(p),'track_id':track.id,'name':track.name,'sound':track.sound}

@mcp.tool()
def rename_drum_track(path: str, track_id: str, name: str, overwrite: bool = False) -> dict:
    """Rename a drum row, preserving its notes and sound. Approval required."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    p=file_path(path);pattern=DrumPattern.load(p)
    pattern.rename_track(track_id,name)
    pattern.save(p)
    return {'path':str(p),'track_id':track_id,'name':pattern.track(track_id).name}

@mcp.tool()
def set_drum_track_sound(path: str, track_id: str, sound: str,
                         overwrite: bool = False) -> dict:
    """Choose kick/snare/hihat for one existing drum row. Approval required."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    p=file_path(path);pattern=DrumPattern.load(p)
    pattern.set_track_sound(track_id,sound)
    pattern.save(p)
    return {'path':str(p),'track_id':track_id,'sound':sound}

@mcp.tool()
def remove_drum_track(path: str, track_id: str, overwrite: bool = False) -> dict:
    """Permanently delete a drum row and its hits. Approval required."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    p=file_path(path);pattern=DrumPattern.load(p)
    pattern.remove_track(track_id)
    pattern.save(p)
    return {'path':str(p),'track_id':track_id,'tracks_remaining':len(pattern.tracks)}

@mcp.tool()
def create_arrangement(path: str, title: str = '新音轨工程',
                       bpm: int = 120, overwrite: bool = False) -> dict:
    """Create a portable empty .mtrack arrangement. Add source clips separately."""
    p=file_path(path)
    if p.suffix.lower()!='.mtrack':raise ValueError('Use a .mtrack path')
    arr=Arrangement(title=title,bpm=bpm);arr.validate()
    protected_save(p,json.dumps(arr.to_dict(),ensure_ascii=False,indent=2),overwrite)
    return {'path':str(p),'title':title,'tracks':0}

@mcp.tool()
def inspect_arrangement(path: str) -> dict:
    """Inspect all tracks/clips and the current audible event count."""
    p,arr=load_arrangement_scoped(path)
    return {'arrangement':arr.to_dict(),'audible_events':len(rendered_events(arr,p))}

@mcp.tool()
def add_arrangement_clip(path: str, source: str,
                         track_index: int = -1, start_beat: float = 0,
                         overwrite: bool = False) -> dict:
    """Add existing project .jianpu/.drum. track_index=-1 creates a track. Requires approval."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    from .arrangement import find_project_root
    p,arr=load_arrangement_scoped(path)
    target=file_path(source)
    index=add_music_clip(arr,p,target,track_index=None if track_index == -1 else track_index,
                         start_beat=start_beat,project_root=find_project_root(p))
    arr.save(p)
    return {'path':str(p),'track_index':index,'clip_index':len(arr.tracks[index].clips)-1}

@mcp.tool()
def edit_arrangement_clip(path: str, track_index: int, clip_index: int,
                         start_beat: float | None = None,
                         trim_start: float | None = None,
                         trim_end: float | None = None,
                         clear_trim_end: bool = False,
                         reversed: bool | None = None,
                         gain: float | None = None,
                         instrument: str | None = None,
                         overwrite: bool = False) -> dict:
    """Non-destructively trim, reverse or reposition one clip (0-indexed). Requires approval."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    from .arrangement import source_beats, resolve_source
    p,arr=load_arrangement_scoped(path)
    track=arr.tracks[track_index];clip=track.clips[clip_index]
    if start_beat is not None:clip.start_beat=start_beat
    if trim_start is not None:clip.trim_start=trim_start
    if clear_trim_end:clip.trim_end=None
    elif trim_end is not None:clip.trim_end=trim_end
    if reversed is not None:clip.reversed=reversed
    if gain is not None:clip.gain=gain
    if instrument is not None:track.instrument=instrument
    arr.validate()
    length=source_beats(resolve_source(p,clip.source))
    if clip.trim_start >= length or (clip.trim_end is not None and clip.trim_end>length):
        raise ValueError('Clip trim exceeds source duration')
    arr.save(p)
    return {'path':str(p),'clip':vars(clip),'track':track.name}

@mcp.tool()
def reorder_arrangement_track(path: str, track_index: int, delta: int,
                              overwrite: bool = False) -> dict:
    """Reorder a track up/down by delta=-1 or +1; requires approval."""
    if not overwrite:raise ValueError('Set overwrite=true only after approval')
    if delta not in (-1,1):raise ValueError('delta must be -1 or +1')
    p,arr=load_arrangement_scoped(path)
    arr.move_track(track_index,delta);arr.save(p)
    return {'path':str(p),'new_index':track_index+delta}

@mcp.tool()
def export_multitrack_midi(path: str, output: str, overwrite: bool = False) -> str:
    """Export all tracks as multi-instrument GM MIDI; percussion channel 10."""
    p=file_path(output)
    if p.exists() and not overwrite:raise FileExistsError('Output exists; approval needed')
    source,arr=load_arrangement_scoped(path)
    return str(do_arr_midi(arr,source,p))

@mcp.tool()
def export_multitrack_audio(path: str, output: str, overwrite: bool = False) -> str:
    """Mix arrangement into WAV or MP3 with the built-in local synth."""
    p=file_path(output)
    if p.exists() and not overwrite:raise FileExistsError('Output exists; approval needed')
    source,arr=load_arrangement_scoped(path)
    return str(do_arr_audio(arr,source,p))

@mcp.tool()
def export_drum_pattern(path: str, output: str, overwrite: bool = False) -> str:
    """Export a .drum pattern as WAV/MP3/MIDI."""
    p=file_path(output)
    if p.exists() and not overwrite:raise FileExistsError('Output exists; approval needed')
    drum=DrumPattern.load(file_path(path))
    if p.suffix.lower()=='.mid':return str(do_drum_midi(drum,p))
    return str(do_drum_audio(drum,p))

def main():
    mcp.run(transport='stdio')

if __name__ == '__main__': main()
