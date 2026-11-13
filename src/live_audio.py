"""Low-latency, polyphonic live monitor for computer/MIDI keyboard input.

Optional PortAudio backend (sounddevice). The score model and MIDI capture remain
usable even when the machine has no audio output device.
"""
from __future__ import annotations

from threading import RLock
from .midi import INSTRUMENTS
import math
import numpy as np


class LiveAudioSynth:
    RATE = 44100

    def __init__(self):
        self._stream = None
        self._lock = RLock()
        self._voices = {}
        self.instrument = 'piano'
        self.volume = 0.8
        self.error = None

    def _ensure_stream(self):
        if self._stream is not None:
            return True
        try:
            import sounddevice as sd
            stream = None
            last_error = None
            for channels in (2, 1):
                try:
                    stream = sd.OutputStream(samplerate=self.RATE, channels=channels,
                          blocksize=256, dtype='float32', latency='low',
                          callback=self._render)
                    stream.start()
                    break
                except Exception as exc:
                    last_error = exc
                    if stream is not None:
                        try:stream.close()
                        except Exception:pass
                    stream = None
            if stream is None:
                raise RuntimeError(f'默认音频输出设备无法启动：{last_error}')
            self._stream = stream
            self.error = None
            return True
        except Exception as exc:
            self.error = f'实时监听不可用：{exc}'
            return False

    def note_on(self, source: str, pitch: int, velocity: int = 90):
        if self.instrument not in INSTRUMENTS:
            raise ValueError(f'Unsupported live instrument: {self.instrument}')
        audible = self._ensure_stream()
        with self._lock:
            self._voices[(source, pitch)] = {
                'pitch': pitch, 'phase': 0., 'level': 0.,
                'velocity': max(1, min(127, velocity))/127.,
                'instrument': self.instrument, 'released': False}
        return audible

    def note_off(self, source: str, pitch: int):
        with self._lock:
            voice = self._voices.get((source, pitch))
            if voice is not None: voice['released'] = True

    def all_off(self):
        with self._lock:
            for voice in self._voices.values():
                voice['released'] = True

    def stop(self):
        self.all_off()
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop(); stream.close()
            except Exception:
                pass
        with self._lock:
            self._voices.clear()

    def _render(self, outdata, frames, time_info, status):
        t = np.arange(frames, dtype=np.float64)
        mix = np.zeros(frames, dtype=np.float64)
        finished = []
        with self._lock:
            for key, voice in self._voices.items():
                pitch = voice['pitch']
                freq = 440.*(2.**((pitch-69)/12))
                phase = voice['phase'] + (t * (2*math.pi*freq/self.RATE))
                # Capture the instrument at note-on to avoid timbre changing
                # abruptly while another note is still releasing.
                tone = voice.get('instrument', self.instrument)
                if tone == 'gameboy':
                    wave = .70*np.where(np.sin(phase)>0,1.,-1.) + .30*np.sin(phase)
                elif tone == 'flute':
                    wave = .95*np.sin(phase) + .05*np.sin(2*phase)
                elif tone == 'clarinet':
                    wave = .76*np.sin(phase) + .18*np.sin(3*phase) + .06*np.sin(5*phase)
                elif tone == 'violin':
                    wave = (.52*np.sin(phase) + .27*np.sin(2*phase)
                            + .14*np.sin(3*phase) + .07*np.sin(4*phase))
                elif tone == 'strings':
                    wave = (.67*np.sin(phase) + .17*np.sin(2*phase)
                            + .10*np.sin(3*phase) + .06*np.sin(5*phase))
                elif tone == 'music_box':
                    wave = (.69*np.sin(phase) + .23*np.sin(3.99*phase)
                            + .08*np.sin(6.01*phase))
                elif tone == 'guitar':
                    wave = (.68*np.sin(phase) + .23*np.sin(2*phase)
                            + .09*np.sin(3*phase))
                else:  # piano
                    wave = (.73*np.sin(phase) + .18*np.sin(2*phase)
                            + .09*np.sin(3*phase))
                old = voice['level']
                desired = 0.0 if voice['released'] else 1.0
                # Attack 8 ms; release about 90 ms. Exact per-sample continuous ramps.
                pole = math.exp(-1. / (self.RATE * (.09 if voice['released'] else .008)))
                env = desired + (old-desired) * np.power(pole, t+1)
                voice['level'] = float(env[-1])
                voice['phase'] = float((phase[-1] + 2*math.pi*freq/self.RATE) % (2*math.pi))
                mix += wave * env * voice['velocity'] * .18
                if voice['released'] and voice['level'] < .001:
                    finished.append(key)
            for key in finished:
                self._voices.pop(key, None)
        outdata[:, :] = np.tanh(mix * self.volume).astype(np.float32)[:, None]
