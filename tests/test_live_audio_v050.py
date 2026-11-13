"""Device-free audio callback coverage: multi-voice output and release."""
import numpy as np
from melody_notation.live_audio import LiveAudioSynth


def test_audio_voice_generates_finite_stereo_and_releases():
    synth=LiveAudioSynth()
    synth._voices[('keyboard',60)] = {'pitch':60,'phase':0.,'level':0.,
        'velocity':90/127.,'released':False}
    synth._voices[('midi',64)] = {'pitch':64,'phase':0.,'level':0.,
        'velocity':100/127.,'released':False}
    stereo=np.zeros((512,2),dtype=np.float32)
    synth._render(stereo,512,None,None)
    assert np.max(np.abs(stereo))>0.01
    assert np.all(np.isfinite(stereo))
    assert np.allclose(stereo[:,0],stereo[:,1])
    synth.all_off()
    for _ in range(250):synth._render(stereo,512,None,None)
    assert len(synth._voices)==0
