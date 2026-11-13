"""Headless audio preview renderer shared by the Qt GUI and unit tests.

Musical beat speed changes without resampling the resulting wave, preserving pitch.
"""
from __future__ import annotations
from pathlib import Path
from .audio import SAMPLE_RATE, synthesize
from .arrangement import source_beats, resolve_source

def render_preview(kind, data, path, instrument, speed, output):
    """Offline preview in a worker; speed is applied to musical events, not pitch."""
    import numpy as np
    import soundfile as sf
    from .audio import _tone, _comb_reverb
    from .drums import render_drum_hit
    from .arrangement import rendered_events
    speed=float(speed)
    if kind=='jianpu':
        arr=synthesize(data,instrument,SAMPLE_RATE,speed=speed)
    elif kind=='drum':
        p=data
        duration=(p.beats*60/p.bpm)/speed
        arr=np.zeros(max(1,round((duration+.35)*SAMPLE_RATE)),dtype=np.float32)
        # hits is keyed by persistent track IDs (e.g. "track_4"), NOT drum
        # voice names.  Resolve the actual synth voice from each DrumTrack,
        # just as standalone WAV/MIDI export and multitrack mixing do.
        # Cache one-shots by sound, since several named tracks may share it.
        samples={}
        for track in p.tracks:
            indices=p.hits[track.id]
            if not indices:
                continue
            if track.sound not in samples:
                samples[track.sound]=render_drum_hit(track.sound,p.kit,sr=SAMPLE_RATE)
            hit=samples[track.sound]
            for index in indices:
                start=round((index/4*60/p.bpm)/speed*SAMPLE_RATE)
                n=min(len(hit),len(arr)-start)
                if n>0:arr[start:start+n]+=hit[:n]
    else:
        if path is None: raise ValueError('多轨工程需要先保存为 .mtrack 才能试听')
        if not Path(path).is_file():raise ValueError('请先保存多轨工程')
        events=rendered_events(data,path)
        end_beats=max((clip.start_beat+max(0.,
                         (clip.trim_end if clip.trim_end is not None
                          else source_beats(resolve_source(path,clip.source)))-clip.trim_start)
                          for t in data.tracks for clip in t.clips),default=0.)
        duration=end_beats*60/data.bpm/speed
        if duration>600:raise ValueError('试听最多支持 10 分钟')
        arr=np.zeros(max(1,round((duration+.45)*SAMPLE_RATE)),dtype=np.float32)
        for ti,st,ed,pitch,vel,voice,kit in events:
            start=round(st*60/data.bpm/speed*SAMPLE_RATE)
            seconds=(ed-st)*60/data.bpm/speed
            if voice: wave=render_drum_hit(voice,kit,sr=SAMPLE_RATE)
            else:wave=_tone(pitch,seconds,data.tracks[ti].instrument,SAMPLE_RATE)*vel/92
            n=min(len(wave),len(arr)-start)
            if n>0:arr[start:start+n]+=wave[:n]
        # A quiet shared ambience keeps independently rendered track clips
        # in the same acoustic space; the score synth already does this.
        arr=_comb_reverb(arr,SAMPLE_RATE,.09)
    if len(arr):
        peak=float(np.max(np.abs(arr)))
        if peak>.94:arr*=.94/peak
    sf.write(str(output),arr,SAMPLE_RATE,subtype='PCM_16')
    return str(output)

