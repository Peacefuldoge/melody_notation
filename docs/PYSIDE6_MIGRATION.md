# Melody Notation v0.4.0 · PySide6 GUI migration

## Objectives

Replace the desktop **presentation layer** with PySide6 without changing any existing project file formats or the headless engines. New Qt code lives in `src/qt_gui.py`, `qt_help.py` and `preview_engine.py`. Core music functions stay independent from Qt and from AI providers.

## Window layout

- **Left:** compact ChatGPT-inspired project navigation, project creation/opening, project file tree with folders, search, recent project switcher, file/edit/export menu.
- **Center:** `QTabWidget`, supporting `.jianpu`, `.drum`, `.mtrack` **within the same workspace**. Closing an edited tab prompts to save.
- **Right top:** built-in audio preview (`QMediaPlayer` + `QAudioOutput`), progress seek, play/pause/stop, instrument presets and speeds 1.00× / 1.25× / 1.50× / 1.75× / 2.00×.
- **Right bottom:** context-sensitive properties for a selected notation note / drum kit / multitrack instrument, plus slur and note operations.
- **Top:** compact product and current-file title; no redundant file/edit/export button row.

### Actual document editors

| Format | Core UI | Edits | Persistence |
|---|---|---|---|
| `.jianpu` | Scrollable, horizontally centered, click-to-select score renderer shared with PNG export | Pitch, octave, duration, accidentals, ornaments, slur start/end, add/remove note, source text, undo/redo | Original plain-text format |
| `.drum` | 16-step-per-bar grid for kick/snare/closed hi-hat | Toggle hits, change BPM/bars/kit, undo/redo | Original JSON format |
| `.mtrack` | Timeline overview, track table, clip table | Add Melody sources, move/delete tracks, move/reverse/trim/gain clips, mute/Solo, instrument, undo/redo | Original JSON format |

### Playback

The Qt UI synthesizes the current document in a worker thread to a WAV file inside a temporary directory. `QMediaPlayer` opens that WAV **inside the app** (no external player). Speed is applied to individual musical events before synthesis so note pitch is preserved. The temporary files are cleaned on normal exit. The playback engine can continue to be changed without altering any `.jianpu`, `.drum` or `.mtrack` file.

### Notes on unsaved documents

- Score source text can contain temporarily invalid bars until the user applies it. Save accepts non-strict parse but exporting/audio must pass strict validation.
- Multiple documents can be edited independently and have their own undo stacks. The active tab is the only target of Save, Export and Playback.
- `.mtrack` renders source files **from disk**, so save changes in related `.jianpu`/`.drum` tabs before playing a multitrack mix.
- The multitrack timeline is currently a visual overview with numeric clip editing; **mouse dragging to position/resize clips is not yet implemented**.
- UI does not yet provide a channel mixer, DAW-style automation, full MusicXML engraving, or AI chat panels.

## Install on Windows (Conda)

```powershell
conda activate melody
cd D:\Work\melody-notation-v0.4.0
python -m pip install -e ".[all,test]"
python -m melody_notation.cli gui
```

For only the desktop GUI (without the optional AI SDKs):

```powershell
python -m pip install -e ".[gui,test]"
```

Open a particular project directly:

```powershell
python -m melody_notation.cli gui "D:\Work\My Melody Project"
```

Previous Tkinter GUI is retained temporarily for fallback:

```powershell
python -m melody_notation.cli tk-gui
```

## Verification

```powershell
python -m pytest -q
python devtools\qt_gui_smoke.py
```

Use the GUI smoke test **after PySide6 has been installed**. It creates an isolated temporary project and tests three editors, theme changes, score note edits, drum editing and saving. It does not overwrite real user projects.

**Validation boundary for this release:** the packaging/build environment did not have PySide6 and could not install it due network access. We ran core tests, Qt module syntax compilation and headless preview engine tests, but could **not** actually launch the Qt GUI or verify Windows audio-device output here. Install on the target Windows computer and run the smoke script before migrating daily work.

## Qt API references

- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/)
- [QMainWindow](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QMainWindow.html)
- [QMediaPlayer](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html)

## Architecture and compatibility

- Only CLI command `gui` now routes to Qt; command `tk-gui` continues to route to the legacy Tkinter UI.
- No changes to `core.py`, `editing.py`, `midi.py`, `audio.py`, `drums.py`, `arrangement.py`, `mcp_server.py` or `.agents/skills/melody-harmony` were required.
- The Codex and DeepSeek Harness MCP entry point remains `python -m melody_notation.mcp_server`; the MCP schema is unchanged.
- `.jianpu` / `.drum` / `.mtrack` can still be edited with previous versions. Test with copies of important projects when migrating.
