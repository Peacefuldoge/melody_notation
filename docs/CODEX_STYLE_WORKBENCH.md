# Melody Notation v0.4.2 — Codex-style application shell

## Intent

Use the **information architecture** of a Codex/ChatGPT desktop workbench, without copying ChatGPT branding, its conversation pane, or its color palette. The application remains a music editor, not a chat application.

```
┌────────────────────── File · Edit · View · Export · Help ─────────────────┐
│                         Selected file                           Inspector │
├────┬────────────────────┬──────────────────────────┬────────────────────┤
│    │ Melody Notation    │  Tabs: score/drums/track │ Preview & playback │
│ ≡  │ + New music file   │                          │                    │
│ +  │ Search             │                          │ Note / beat / clip │
│ ⌕  │ Recent projects    │    Editable music canvas │ property inspector │
│    │ Projects           │                          │                    │
│    │  ↳ subfolders     │                          │                    │
│ ?  │  ↳ .jianpu        │                          │                    │
│ ⚙  │  ↳ .drum          │                          │                    │
└────┴────────────────────┴──────────────────────────┴────────────────────┘
```

## Rules

1. A permanent **54 px icon rail** provides project toggle, new-file menu, search, help and settings. Settings stays immediately under Help at the bottom.
2. The adjacent project panel shows recent projects and the **current project's hierarchy**, with a single `+ New music file` menu and the existing context menu. It collapses without hiding the rail.
3. The menu bar holds File, Edit, View, Export and Help. No duplicate File/Edit/Export dropdown in the project panel.
4. The central document tabs retain `.jianpu`, `.drum`, `.mtrack` editors. A narrow chrome row shows the current document. Nothing is replaced by a mock chat area.
5. The inspector can be toggled with the top-right icon, View menu or Ctrl+I. All edits remain in each document widget.
6. Theme tokens, printed PNG behavior, settings dialog, bilingual UI and native Windows material remain from v0.4.1.
7. No persistence schema changes, no change to audio/MIDI/MCP/score parser. Project file formats stay backward compatible.

## Validation

- Core pytest suite is independent of PySide6 and can run everywhere.
- `python devtools/qt_codex_layout_smoke.py` uses a disposable project and checks multi-tab editing, sidebar/inspector toggles, themes and search. Requires PySide6 and display or `QT_QPA_PLATFORM=offscreen`.
- Final Windows validation should include launch, window resize, touchpad scroll, QMediaPlayer playback, save/reopen, and QSettings persistence. Do not treat static/mockup previews as actual Qt screenshots.
