# GUI migration note (v0.4.0)

- Preferred desktop UI: `melody_notation.qt_gui`, launched by `python -m melody_notation.cli gui`.
- Previous Tkinter GUI: `python -m melody_notation.cli tk-gui`. Do not silently delete legacy files until Qt testing is complete.
- Project document formats and headless MCP entry point MUST remain backward compatible.
- Qt presentation code must not be imported by the Core, MCP or Harmony Skill.
- Qt GUI runtime smoke: `python devtools/qt_gui_smoke.py` after installing PySide6.
- For musical harmony, read `.agents/skills/melody-harmony/SKILL.md`.

# Melody Notation agent notes

This project provides a reusable harmony Skill at `.agents/skills/melody-harmony/SKILL.md`.

When asked to harmonize a numbered melody, explain chord colors, propose chord progressions, select voicings, or plan arrangements:
1. Load the `melody-harmony` Skill and follow its task workflow.
2. Use its bundled `src/harmony/` references for verified chord formulas and contextual emotional descriptions.
3. If communicating via the MCP server (including DeepSeek Harness), use `list_harmony_topics` and `read_harmony_guide` to retrieve the same knowledge.
4. Respect existing single-melody `.jianpu` capabilities: the `.jianpu` editor is monophonic, but `.mtrack` arrangements now support multiple `.jianpu` and `.drum` clips mixed together. Do not claim automatic chord generation or a piano-roll editor exists.
5. Never overwrite the user's score without approval; validate against the key, modulation points and bar durations.

This instruction does not supersede user requests or project code safety rules.

## v0.3 arrangement/drums contract

- Use `.jianpu` for monophonic numbered notation, `.drum` for editable kick/snare/closed-hi-hat step patterns, `.mtrack` for a reference-based multi-track composition.
- Read `docs/MULTITRACK_DRUMS.md` and the melody-notation Skill for commands and examples.
- For Codex and DeepSeek Harness, use MCP `inspect_arrangement`, `create_arrangement`, `add_arrangement_clip`, `edit_arrangement_clip`, `reorder_arrangement_track`, `export_multitrack_midi`, `export_multitrack_audio` and `.drum` tools.
- **Never edit an original `.jianpu` to trim/reverse the arrangement.** Update the `.mtrack` clip fields and preserve the source.
- MIDI drums follow GM channel 10 notes 36 (kick), 38 (snare), 42 (closed hi-hat). Acoustic/electronic/8-bit kit variations are synthesized in WAV/MP3 but are not guaranteed to round-trip as a sound kit in arbitrary MIDI players.
- Any operation changing an existing file needs explicit user approval (`overwrite=true`). Inspect/preview first. No autonomous file overwrites without review.

## PySide6 application shell (v0.4.2)
- Preserve the Codex-style **information architecture**, not a copy of ChatGPT branding: fixed 54px icon rail, collapsible project pane, central document tabs and optional right playback/inspector pane.
- Keep a single standard menu bar. Project ellipsis is **project operations only**; `+ New music file` holds score/drums/multitrack creation.
- Help and Settings belong at the bottom of the permanent icon rail, Settings immediately under Help.
- Keep light, dark, beige and olive palettes and apply them to score preview too; printed PNG stays white.
- Never introduce AI conversation UI or pretend missing music functions exist without explicit request.
- `qt_gui.py` must not modify `.jianpu`, `.drum` or `.mtrack` models; engine and MCP are separate from Qt.

- The disk directory is now `src/`, mapped by setuptools to the importable `melody_notation` package. Never change public imports to `src.*`; preserve the stable CLI/MCP module paths.

## v0.4.5 custom drum tracks
- `.drum` v2 stores `tracks: [{id,name,sound}]`, `hits` keyed by stable track ID, and `next_track_number`; the v1 three-voice files must remain loadable.
- New tracks are not new synthesized sound engines: choose among kick, snare, hihat independently per row. The first three default track IDs remain `kick`, `snare`, `hihat` for backwards-compatible MCP calls.
- Keep standalone percussion export and `.mtrack` event generation iterating actual tracks, not the fixed `DRUM_VOICES` mapping.

## v0.4.6 custom-drum preview compatibility

- `.drum` v2 `hits` keys are persistent track IDs, not synth voice names. For sound synthesis always iterate `pattern.tracks` and resolve `track.sound` to `kick`/`snare`/`hihat` before invoking `render_drum_hit`.
- Keep tests for customized/deleted/renamed tracks when changing audio preview, export, arrangement or the GUI.
