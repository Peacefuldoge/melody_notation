"""Offline preview synth + optional proper SF2 soundfont rendering.

The built-in synth is intentionally lightweight, but v0.4.3 makes it less
"toy-like" by adding gentler envelopes, mild body resonance, a short ambience
reverb, and more instrument-specific harmonic shapes.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
import soundfile as sf
from .core import Score, timeline_events
from .midi import INSTRUMENTS, export_midi

SAMPLE_RATE = 22050


def _adsr(duration: float, sr: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    n = max(1, int(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    env = np.ones(n, dtype=np.float64) * sustain
    a = 0
    if attack > 0:
        a = min(n, max(1, int(attack * sr)))
        env[:a] = np.linspace(0.0, 1.0, a, endpoint=False)
    d = max(1, int(decay * sr))
    if a < n:
        end = min(n, a + d)
        env[a:end] = np.linspace(1.0, sustain, end - a, endpoint=False)
    if release > 0:
        r = min(n, max(1, int(release * sr)))
        start = max(0, n - r)
        env[start:] *= np.linspace(1.0, 0.0, n - start, endpoint=True)
    return env



def _performance_envelope(held: float, sr: int, attack: float, decay: float,
                          sustain: float, release: float, damping: float = 0.) -> np.ndarray:
    """Note-on, note-off and natural decay are separate musical events.

    The old percussive patch used sustain=0 in an ADSR with a 70 ms decay:
    its piano/guitar notes became silent long before their written duration.
    This envelope keeps the voice alive while the note is held and appends a
    short, smooth release, so consecutive notes overlap without changing timing.
    """
    hold_n=max(1,round(max(0.,held)*sr))
    # Short ornaments get a shorter release so trills remain intelligible.
    release=min(release,max(.055,.10+.45*held))
    rel_n=max(1,round(release*sr))
    held_env=np.full(hold_n,sustain,dtype=np.float64)
    a=min(hold_n,max(1,round(attack*sr)))
    held_env[:a]=np.linspace(0.,1.,a,endpoint=False)
    d=min(hold_n-a,max(0,round(decay*sr)))
    if d:
        held_env[a:a+d]=np.linspace(1.,sustain,d,endpoint=False)
    if damping:
        held_env*=np.exp(-damping*np.arange(hold_n,dtype=np.float64)/sr)
    # Exponential note-off with a zero endpoint (no sudden sample cut).
    tail=held_env[-1]*np.exp(-6.*(np.arange(1,rel_n+1)/rel_n))
    tail[-1]=0.
    return np.concatenate((held_env,tail))

def _one_pole_lowpass(x: np.ndarray, cutoff_hz: float, sr: int) -> np.ndarray:
    cutoff_hz = max(40.0, min(cutoff_hz, sr * 0.45))
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff_hz / sr)
    y = np.empty_like(x, dtype=np.float64)
    prev = 0.0
    for i, v in enumerate(x.astype(np.float64, copy=False)):
        prev = prev + alpha * (v - prev)
        y[i] = prev
    return y


def _comb_reverb(x: np.ndarray, sr: int, mix: float = 0.12) -> np.ndarray:
    if mix <= 0:
        return x.astype(np.float32)
    wet = np.zeros_like(x, dtype=np.float64)
    for delay_ms, gain in ((29, 0.34), (41, 0.25), (53, 0.18), (71, 0.11)):
        delay = max(1, int(sr * delay_ms / 1000))
        buf = np.zeros_like(x, dtype=np.float64)
        if delay < len(x):
            buf[delay:] = x[:-delay] * gain
            wet += buf
    wet = _one_pole_lowpass(wet, 2800, sr)
    out = x.astype(np.float64) * (1.0 - mix) + wet * mix
    return out.astype(np.float32)


def _soft_clip(x: np.ndarray, drive: float = 1.3) -> np.ndarray:
    return np.tanh(x * drive) / np.tanh(drive)


def _tone(midi: int, duration: float, instrument: str, sr: int) -> np.ndarray:
    """Render a held note and its independent, short release tail.

    ``duration`` is the *note-on length*, not a sample cut-off.  The caller
    can start the next note on time while the previous note fades naturally.
    """
    duration=max(.015,float(duration))
    profiles={
        'gameboy': (.002,.018,.68,.06,.85),
        'flute': (.045,.10,.80,.18,.025),
        'clarinet': (.028,.09,.78,.16,.035),
        'violin': (.05,.13,.84,.28,.035),
        'strings': (.06,.13,.85,.30,.03),
        'music_box': (.002,.09,.47,.30,1.8),
        'guitar': (.003,.12,.60,.28,1.15),
        'piano': (.003,.14,.71,.34,.75),
    }
    attack,decay,sustain,release,damping=profiles.get(instrument,profiles['piano'])
    env=_performance_envelope(duration,sr,attack,decay,sustain,release,damping)
    n=len(env)
    t=np.arange(n,dtype=np.float64)/sr
    hz=440*2**((midi-69)/12)
    rng=np.random.default_rng((midi*1315423911+int(duration*1000))&0xFFFFFFFF)
    noise=rng.standard_normal(n)*.03

    if instrument=='gameboy':
        phase=(hz*t)%1.
        pulse=np.where(phase<.25,1.,-1.)
        wave4=np.round(np.sin(2*np.pi*phase)*7.)/7.
        wave=.78*pulse+.22*wave4
        return (wave*env*.20).astype(np.float32)

    if instrument in ('flute','clarinet'):
        vib_depth=.0012 if instrument=='flute' else .0007
        vib_rate=5.1 if instrument=='flute' else 5.6
        vibrato=vib_depth*np.sin(2*np.pi*vib_rate*t)*np.clip(t/.18,0,1)
        phase=2*np.pi*hz*(t+np.cumsum(vibrato)/sr)
        if instrument=='flute':
            wave=np.sin(phase)+.11*np.sin(2*phase)+.04*np.sin(3*phase)
            wave+=_one_pole_lowpass(noise,2400,sr)*.55*np.clip(t/.05,0,1)
        else:
            wave=np.sin(phase)+.32*np.sin(3*phase)+.18*np.sin(5*phase)
            wave+=_one_pole_lowpass(noise,1800,sr)*.20
        return _comb_reverb(_soft_clip(wave*env*.18,1.08),sr,.08)

    if instrument in ('violin','strings'):
        vibrato=.0018*np.sin(2*np.pi*5.3*t)*np.clip((t-.04)/.2,0,1)
        phase=2*np.pi*hz*(t+np.cumsum(vibrato)/sr)
        harmonics=sum(np.sin(k*phase)/(k**1.12) for k in range(1,8))
        bow=_one_pole_lowpass(noise,2200,sr)*.28
        wave=harmonics+bow
        out=_one_pole_lowpass(wave*env,4500,sr)*.17
        return _comb_reverb(_soft_clip(out,1.1),sr,.12)

    if instrument=='music_box':
        phase=2*np.pi*hz*t
        wave=(np.sin(phase)+.42*np.sin(3.99*phase)+.18*np.sin(6.01*phase)
              +.10*np.sin(8.*phase))
        return _comb_reverb(wave*env*.16,sr,.16)

    if instrument=='guitar':
        phase=2*np.pi*hz*t
        string=sum(np.sin(k*phase)/(k**1.25) for k in range(1,8))
        pluck=_one_pole_lowpass(noise,4200,sr)*np.exp(-t*32.)*1.3
        out=_one_pole_lowpass((string+pluck)*env,5200,sr)*.18
        return _comb_reverb(out,sr,.09)

    # Piano: three slightly detuned strings and a decaying hammer transient.
    strings=0.
    for detune in (0.,-.0017,.0019):
        p=2*np.pi*hz*(1.+detune)*t
        strings+=sum(np.sin(k*p+.03*k)/(k**1.33) for k in range(1,8))/3.
    hammer=_one_pole_lowpass(noise,7000,sr)*np.exp(-t*45.)*1.1
    body=.10*np.sin(2*np.pi*hz*2.01*t)+.06*np.sin(2*np.pi*hz*2.99*t)
    out=_one_pole_lowpass((strings+hammer+body)*env,5600,sr)*.18
    return _comb_reverb(_soft_clip(out,1.12),sr,.10)


_AMBIENCE = {
    'gameboy': 0.02,
    'flute': 0.10,
    'clarinet': 0.09,
    'violin': 0.12,
    'strings': 0.14,
    'music_box': 0.16,
    'guitar': 0.08,
    'piano': 0.08,
}


def synthesize(score: Score, instrument: str = 'piano', sr: int = SAMPLE_RATE, speed: float = 1.0) -> np.ndarray:
    score.validate(strict=True)
    if instrument not in INSTRUMENTS:
        raise ValueError(f"Unsupported instrument {instrument}")
    if not .25 <= speed <= 4.0:
        raise ValueError('Playback speed must be between 0.25 and 4.0')
    duration = sum(n.beats for m in score.measures for n in m) * 60 / (score.bpm * speed)
    if duration > 600:
        raise ValueError('Audio preview capped at 10 minutes')
    arr = np.zeros(int((duration + .45) * sr), dtype=np.float32)
    for t0, t1, pitch, velocity in timeline_events(score, speed=speed):
        pos = round(t0 * sr)
        sound = _tone(pitch, max(0.03, t1 - t0), instrument, sr) * (velocity / 92)
        length = min(len(sound), len(arr) - pos)
        arr[pos:pos + length] += sound[:length]
    arr = _comb_reverb(arr, sr, _AMBIENCE.get(instrument, 0.08)).astype(np.float32)
    arr = _soft_clip(arr, 1.18).astype(np.float32)
    peak = np.max(np.abs(arr)) if len(arr) else 0
    if peak > .92:
        arr *= .92 / peak
    return arr


def export_audio(score: Score, path: str | Path, instrument: str = 'piano', sf2: str | None = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() not in ('.wav', '.mp3'):
        raise ValueError('Choose a .wav or .mp3 output path')
    if sf2:
        if not shutil.which('fluidsynth'):
            raise RuntimeError('FluidSynth executable not found. Install it or omit --sf2 for preview synth.')
        if not Path(sf2).is_file():
            raise FileNotFoundError(sf2)
        with tempfile.TemporaryDirectory() as td:
            mid = export_midi(score, Path(td) / 'score.mid', instrument)
            wav = Path(td) / 'audio.wav'
            subprocess.run(['fluidsynth', '-ni', '-F', str(wav), '-r', '44100', str(sf2), str(mid)], check=True,
                           stdout=subprocess.DEVNULL)
            if p.suffix.lower() == '.wav':
                shutil.copy2(wav, p)
            else:
                _convert_mp3(wav, p)
        return p
    arr = synthesize(score, instrument)
    if p.suffix.lower() == '.wav':
        sf.write(p, arr, SAMPLE_RATE, subtype='PCM_16')
    else:
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / 'preview.wav'
            sf.write(wav, arr, SAMPLE_RATE, subtype='PCM_16')
            _convert_mp3(wav, p)
    return p


def _convert_mp3(wav: Path, mp3: Path):
    if not shutil.which('ffmpeg'):
        raise RuntimeError('MP3 export needs ffmpeg installed on PATH; WAV export works without it.')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(wav),
                    '-codec:a', 'libmp3lame', '-b:a', '192k', str(mp3)], check=True)
