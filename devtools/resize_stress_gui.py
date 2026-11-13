"""Interactive or offscreen Windows resize stress test for Melody Notation.

Run from project root:
  python devtools/resize_stress_gui.py --iterations 250

To test without a visible window:
  python devtools/resize_stress_gui.py --offscreen --iterations 250

A crash may leave a traceback in:
  %LOCALAPPDATA%\\MelodyNotation\\logs\\crash.log
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=120)
    parser.add_argument('--offscreen', action='store_true')
    args = parser.parse_args()
    if args.offscreen:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    from melody_notation.diagnostics import enable_gui_crash_log
    log = enable_gui_crash_log()
    from PySide6.QtWidgets import QApplication
    from melody_notation.qt_gui import MelodyMainWindow, ScoreEditor
    from melody_notation.core import parse_text, blank_score_text

    app = QApplication.instance() or QApplication(sys.argv[:1])
    win = MelodyMainWindow()
    win.show()
    app.processEvents()
    editor = ScoreEditor(parse_text(blank_score_text(), strict=False))
    editor.resize(1100, 800)
    editor.show()
    app.processEvents()
    panel = editor.keyboard_panel
    widths = (1520, 1000, 1280, 980, 1190, 1470)
    editor_widths = (1200, 850, 610, 420, 730, 1350)
    try:
        for i in range(args.iterations):
            win.resize(widths[i % len(widths)], 800 + (i % 4) * 32)
            editor.resize(editor_widths[i % len(editor_widths)], 760)
            if i % 8 == 0:
                panel.settings_button.click()
            if i % 13 == 0:
                win.toggle_sidebar()
            app.processEvents()
            if i % 25 == 0:
                print(f'Completed {i + 1}/{args.iterations} resize cycles', flush=True)
        print(f'PASS: {args.iterations} resize cycles; crash log: {log}', flush=True)
    finally:
        panel.settings_dialog.close()
        editor.set_input_active(False)
        editor.close()
        win.close()
        app.processEvents()


if __name__ == '__main__':
    main()
