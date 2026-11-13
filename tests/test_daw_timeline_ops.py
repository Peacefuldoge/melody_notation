from melody_notation.arrangement import Clip
from melody_notation.timeline_ops import (
    snap_beat, clip_length, change_clip_on_timeline, split_clip,
)
import pytest


def test_snap_and_move():
    c=Clip('melody.jianpu',start_beat=2.0)
    assert snap_beat(2.32,.25)==2.25
    assert snap_beat(2.32,0)==2.32
    assert change_clip_on_timeline(c,'move',1.35,12,.25).start_beat==3.25
    assert c.start_beat==2.0  # non-destructive copy
    assert change_clip_on_timeline(c,'move',-50,12,.25).start_beat==0.0


def test_trim_left_keeps_end_of_clip_in_place():
    c=Clip('melody.jianpu',start_beat=4,trim_start=1,trim_end=9)
    end_before=c.start_beat+clip_length(c,12)
    edited=change_clip_on_timeline(c,'trim_left',2,12,0.25)
    assert edited.start_beat==6
    assert edited.trim_start==3
    assert edited.start_beat+clip_length(edited,12)==end_before
    assert change_clip_on_timeline(c,'trim_left',-20,12,0.25).trim_start==0


def test_trim_right_clamps_to_source_length():
    c=Clip('melody.jianpu',start_beat=2,trim_start=1,trim_end=4)
    edited=change_clip_on_timeline(c,'trim_right',50,8,.25)
    assert edited.trim_end==8
    trimmed=change_clip_on_timeline(c,'trim_right',-50,8,.25)
    assert clip_length(trimmed,8)==.25


def test_split_preserves_coverage_and_source_offsets():
    c=Clip('melody.jianpu',start_beat=4,trim_start=1,trim_end=9)
    a,b=split_clip(c,7,12,.25)
    assert (a.start_beat,a.trim_start,a.trim_end)==(4,1,4)
    assert (b.start_beat,b.trim_start,b.trim_end)==(7,4,9)
    assert clip_length(a,12)+clip_length(b,12)==clip_length(c,12)
    with pytest.raises(ValueError):split_clip(c,4,12,.25)


def test_split_and_trim_do_not_change_source():
    c=Clip('melody.jianpu',start_beat=1,trim_start=0,trim_end=None)
    left,right=split_clip(c,4,8,.25)
    assert c.trim_end is None
    assert left.trim_end==3
    assert right.trim_start==3
