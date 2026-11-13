"""Regression tests for horizontal centering without breaking hit testing."""
import tkinter as tk
import pytest
from melody_notation.gui import Editor, score_preview_layout


def test_wide_viewport_centers_page_at_native_size():
    scale, pos, shown, region = score_preview_layout((1200, 3200), (1700, 800))
    assert scale == 1
    assert shown == (1200, 3200)
    assert pos == (250, 12)
    assert region == (0, 0, 1700, 3224)


def test_narrow_viewport_fits_without_offscreen_page():
    scale, pos, shown, region = score_preview_layout((1200, 3200), (800, 500))
    assert 0 < scale < 1
    assert shown[0] <= 800 - 24
    assert abs(pos[0] - ((800 - shown[0]) // 2)) <= 1
    assert region[2] == 800
    assert region[3] > 500


def test_near_page_width_preserves_padding_and_does_not_upscale():
    for w in [960, 1200, 1224, 1440, 1800]:
        scale, pos, shown, region = score_preview_layout((1200, 1200), (w, 750))
        assert scale <= 1
        assert pos[0] >= 12
        assert pos[0] + shown[0] <= region[2]
        assert abs((w - shown[0]) / 2 - pos[0]) <= 1


def test_real_tk_window_resize_repositions_and_keeps_note_selection():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('Tk display not available')
    try:
        root.geometry('1450x850')
        ed = Editor(root)
        root.update()
        ed.redraw()
        first_x = ed.offset[0]
        root.geometry('1840x900')
        root.update()
        ed.redraw()
        second_x = ed.offset[0]
        assert second_x > first_x
        assert ed.offset[0] == max(12, (ed.canvas.winfo_width() - ed.photo.width()) // 2)
        assert ed.canvas.cget('scrollregion')
        # Click the first note using its transform from image to viewport coords.
        bar, note, (x0, y0, x1, y1) = ed.hits[0]
        page_x = ed.offset[0] + ed.scale * ((x0 + x1) / 2)
        page_y = ed.offset[1] + ed.scale * ((y0 + y1) / 2)
        class E: pass
        e = E()
        e.x = int(page_x - ed.canvas.canvasx(0))
        e.y = int(page_y - ed.canvas.canvasy(0))
        ed._on_canvas_click(e)
        assert ed.selected == (bar, note)
    finally:
        root.destroy()
