"""Searchable Qt help window; compatible with legacy music-domain documentation."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QTextBrowser, QPushButton)

QT_WORKSPACE_GUIDE = """# PySide6 项目工作台

### 三种可编辑文件

- `.jianpu`：点击音符修改音高、八度、时值、临时升降号、装饰音及连音线。右上角可展开源码抽屉。
- `.drum`：16 步/小节的可点击鼓点网格。底鼓、军鼓、踩镲，原声／电子／8-bit 鼓组。
- `.mtrack`：多轨时间线。加入项目里的 `.jianpu` / `.drum`，调整片段开始拍、裁剪区间、反转、音量、轨道排序及静音/Solo。

### 工作台布局

- **左侧**：项目文件树、搜索、新建三种文件、文件/编辑/导出菜单与最近项目。
- **中央**：支持三种文件的多标签编辑器；关闭标签时检查未保存修改。
- **右侧**：上方为独立的内部试听播放器，下方为当前文档的编辑 Inspector。
- **顶部**：只显示产品名称和当前文件，不重复放置操作按钮。

### 操作流程

1. 左侧选择「打开」，选一个项目文件夹；或点 `+` 创建项目。
2. 点击「+ 简谱」、「+ 鼓点」或「+ 多轨」创建编辑文档。
3. 双击项目树中的文件在中央标签打开。可以同时打开多份音乐文件。
4. Ctrl+S 保存当前标签，在「文件/编辑/导出」菜单导出 MP3/WAV/MIDI/PNG。
5. 在右侧「试听控制」选择音色、倍速，点击播放；无需启动外部播放器。

### 快捷键

| 按键 | 功能 |
|---|---|
| Ctrl+N | 新简谱 |
| Ctrl+O | 打开文件 |
| Ctrl+S | 保存 |
| Ctrl+Shift+S | 另存为 |
| Ctrl+Z / Ctrl+Y | 撤销 / 重做 |
| Ctrl+Return | 从源码更新乐谱 |
| Ctrl+Tab | 下一个标签 |
| Ctrl+W | 关闭当前标签 |
| Ctrl+Shift+F | 搜索文件 |
| F1 | 帮助 |

### 兼容性与限制

当前是 PySide6 第一版。核心 MIDI/WAV/MP3/PNG、MCP 和文件格式沿用 v0.3.0。时间线可视化只展示片段，位置与裁剪通过数字控件修改，尚未实现鼠标拖拽片段。部分复杂简谱排版和视觉识谱仍处于 Beta 阶段。AI 对话工作台尚未加入。
"""

DRUM_GUIDE = """# 鼓点编辑教程

1. 新建 `.drum` 文件。选择原声 `acoustic`、电子 `electronic` 或 8-bit `gameboy`。
2. 在三行表格里点击格子：底鼓 Kick / 军鼓 Snare / 闭合踩镲 Hi-hat。
3. 每小节有 16 步，每步为 1/4 拍。可在顶部调整 BPM 和小节数。
4. 点击「应用设置」，在右侧试听，然后 Ctrl+S 保存。
5. 导出 MIDI 使用 General MIDI 鼓音符 36 / 38 / 42。自定义鼓组音色在 WAV/MP3 中体现，普通 MIDI 不携带波形。
"""

MULTITRACK_GUIDE = """# 多音轨编排教程

1. 在同一 Melody 项目中，准备一份或多份 `.jianpu`、`.drum` 文件。
2. 新建 `.mtrack` 多轨工程并打开，在中央点击「＋ 加入简谱/鼓点」。
3. 选择要加入的文件；可创建新音轨，也可以加入已选中的同类型轨道。
4. 选中音轨后，可在右侧设置音色、静音、Solo，或使用中央按钮上下调整轨道顺序。
5. 选中片段，设置 **开始拍、裁剪起、裁剪止、音量、反转**，点击「应用到片段」。
6. 裁剪是非破坏性的，不会改写源简谱和鼓点。反转是音符／鼓击**事件顺序反转**，不是音频波形倒放。
7. Ctrl+S 保存，然后试听混音、导出 WAV/MP3 或分轨 MIDI。

重要：多轨引用的是**已保存**的源素材，若其他标签中有未保存的修改，先保存相关素材再试听多轨。
"""


EN_WORKSPACE_GUIDE = """# PySide6 music workbench

