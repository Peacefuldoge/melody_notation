---
name: melody-notation
description: Create, edit, transcribe and export Chinese numbered music notation (简谱/Jianpu) as audio WAV/MP3, MIDI or PNG using Melody Notation tools. Use when users discuss numbered note scores or sheet-to-MIDI tasks.
---

# Melody Notation

Use `melody-notation` MCP tools if configured; otherwise use the `melody-notation` Python CLI.

## Score text grammar

Use a UTF-8 `.jianpu` file with metadata (`title`, `key`, `time`, `bpm`), then `notes:` and measures separated with `|`.

- `1` through `7` are scale degrees (middle octave), `0` is rest.
- `1'` denotes one octave higher; `5,` denotes one octave lower.
- `3/2` is eighth note (0.5 beat); `3/4` sixteenth (0.25 beat); `3.` dotted quarter (1.5 beats); `3./2` dotted eighth (0.75 beats).
- `-` lengthens previous note/rest by 1 beat.
- Standalone `(` and `)` mark notation slur start and end; a slur may cross measures, but cannot overlap/nest another slur or include a rest.
- `R` means one full bar of rest.
- A valid 4/4 measure has exactly four beats; check every measure before export.
- Accidentals supported as `#4` or `b7`. Add ornaments as `5{tr}`, `5{mordent}`, `5{lower_mordent}`, `5{turn}`, `5{staccato}`, `5{accent}`, `5{tenuto}`, or `5{tremolo}`. Rest notes cannot carry ornaments.

## Workflow

1. `create_score` or `inspect_score` before editing.
2. Use `edit_note` to modify a specific note (degree, octave, beats, accidental), or `replace_measure` for an entire measure. Use `create_slur` / `remove_slur` for notation slurs; `insert_note` / `delete_note` for event count changes. Request confirmation before writing existing files (`overwrite=true`).
3. Validate all measure durations.
4. Ask for the intended instrument; `list_instruments` returns supported presets.
5. Use `export_audio` for a preview, `export_midi` for editable DAW notes, `export_png` for notation.
6. For image input, use `transcribe_image` only with explicitly configured vision model credentials. Return draft plus `uncertainty`. **Do not present OCR as exact**. The user must approve uncertain digits, dots, beams, time signatures, and rests before final exports.
7. Do not invent accompaniment. A `.jianpu` file is a monophonic melody; a `.mtrack` can layer multiple edited melody and drum sources.

## Important limitations

- Built-in oscillator instruments sound approximate. For realistic timbres use FluidSynth and a properly licensed SF2 SoundFont.
- The PNG renderer is a minimal text-like numbered score, not full publishing-quality layout; it draws single-level slur arcs but does not implement ties or multi-voice notation.
- Multi-page/crowded score OCR is experimental and requires manual correction.
- v0.3 multitrack/drum editors run as independent windows, not central score tabs; no piano-roll, audio waveform reversal, or AI chat yet.

## v0.2 notation editing API

- MCP note/bar locations are **one-indexed**. `edit_note(path, measure_number, note_number, degree, octave, beats, accidental, ornament, overwrite=true)` accepts omitted properties.
- `create_slur(path, start_measure, start_note, end_measure, end_note, overwrite=true)` draws an arc from an earlier note to a later note, including across measures.
- `remove_slur(path, measure_number, note_number, overwrite=true)` removes the slur enclosing the selected note.
- A slur is a **phrase mark**, not a tie; it does not extend MIDI note durations.
- Temporary bar-duration errors are permissible while editing; final exports require strict validation.
- For click-to-edit, launch `python -m melody_notation.cli gui` and select individual numbers on the rendered score.

## v0.2.4 preview

- `gameboy` instrument uses a custom 8-bit-style pulse and wavetable synth for WAV/MP3, with General MIDI Lead 1 (square) approximation for MIDI.
- GUI speed selection is 1.00×/1.25×/1.50×/1.75×/2.00×; preview only, it does not modify score BPM or normal exports.
- Ornament performance is expanded into MIDI note events, with diatonic neighbors and deterministic timing; not a full engraving/performance semantics implementation.

