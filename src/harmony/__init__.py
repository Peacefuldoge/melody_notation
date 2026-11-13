"""Read-only musical harmony knowledge for Codex/DeepSeek Harness.

Knowledge retrieval does not implement multi-track accompaniment.
"""
from __future__ import annotations
from importlib.resources import files

TOPICS = {
    'overview': '学习路径和能力边界',
    'chords': '常见和弦构成、情绪与用法',
    'progressions': '大调/小调的和弦进行',
    'workflow': 'AI 为简谱配和弦的检查步骤',
    'sources': '出处与情感解释的证据边界',
}


def read_topic(topic: str = 'overview') -> str:
    """Return bundled read-only reference text; no filesystem path input."""
    if topic not in TOPICS:
        raise ValueError(f'Unknown harmony topic {topic!r}. Allowed: {", ".join(TOPICS)}')
    if topic == 'overview':
        return ('Melody Harmony is a read-only composition knowledge skill. '
                'Choose chords based on key, melody, bass motion, harmonic function, '
                'voice leading and context. Emotion labels are tendencies, not laws. '
                'Read chords, progressions, workflow, sources for details. '
                'The current Melody Notation engine is monophonic: do not promise '
                'simultaneous chord playback, multi-track export or native chord notation.')
    return files(__package__).joinpath(f'{topic}.md').read_text(encoding='utf-8')
