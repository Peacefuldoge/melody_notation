"""Beat-accurate, non-destructive editing primitives for the DAW timeline.

These functions have no Qt dependency and keep the existing .mtrack v1 schema.
"""
from __future__ import annotations
from copy import deepcopy
from math import floor
from .arrangement import Clip

MIN_CLIP_BEATS = 0.25


def snap_beat(value: float, grid: float) -> float:
    value = max(0.0, float(value))
    return floor(value / grid + 0.5) * grid if grid > 0 else round(value, 4)


def clip_length(clip: Clip, source_length: float) -> float:
    return (source_length if clip.trim_end is None else clip.trim_end) - clip.trim_start


def change_clip_on_timeline(clip: Clip, action: str, delta_beats: float,
                            source_length: float, grid: float = 0.25) -> Clip:
    """Move or trim a clip. Trims preserve absolute source event timing.

    Left trims slide the clip start and its source in-point equally, so the
    right edge does not move. Right trims only change the out-point.
    """
    result = deepcopy(clip)
    end = source_length if clip.trim_end is None else clip.trim_end
    if source_length <= 0 or clip.trim_start >= end:
        raise ValueError('无效的素材裁剪范围')
    if action == 'move':
        result.start_beat = snap_beat(clip.start_beat + delta_beats, grid)
    elif action == 'trim_left':
        target = snap_beat(clip.start_beat + delta_beats, grid)
        target = min(max(target, max(0.0, clip.start_beat - clip.trim_start)),
                     clip.start_beat + end - clip.trim_start - MIN_CLIP_BEATS)
        delta = target - clip.start_beat
        result.start_beat = round(target, 4)
        result.trim_start = round(clip.trim_start + delta, 4)
    elif action == 'trim_right':
        original_end = clip.start_beat + end - clip.trim_start
        target = snap_beat(original_end + delta_beats, grid)
        target = min(max(target, clip.start_beat + MIN_CLIP_BEATS),
                     clip.start_beat + source_length - clip.trim_start)
        result.trim_end = round(clip.trim_start + target - clip.start_beat, 4)
    else:
        raise ValueError('未知的时间线编辑模式')
    return result


def split_clip(clip: Clip, position_beat: float, source_length: float,
               grid: float = 0.25) -> tuple[Clip, Clip]:
    at = snap_beat(position_beat, grid)
    length = clip_length(clip, source_length)
    rel = at - clip.start_beat
    if rel < MIN_CLIP_BEATS - 1e-5 or rel > length - MIN_CLIP_BEATS + 1e-5:
        raise ValueError('切割位置必须在片段内部，并至少保留 1/4 拍')
    left, right = deepcopy(clip), deepcopy(clip)
    left.trim_end = round(clip.trim_start + rel, 4)
    right.start_beat = round(at, 4)
    right.trim_start = left.trim_end
    return left, right