## Bundled score examples (v0.2.5)

The GUI's 文件 → 内置示例 menu contains `荒` (`examples/huang.jianpu`) in addition to existing examples.
The sample is a manually transcribed, editable excerpt from user-provided images: 41 visible bars, 1=A, 4/4, BPM 88, and `key_changes: 25=Bb`. The original image explicitly skips the instrumental break; its missing notes and duration must not be invented. Lyrics and composer/performer metadata are omitted.

`.jianpu` supports an optional header `key_changes: 25=Bb` for a new tonic starting at the specified 1-based bar. The parser, renderer, MIDI exporter and local synth respect this modulation.

## v0.2.7 project workstation

- A project is a normal directory containing multiple editable `.jianpu` files, optionally grouped into subfolders. It may include `.melody-project.json` metadata.
- GUI has a left project tree, central document tabs, right note Inspector and bottom transport. Each tab preserves independent undo/redo and pending source drafts.
- New/other projects use the same existing MIDI/audio/PNG engines. v0.3 adds separate `.mtrack` composition and `.drum` step-sequencer windows; AI Chat UI is not implemented.
- When an MCP agent must work on files in a particular GUI project, configure `MELODY_WORKSPACE` to that project directory. The running GUI does not automatically sync its unsaved in-memory document to MCP (nor reread external writes); ask the human to save/reopen when coordinating changes.

## Harmony knowledge (v0.2.13)

For chord qualities, emotional color and harmonization, invoke the project `melody-harmony` Skill (`.agents/skills/melody-harmony/SKILL.md`). Do not claim the existing monophonic `.jianpu` engine can synthesize simultaneous harmony. For DeepSeek Harness, call MCP `list_harmony_topics` and `read_harmony_guide(topic)` to retrieve the same reference in a read-only way.

## v0.3 multi-track and drum workflow

Three project document types: `.jianpu` (notation), `.drum` (editable 4/4 rhythm grid, 16 steps/bar), `.mtrack` (multi-track clip arrangement). The GUI File menu creates each type. Double-click an asset in the project navigator to open its editor.

1. `list_drum_kits()` lists `acoustic`, `electronic`, `gameboy` and the kick/snare/closed-hi-hat GM note numbers. Use `create_drum_pattern` and `toggle_drum_hit` to edit grid steps; **steps are zero-indexed**, with 0..15 in each 4/4 bar. `inspect_drum_pattern` is read-only.
2. Use `create_arrangement` to create a `.mtrack`. `add_arrangement_clip` attaches a project `.jianpu` or `.drum` and creates a new track by default (`track_index=-1`), or adds to an existing same-kind track. `start_beat` places the clip on the project beat timeline.
3. `inspect_arrangement` before modifying, then `edit_arrangement_clip` using **zero-indexed** `track_index` and `clip_index`. Set `trim_start` and `trim_end` as *source beats*, `start_beat` as *arrangement beats*, `reversed=true` to reverse **note/hit chronology** (not PCM waveform samples), and `gain` from 0 to 2. `clear_trim_end=true` restores the full clip length.
4. Use `reorder_arrangement_track(delta=-1|1)` for track order. Set mute and solo in the PySide6 multitrack editor or the arrangement JSON file. An arrangement plays all non-muted tracks, or only solo tracks if any are soloed.
5. `export_multitrack_midi` creates a multi-instrument MIDI with General MIDI percussion-channel-10 drums; `export_multitrack_audio` mixes the actual built-in 3-kit drum sounds to WAV/MP3. `export_drum_pattern` exports individual patterns.
6. All project paths must be inside the configured `MELODY_WORKSPACE`, and modifications of existing files require explicit approval and `overwrite=true`. Save/reopen GUI files before an Agent rewrites them; GUI unsaved drafts do not automatically sync to MCP.

Do not claim `.mtrack` supports automatic harmony generation or full sample-based reverse playback. Consult `docs/MULTITRACK_DRUMS.md` for schema and constraints.
