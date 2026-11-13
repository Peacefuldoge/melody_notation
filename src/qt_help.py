"""Searchable Qt help window; compatible with legacy music-domain documentation."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QTextBrowser, QPushButton)

QT_WORKSPACE_GUIDE = """# Melody Notation v0.5.10 · 快速入门

### 先新建项目，再创建音乐文件

1. 左侧「新建项目」选择保存位置并命名，或「打开项目」选择已有文件夹。
2. 在项目树中选择项目/子文件夹，点击「新建音乐文件」选择文件类型。
3. **简谱 `.jianpu`**：新建时只有空白小节，没有预置音符或休止符。点击「＋ 添加音符」开始，或编辑源码。
4. **鼓点 `.drum`**：新建时只有 Kick、Snare、Hi-hat 三条没有预置节奏的空轨。
5. **多轨 `.mtrack`**：加入项目内已经保存的 `.jianpu` / `.drum` 作为片段；支持音量、裁剪、反转、静音和 Solo。
6. Ctrl+S 保存，右侧试听后从「导出」菜单选择当前文档支持的格式。

### 工作区

- **左侧**：最近项目、项目文件树、文件搜索、右键菜单和新建入口。
- **中央**：多标签编辑器；简谱编辑器底部可展开实时演奏钢琴。
- **右侧**：试听控制和当前音符/音轨属性面板。
- **设置**：左下角「?」下方齿轮，调整主题、语言和默认保存位置。

### 项目树右键操作与删除

右键文件可选择「打开」「重命名」「删除文件（移至回收站）」。右键子文件夹可「重命名」「新建子文件夹」或「删除文件夹（移至回收站）」。右键项目根节点可以**删除整个项目**，但仅允许删除由 Melody 创建、带有效项目标识的目录。

每次删除都会要求确认。删除后相关打开标签会关闭，**未保存草稿不会自动写回**；删除文件夹同时移走全部子项。删除 `.jianpu` 或 `.drum` 不能自动修复别的 `.mtrack` 对它的引用。文件删除**不能使用 Ctrl+Z 撤销**，误删请先检查系统回收站，并做好独立备份。

### 快捷键

| 按键 | 操作 |
|---|---|
| Ctrl+N / Ctrl+O | 新建简谱 / 打开文件 |
| Ctrl+S / Ctrl+Shift+S | 保存 / 另存为 |
| Ctrl+Z / Ctrl+Y | 编辑撤销 / 重做，不恢复磁盘删除 |
| Ctrl+Tab / Ctrl+W | 切换标签 / 关闭标签 |
| Ctrl+Space | 试听播放 / 暂停 |
| Ctrl+Enter | 从源码更新谱面 |
| Ctrl+Shift+F | 聚焦项目文件搜索 |
| Ctrl+I | 属性面板展开 / 收起 |
| F1 | 本帮助窗口 |

### 使用边界

`.jianpu` 目前是单声部记谱模型；录制时的和弦可保存在原始 MIDI 导出中。MP3 导出需要 FFmpeg。视觉图片识谱处于 Beta 阶段且依赖用户授权的 API；AI 对话式多 Agent 创作面板并未在此版本内置。
"""

DRUM_GUIDE = """# 鼓点编辑（.drum）

1. 新建鼓点得到 **Kick（底鼓）／Snare（军鼓）／Hi-hat（踩镲）三条全空轨**，不会自动填入节奏。
2. 点击网格中的格子切换鼓击；每小节 16 步（在 4/4 下每步 1/4 拍）。
3. 点击「＋ 添加鼓轨」创建更多轨道；右键轨道名可**重命名、选择鼓声音色或删除单条鼓轨**，双击轨道名也能重命名。
4. 选择 acoustic / electronic / gameboy 鼓组，修改 BPM、小节数后点击「应用设置」。
5. 在右侧试听，按 Ctrl+S 保存；需要时导出 MIDI/WAV/MP3。

请区分两种删除：**鼓轨删除**只移除 `.drum` 文件内的一条音轨；**项目树右键删除文件**会把整个 `.drum` 文件移入系统回收站。鼓点 MIDI 使用标准鼓音符，不包含内置鼓组的波形音色。
"""

MULTITRACK_GUIDE = """# 多轨编排（.mtrack）

1. 先在同一个项目中建立并保存 `.jianpu` 和/或 `.drum` 源素材。
2. 新建 `.mtrack` 并在编辑器中「＋ 加入简谱/鼓点」，选择项目里的文件。
3. 将片段分配到音轨，调整片段的**开始拍、裁剪起止、音量与反转**；可移动轨道顺序、静音或 Solo。
4. 裁剪不会改写原始简谱或鼓点；反转是音符/鼓击的**事件顺序反转**，并非音频倒放。
5. 保存、试听混音，并可导出 WAV/MP3 或分轨 MIDI。

