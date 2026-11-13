"""In-window audio playback, with no external media-player window.

Windows: built-in WinMM MCI waveaudio (zero extra dependencies).
macOS/Linux: optional sounddevice backend (`pip install sounddevice`).

The UI invokes these objects only on the Tk main thread. Waveform rendering can
run on a worker; no Tk calls are made from the worker.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import tempfile
import time
import uuid

import numpy as np
import soundfile as sf


class PlaybackError(RuntimeError):
    """Audio device is missing or the playback command failed."""


def clock_label(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60}:{seconds % 60:02d}'


class WindowsMCIPlayer:
    """Control WAV playback inside the process with the Windows waveaudio driver.

    MCI is a Windows legacy interface: suitable for our Tkinter Windows build;
    a modern WASAPI adapter can replace it later behind this same API.
    """

    def __init__(self, *, sender=None, error_text=None):
        if sender is None:
            if os.name != 'nt':
                raise PlaybackError('Windows built-in audio playback is only available on Windows')
            dll = ctypes.WinDLL('winmm')
            sender = dll.mciSendStringW
            sender.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
            sender.restype = ctypes.c_uint
            error_text = dll.mciGetErrorStringW
            error_text.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
            error_text.restype = ctypes.c_int
        self._send = sender
        self._error_text = error_text
        self._alias = 'melody_' + uuid.uuid4().hex[:12]
        self._path: Path | None = None
        self._owns_path = False
        self._state = 'stopped'
        self._duration = 0.0
        self._paused_at = 0.0
        self._seek_at = 0.0
        self._seeked_while_paused = False

    def _cmd(self, command: str, *, result: bool = False) -> str:
        buf = ctypes.create_unicode_buffer(256)
        code = self._send(command, buf, len(buf), None)
        if code:
            reason = f'Windows MCI error {code}'
            if self._error_text is not None:
                err = ctypes.create_unicode_buffer(256)
                if self._error_text(code, err, len(err)):
                    reason = err.value
            raise PlaybackError(f'{reason} ({command.split(" ", 1)[0]})')
        return buf.value if result else ''

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        if self._path is None:
            return 0.0
        if self._state == 'paused':
            return self._paused_at
        if self._state == 'stopped':
            return self._seek_at
        try:
            ms = int(self._cmd(f'status {self._alias} position', result=True))
            return max(0.0, min(self.duration, ms / 1000.0))
        except (ValueError, PlaybackError):
            return 0.0

    @property
    def state(self) -> str:
        if self._path is None or self._state == 'paused':
            return self._state
        if self._state == 'playing':
            try:
                mode = self._cmd(f'status {self._alias} mode', result=True).lower()
                if mode != 'playing':
                    self._state = 'stopped'
                    self._seek_at = self.duration
            except PlaybackError:
                self._state = 'stopped'
        return self._state

    def load(self, audio: np.ndarray, samplerate: int) -> None:
        self.close()
        file_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix='melody_play_', suffix='.wav', delete=False) as fp:
                file_path = Path(fp.name)
            # MCI handles PCM_16 files consistently on Windows.
            sf.write(file_path, np.asarray(audio, dtype=np.float32), samplerate, subtype='PCM_16')
            self._cmd(f'open "{file_path}" type waveaudio alias {self._alias}')
            self._path = file_path
            self._owns_path = True
            self._cmd(f'set {self._alias} time format milliseconds')
            self._duration = len(audio) / samplerate
            self._state = 'stopped'
            self._paused_at = 0
            self._seek_at = 0
            self._seeked_while_paused = False
        except Exception:
            if self._path is not None:
                try: self._cmd(f'close {self._alias}')
                except PlaybackError: pass
            self._path = None
            self._owns_path = False
            if file_path is not None:
                file_path.unlink(missing_ok=True)
            raise

    def load_file(self, path: str | Path) -> None:
        """Play a pre-rendered WAV directly, without copying or deleting it.

        Qt's audio backend is not reliable on every Windows installation;
        reusing the existing WinMM/MCI backend avoids external codecs.
        Caller owns the WAV and must keep it available until close().
        """
        src = Path(path).resolve()
        if not src.is_file():
            raise PlaybackError(f'试听音频文件不存在：{src}')
        try:
            info = sf.info(src)
            if not info.frames or info.samplerate <= 0:
                raise PlaybackError('试听音频文件没有可播放的数据')
        except (RuntimeError, OSError) as exc:
            raise PlaybackError(f'试听 WAV 无法读取：{exc}') from exc
        self.close()
        opened = False
        try:
            self._cmd(f'open "{src}" type waveaudio alias {self._alias}')
            opened = True
            self._path = src
            self._owns_path = False
            self._cmd(f'set {self._alias} time format milliseconds')
            self._duration = info.frames / info.samplerate
            self._state = 'stopped'
            self._paused_at = self._seek_at = 0.0
            self._seeked_while_paused = False
        except Exception:
            if opened:
                try: self._cmd(f'close {self._alias}')
                except PlaybackError: pass
            self._path = None
            self._owns_path = False
            raise

    def play(self) -> None:
        if self._path is None:
            raise PlaybackError('请先加载一段可试听的旋律')
        if self._state == 'paused':
            if self._seeked_while_paused:
                self._cmd(f'play {self._alias} from {int(self._paused_at * 1000)}')
            else:
                try:
                    self._cmd(f'resume {self._alias}')
                except PlaybackError:
                    # Some old waveaudio drivers reject RESUME but accept PLAY FROM.
                    self._cmd(f'play {self._alias} from {int(self._paused_at * 1000)}')
        else:
            start = 0 if self._seek_at >= self.duration else int(self._seek_at * 1000)
            self._cmd(f'play {self._alias} from {start}')
        self._seeked_while_paused = False
        self._state = 'playing'

    def pause(self) -> None:
        if self.state != 'playing':
            return
        self._paused_at = self.position
        self._cmd(f'pause {self._alias}')
        self._state = 'paused'

    def stop(self) -> None:
        if self._path is not None:
            self._cmd(f'stop {self._alias}')
            self._cmd(f'seek {self._alias} to start')
        self._state = 'stopped'
        self._paused_at = 0
        self._seek_at = 0
        self._seeked_while_paused = False

    def seek(self, seconds: float) -> None:
        if self._path is None:
            return
        seconds = max(0.0, min(float(seconds), self.duration))
        ms = int(seconds * 1000)
        state = self.state
        if state == 'playing':
            self._cmd(f'play {self._alias} from {ms}')
        else:
            self._cmd(f'seek {self._alias} to {ms}')
        self._seek_at = seconds
        if state == 'paused':
            self._paused_at = seconds
            self._seeked_while_paused = True

    def close(self) -> None:
        path = self._path
        if path is None:
            return
        try:
            self._cmd(f'stop {self._alias}')
        except PlaybackError:
            pass
        try:
            self._cmd(f'close {self._alias}')
        finally:
            self._path = None
            self._state = 'stopped'
            self._duration = 0
            self._paused_at = 0
            self._seek_at = 0
            self._seeked_while_paused = False
            if self._owns_path:
                path.unlink(missing_ok=True)
            self._owns_path = False


class SoundDevicePlayer:
    """Optional portable backend. Import sounddevice only when used."""

    def __init__(self, *, sounddevice=None, clock=None):
        if sounddevice is None:
            try:
                import sounddevice as sounddevice
            except ImportError as exc:
                raise PlaybackError('此系统请先安装音频后端：python -m pip install sounddevice') from exc
        self._sd = sounddevice
        self._clock = clock or time.monotonic
        self._data = np.empty(0, dtype=np.float32)
        self._sr = 22050
        self._position = 0.0
        self._started_at = 0.0
        self._state = 'stopped'

    @property
    def duration(self):
        return len(self._data) / self._sr

    @property
    def position(self):
        if self._state == 'playing':
            return min(self.duration, self._position + max(0, self._clock() - self._started_at))
        return self._position

    @property
    def state(self):
        if self._state == 'playing' and self.position >= self.duration:
            self._sd.stop()
            self._state = 'stopped'
            self._position = self.duration
        return self._state

    def load(self, audio: np.ndarray, samplerate: int):
        self.close()
        self._data = np.asarray(audio, dtype=np.float32).copy()
        self._sr = samplerate
        self._position = 0

    def play(self):
        if not len(self._data):
            raise PlaybackError('请先加载一段可试听的旋律')
        if self.position >= self.duration:
            self._position = 0.0
        start = min(len(self._data), int(self._position * self._sr))
        try:
            self._sd.play(self._data[start:], samplerate=self._sr, blocking=False)
        except Exception as exc:
            raise PlaybackError(f'音频设备无法播放：{exc}') from exc
        self._started_at = self._clock()
        self._state = 'playing'

    def pause(self):
        if self.state != 'playing':
            return
        self._position = self.position
        self._sd.stop()
        self._state = 'paused'

    def stop(self):
        self._sd.stop()
        self._position = 0.0
        self._state = 'stopped'

    def seek(self, seconds: float):
        was_playing = self.state == 'playing'
        self._sd.stop()
        self._position = max(0.0, min(float(seconds), self.duration))
        self._state = 'paused' if was_playing else self._state
        if was_playing:
            self.play()

    def close(self):
        self._sd.stop()
        self._data = np.empty(0, dtype=np.float32)
        self._position = 0
        self._state = 'stopped'


def create_player():
    return WindowsMCIPlayer() if os.name == 'nt' else SoundDevicePlayer()
