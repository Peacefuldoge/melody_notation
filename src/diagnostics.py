"""Opt-in-at-GUI-startup fatal-crash traceback capture.

Native Qt/PortAudio access violations can terminate Python without a normal
exception dialog. faulthandler writes the last Python thread stacks to a
file on supported platforms (including Windows) to aid reproducible reports.
"""
from __future__ import annotations

import faulthandler
import os
from pathlib import Path
import sys
import traceback
from datetime import datetime, timezone

_log_handle = None
_original_excepthook = None


def crash_log_path() -> Path:
    """Keep logs outside the tracked project and user output directory."""
    local = os.environ.get('LOCALAPPDATA')
    root = Path(local) if local else Path.home() / '.local' / 'state'
    return root / 'MelodyNotation' / 'logs' / 'crash.log'


def enable_gui_crash_log(log_path: Path | None = None) -> Path:
    """Enable one persistent crash log for the GUI process (idempotent)."""
    global _log_handle, _original_excepthook
    path = Path(log_path) if log_path is not None else crash_log_path()
    if _log_handle is not None:
        return Path(_log_handle.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep historical failures but prevent an unbounded log from accumulating.
    if path.exists() and path.stat().st_size > 3 * 1024 * 1024:
        path.replace(path.with_suffix('.previous.log'))
    stream = path.open('a', encoding='utf-8', buffering=1)
    stream.write(f'\n--- GUI session {datetime.now(timezone.utc).isoformat()} ---\n')
    faulthandler.enable(file=stream, all_threads=True)
    _log_handle = stream
    _original_excepthook = sys.excepthook

    def _log_exception(exc_type, exc_value, exc_traceback):
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=stream)
        stream.flush()
        _original_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _log_exception
    return path
