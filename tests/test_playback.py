from __future__ import annotations
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest

from melody_notation.playback import (
    PlaybackError, SoundDevicePlayer, WindowsMCIPlayer, clock_label,
)


def test_clock_labels():
    assert clock_label(0) == '0:00'
    assert clock_label(61.9) == '1:01'
    assert clock_label(-4) == '0:00'


class FakeWinMM:
    def __init__(self):
        self.commands=[]
        self.state='stopped'
        self.pos=0
        self.opened=False

    def __call__(self, command, buffer, length, callback):
        self.commands.append(command)
        if command.startswith('open '):
            self.opened=True
        elif command.startswith('play '):
            self.state='playing'
            if ' from ' in command:self.pos=int(command.rsplit(' from ',1)[1])
        elif command.startswith('pause '):
            self.state='paused'
        elif command.startswith('resume '):
            self.state='playing'
        elif command.startswith('stop '):
            self.state='stopped'
        elif command.startswith('seek '):
            if command.endswith('to start'):self.pos=0
            else:self.pos=int(command.rsplit(' to ',1)[1])
        elif command.startswith('close '):
            self.opened=False
        elif ' position' in command:
            buffer.value=str(self.pos)
        elif ' mode' in command:
            buffer.value=self.state
        return 0


def test_windows_mci_lifecycle(tmp_path):
    sender=FakeWinMM()
    player=WindowsMCIPlayer(sender=sender)
    player.load(np.zeros(22050, dtype=np.float32),22050)
    assert player.duration==1.0
    assert player._path.exists()
    player.play()
    assert player.state=='playing'
    sender.pos=310
    player.pause()
    assert player.state=='paused'
    assert player.position==pytest.approx(.31)
    player.seek(.6)
    player.play()
    assert sender.pos==600
    assert sender.commands[-1].endswith('from 600')
    player.stop()
    assert player.position==0
    assert player.state=='stopped'
    path=player._path
    player.close()
    assert not path.exists()
    assert not sender.opened


def test_windows_mci_error_cleans_temp_audio():
    sender=FakeWinMM()
    def broken(cmd,buf,n,cb):
        if cmd.startswith('set '):return 255
        return sender(cmd,buf,n,cb)
    player=WindowsMCIPlayer(sender=broken)
    with pytest.raises(PlaybackError, match='255'):
        player.load(np.zeros(100,dtype=np.float32),22050)
    assert player._path is None
    assert not sender.opened


def test_sounddevice_play_pause_seek_resume_stop():
    sd=Mock()
    now=[0.0]
    player=SoundDevicePlayer(sounddevice=sd,clock=lambda:now[0])
    player.load(np.zeros(1000,dtype=np.float32),1000)
    player.play()
    now[0]=.2
    assert player.position==pytest.approx(.2)
    player.pause()
    assert player.state=='paused'
    assert player.position==pytest.approx(.2)
    now[0]=1.2
    assert player.position==pytest.approx(.2)
    player.seek(.5)
    player.play()
    assert len(sd.play.call_args.args[0])==500
    now[0]=1.4
    assert player.position==pytest.approx(.7)
    player.stop()
    assert player.position==0
    player.close()


def test_sounddevice_ends_at_duration():
    sd=Mock()
    now=[0.0]
    player=SoundDevicePlayer(sounddevice=sd,clock=lambda:now[0])
    player.load(np.zeros(100, dtype=np.float32),100)
    player.play()
    now[0]=1.1
    assert player.state=='stopped'
    assert player.position==1.0
    player.play()
    assert len(sd.play.call_args.args[0])==100


def test_windows_mci_load_existing_wav_without_deleting_source(tmp_path):
    import soundfile as sf
    wav=tmp_path/'试听片段.wav'
    sf.write(wav,np.linspace(-.2,.2,22050,dtype=np.float32),22050,subtype='PCM_16')
    driver=FakeWinMM()
    player=WindowsMCIPlayer(sender=driver)
    player.load_file(wav)
    assert player.duration == pytest.approx(1.0)
    assert player._path == wav.resolve()
    assert player._owns_path is False
    player.play()
    assert any('open "' in cmd and '试听片段.wav' in cmd for cmd in driver.commands)
    assert player.state=='playing'
    player.pause()
    assert player.state=='paused'
    player.seek(.4)
    player.play()
    assert driver.pos==400
    player.stop()
    player.close()
    assert wav.exists(), 'GUI temp folder owns the rendered preview; MCI must not delete it'
    assert not driver.opened


def test_windows_mci_load_existing_wav_error_keeps_source(tmp_path):
    import soundfile as sf
    wav=tmp_path/'preview.wav'
    sf.write(wav,np.zeros(1000,dtype=np.float32),22050,subtype='PCM_16')
    driver=FakeWinMM()
    def broken(command,buffer,length,callback):
        if command.startswith('set '):return 123
        return driver(command,buffer,length,callback)
    player=WindowsMCIPlayer(sender=broken)
    with pytest.raises(PlaybackError, match='123'):
        player.load_file(wav)
    assert not driver.opened
    assert player._path is None
    assert wav.exists()


def test_windows_mci_missing_file_does_not_replace_loaded_audio(tmp_path):
    player=WindowsMCIPlayer(sender=FakeWinMM())
    with pytest.raises(PlaybackError, match='不存在'):
        player.load_file(tmp_path/'missing.wav')
    assert player._path is None