**重要：** 多轨引用磁盘上已保存的素材，不会自动读取其他标签的未保存草稿。删除或在文件管理器外移动源素材，可能导致片段失效；项目树右键删除文件也不会自动解除多轨引用。
"""

PERFORMANCE_GUIDE = """# 虚拟钢琴、键盘与 MIDI 录制

1. 打开 `.jianpu` 后，在编辑器底部展开虚拟钢琴。可以用鼠标点击琴键、电脑键盘或兼容的外接 MIDI 输入设备演奏。
2. 点击「输入设备」选择设备；点击「⚙ 演奏设置」管理键盘音色、监听音量、音域、设备刷新、自定义键位及录制 MIDI 导出。
3. 基础音域默认 C3–C5，窗口变宽可显示更多右侧琴键；可以切换起始八度。**外接 MIDI 音高不随虚拟琴键音域一起移调**。
4. 点击「开始录制」将演奏转换为简谱草稿，停止后检查节拍、休止符和量化结果，再保存 `.jianpu`。
5. 简谱是单声部的；想完整保存和弦、力度以及原始起止时间，请使用「演奏设置」里的**原始 MIDI 导出**，它不同于普通简谱 MIDI 导出。

实时演奏音色与右侧试听播放器的音色设置相互独立。缺少音频输出设备不一定妨碍 MIDI 事件采集，但监听可能没有声音。
"""

EN_WORKSPACE_GUIDE = """# Melody Notation v0.5.10 · Getting started

Create or open a project folder, then use **New Music File** to add a `.jianpu` score, `.drum` pattern, or `.mtrack` arrangement. New scores have empty measures with no preset notes or rests; new drums have three empty Kick/Snare/Hi-hat tracks.

The left sidebar contains the project tree, search, and recent projects. The center contains tabbed editors and the optional performance keyboard; the right side contains preview and properties.

**Right-click project tree:** rename files/folders or delete a file, subfolder, or whole project by moving it to the system Trash/Recycle Bin. The whole-project action is restricted to folders with a valid Melody project manifest. Confirmation is required; unsaved edits in deleted tabs will be lost. Deletion does not update references in other `.mtrack` arrangements and is **not reversible via Ctrl+Z**. Back up important projects.

**Shortcuts:** Ctrl+S save, Ctrl+Shift+S Save As, Ctrl+Tab next tab, Ctrl+W close tab, Ctrl+Space preview, Ctrl+Enter apply score source, Ctrl+Shift+F search, Ctrl+I inspector, F1 help.

MP3 requires FFmpeg. Image-to-score is a consent-based API-powered Beta. AI conversation-based multitrack generation is not built in yet.
"""
EN_DRUM_GUIDE = """# Drum editor

New `.drum` files contain empty Kick, Snare and Hi-hat tracks with no preset hits. Click cells in the 16-step grid. Add tracks with **+**, then right-click a track name to rename it, change the drum voice or remove that track. Choose acoustic/electronic/gameboy sounds, apply tempo/bar settings, save with Ctrl+S and export/preview. Deleting a track is not the same as deleting the `.drum` file from the project tree.
"""
EN_MULTITRACK_GUIDE = """# Multitrack editor

Add saved `.jianpu` or `.drum` sources to an `.mtrack` arrangement. Edit beat position, nondestructive trim, gain, event-order reversal, mute/solo and track order. Save, preview and export. If a referenced source is deleted or moved outside the app, its clips may no longer resolve.
"""
EN_PERFORMANCE_GUIDE = """# Piano and MIDI recording

Expand the performance piano below a score. Play using the mouse, computer keyboard or a compatible MIDI controller. Use **Performance Settings** to choose instrument, listening volume, keyboard range, key mappings and raw MIDI export. Recording captures a monophonic score representation while raw MIDI export can preserve chords, velocities and timing. Preview instrument and live-performance instrument are independent.
"""

class QtHelpDialog(QDialog):
    def __init__(self,parent=None,language='zh'):
        super().__init__(parent)
        self.language=language
        self.setWindowTitle('Melody Notation · 帮助与教程' if language=='zh' else 'Melody Notation · Help')
        self.resize(900,620)
        self.guides=[('快速入门与项目删除',QT_WORKSPACE_GUIDE),('鼓点编辑',DRUM_GUIDE),
                     ('多音轨工程',MULTITRACK_GUIDE),('钢琴与 MIDI 录制',PERFORMANCE_GUIDE)]
        from .help_dialog import HELP_SECTIONS
        for section in HELP_SECTIONS:
            if section.title not in ('项目与多文件','快速入门'):
                self.guides.append((section.title,section.content))
        if language=='en':
            self.guides=[('Getting started', EN_WORKSPACE_GUIDE),
                         ('Drum editor', EN_DRUM_GUIDE),
                         ('Multitrack editor', EN_MULTITRACK_GUIDE),
                         ('Piano and MIDI recording', EN_PERFORMANCE_GUIDE)]
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