- **.jianpu**: numbered notes; click a note to adjust pitch, duration, octave, articulation and slurs.
- **.drum**: three-voice 16-step drum grid, with acoustic, electronic and 8-bit kits.
- **.mtrack**: multitrack arrangements using saved .jianpu and .drum assets.

The left sidebar manages your project. The middle is a tabbed editor. The right panel holds playback and properties. Click the **gear beneath ?** at bottom left for theme, language and default save folder.

Use Ctrl+S to save, Ctrl+Shift+S for Save As, Ctrl+Space to play/pause and F1 for help. The score format uses `1..7` for degrees and `0` for rests. `6/2` is a half-beat note; `6/5` is invalid duration syntax. Export as MIDI, WAV, MP3, or a printable PNG. The score preview follows the theme but exported PNG defaults to white paper.
"""
EN_DRUM_GUIDE = """# Drum editor

Create a `.drum` file. Click cells in the Kick, Snare and Hi-hat rows to toggle hits. There are 16 steps per 4/4 bar. Select acoustic, electronic or Game Boy-style kit. Use Apply settings to commit tempo and length. Save with Ctrl+S; then preview or export MIDI/audio.
"""
EN_MULTITRACK_GUIDE = """# Multitrack editor

Create a `.mtrack` arrangement inside a project. Add existing saved `.jianpu` and `.drum` files as clips. Adjust a clip's starting beat, non-destructive trim, volume and reversal in the central panel. Tracks can be reordered, muted and soloed. Save before previewing/exporting the entire arrangement. Reversal changes event ordering, not the waveform itself.
"""

class QtHelpDialog(QDialog):
    def __init__(self,parent=None,language='zh'):
        super().__init__(parent)
        self.language=language
        self.setWindowTitle('Melody Notation · 帮助与教程' if language=='zh' else 'Melody Notation · Help')
        self.resize(900,620)
        self.guides=[('PySide6 快速入门',QT_WORKSPACE_GUIDE),('鼓点编辑',DRUM_GUIDE),
                     ('多音轨工程',MULTITRACK_GUIDE)]
        from .help_dialog import HELP_SECTIONS
        for section in HELP_SECTIONS:
            if section.title not in ('项目与多文件','快速入门'):
                self.guides.append((section.title,section.content))
        if language=='en':
            self.guides=[('Getting started', EN_WORKSPACE_GUIDE),
                         ('Drum editor', EN_DRUM_GUIDE),
                         ('Multitrack editor', EN_MULTITRACK_GUIDE)]
        layout=QVBoxLayout(self)
        header=QLabel('帮助与教程' if language=='zh' else 'Help & tutorials');header.setObjectName('Header');layout.addWidget(header)
        search=QLineEdit();search.setPlaceholderText('搜索标题和内容，例如：颤音、6/5、音轨、导出' if language=='zh' else 'Search: trill, 6/5, tracks, export…')
        layout.addWidget(search)
        row=QHBoxLayout()
        self.list=QListWidget();self.list.setMaximumWidth(230);row.addWidget(self.list)
        self.text=QTextBrowser();self.text.setOpenExternalLinks(True);row.addWidget(self.text,1)
        layout.addLayout(row,1)
        close=QPushButton('关闭' if language=='zh' else 'Close');close.clicked.connect(self.accept)
        bottom=QHBoxLayout();bottom.addStretch(1);bottom.addWidget(close);layout.addLayout(bottom)
        search.textChanged.connect(self.filter)
        self.list.currentRowChanged.connect(self._select)
        self.filter('')

    def filter(self,keyword):
        term=keyword.casefold().strip()
        self.list.blockSignals(True);self.list.clear()
        for title,body in self.guides:
            if term in (title+' '+body).casefold():self.list.addItem(title)
        self.list.blockSignals(False)
        if self.list.count():self.list.setCurrentRow(0);self._select(0)
        else:self.text.setPlainText('没有匹配的教程章节。' if self.language=='zh' else 'No matching topics.')

    def _select(self,index):
        if index<0:return
        title=self.list.item(index).text()
        for name,body in self.guides:
            if name==title:
                # Plain-text legacy sections stay readable; Markdown renders headings and examples.
                self.text.setMarkdown(body)
                break
