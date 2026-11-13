# Melody Notation v0.4.1 — PySide6 UI refresh

## Scope and compatibility

Pure GUI refresh: `.jianpu`, `.drum`, `.mtrack`, MIDI, audio rendering, PNG export and Codex/DeepSeek Harness MCP interfaces are unchanged. The existing Tkinter fallback (`tk-gui`) is also preserved.

## Changes

1. **Four application themes:** light, dark, warm beige, muted olive. The editable score paper, musical marks, slurs, articulation, active notes, drum pads, and track timeline use matching palette tokens. Print/export PNG still defaults to black notes on white paper.
2. **Window materials:** Windows 11 builds supporting `DwmSetWindowAttribute` are requested to draw native Desktop Acrylic (attribute 38 / transient backdrop), and round the main window (attribute 33 / round). Qt widgets use semi-transparent tinted panels and subtle borders. Windows 10/macOS/Linux fall back to the tinted panels; full OS-background blur is **not guaranteed**, especially if Qt paints an opaque surface. The standard titlebar is preserved so window resizing/maximizing remain native.
3. **High-DPI vector-drawn icons:** sidebar menu, the ? help button, settings gear beneath it, project tree folder/score/drums/tracks and playback buttons are painted through Qt with anti-aliasing at 3x pixel density; no third-party icon font or blurry PNG assets.
4. **Single Settings window:** bottom left, gear immediately below ?, containing theme, UI language (Simplified Chinese / English), default save directory and toggle for native material. Changes apply without restarting and persist via Qt `QSettings`. Default directory controls Open file, New project, Save As, Export and image import file dialog starting locations; project files still use the project tree.
5. **English UI:** main workbench menus, navigation, playback, core Inspector/editing controls, quick help, properties and Settings dialog are localized. Some advanced error messages and legacy workflow dialogs remain Chinese pending a subsequent translation pass.

## Windows requirements

```powershell
conda activate melody
cd D:\Work\melody-notation-v0.4.1
python -m pip install -e ".[gui,test]"
python -m melody_notation.cli gui
```

The DWM backdrop attribute needs **Windows 11 build 22621 or later**. The rounded-corner preference needs Windows 11. On unsupported versions, the UI continues without a fatal error. You can disable native material in Settings if a display driver or remote desktop causes artifacts.

## Verify on the user's Windows computer

```powershell
python devtools\qt_gui_smoke.py
python devtools\qt_settings_smoke.py
python -m pytest -q
```

Check manually: maximize/restore; English and Chinese; open project; create `.jianpu`, `.drum`, `.mtrack`; save and export; switch all four themes while a score is open; verify the gear is directly under ?, the preview colors, anti-aliased icons, and setting persistence after restart. Verify high-DPI display scaling (100%, 125%, 150%).

## Known limitations

- PySide6 was unavailable in the build environment; actual Windows Qt rendering, DWM material, resizing, and settings interaction require Windows testing. Do not interpret headless core tests as a passed GUI acceptance test.
- Desktop Acrylic behind every interior widget is not guaranteed solely by the DWM backdrop request. The tinted translucent panel fallback is deterministic; native blur visibility is platform/Qt-compositor dependent.
- No changes to current music tools, engine algorithms, multi-track mixing, or MCP tools were made.
