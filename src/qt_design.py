"""PySide6 desktop design tokens, high-DPI line icons, localized UI and native chrome.

Native material is best-effort: Win11 DWM; all other systems use an
accessible, tinted translucent panel fallback. Core music files are unaffected.
"""
from __future__ import annotations

import sys
from pathlib import Path

COLORS = {
    'light': dict(window='#F4F7FA', surface='#FFFFFF', soft='#F0F4F8', paper='#FFFFFF',
                  ink='#1A2939', secondary='#64758A', line='#DDE5ED', accent='#3275A9',
                  on_accent='#FFFFFF', selected='#DDEFFC', error='#B84B48', track='#DDEBFA',
                  glass='rgba(255,255,255,214)', glass_edge='#DFE6ED'),
    'dark': dict(window='#151C26', surface='#222D3A', soft='#2B3847', paper='#293544',
                 ink='#E9F2FC', secondary='#A8B8C9', line='#384758', accent='#8CB8E9',
                 on_accent='#172331', selected='#344F69', error='#F0A5AA', track='#3B5875',
                 glass='rgba(34,45,58,218)', glass_edge='#455568'),
    'beige': dict(window='#F4F0E7', surface='#FFFDF8', soft='#ECE6D9', paper='#FAF6EB',
                  ink='#302D27', secondary='#756C5E', line='#D9CFBD', accent='#84603E',
                  on_accent='#FFFFFF', selected='#EADCC6', error='#A43D3A', track='#E6D6BD',
                  glass='rgba(255,253,248,218)', glass_edge='#DED5C8'),
    'olive': dict(window='#EDEFE5', surface='#F8F9F3', soft='#E3E8D9', paper='#F1F3E8',
                  ink='#2E372C', secondary='#687661', line='#CED6C3', accent='#64794B',
                  on_accent='#FFFFFF', selected='#DDE7CB', error='#A34842', track='#D3E0C4',
                  glass='rgba(248,249,243,216)', glass_edge='#CDD7C2'),
}
THEME_NAMES = {
    'light': ('浅色 · Light', 'Light'),
    'dark': ('深色 · Dark', 'Dark'),
    'beige': ('米色 · Beige', 'Beige'),
    'olive': ('橄榄绿 · Olive', 'Olive'),
}

# Translation keys are the actual, visible Chinese UI strings in the Qt workbench.
# Never translate user filenames, instrument identifiers or source notation.
EN = {
    '创作工作台  /  PySide6': 'Music workbench  /  PySide6',
    '未打开项目': 'No project open', '项目': 'Projects', '打开': 'Open',
    '⌕ 搜索项目文件': 'Search project files', '搜索项目文件': 'Search project files',
    '＋ 简谱': '+ Score', '＋ 鼓点': '+ Drums', '＋ 多轨': '+ Tracks',
    '文件 / 编辑 / 导出 ▾': 'File / Edit / Export ▾', '项目文件': 'Project files',
    '＋ 新建子文件夹': '+ New folder', '最近项目': 'Recent projects',
    '试听控制': 'Playback', '▶ 播放': 'Play', '▶ 继续': 'Resume', 'Ⅱ 暂停': 'Pause',
    '■ 停止': 'Stop', '音色': 'Instrument', '倍速': 'Speed',
    '编辑属性': 'Properties', '选择乐谱音符、鼓点或音轨，以编辑属性。': 'Select a note, beat or track to edit.',
    '尚未选中音符': 'No note selected', '请点击谱面中的音符': 'Click a note in the score',
    '音级 / 休止': 'Degree / Rest', '八度': 'Octave', '时值': 'Duration',
    '升降号': 'Accidental', '演奏记号': 'Articulation', '应用到音符': 'Apply to note',
    '后插入': 'Insert after', '删除音符': 'Delete note', '连音线': 'Slur',
    '设起点': 'Set start', '连接': 'Connect', '移除': 'Remove',
    '选中轨道后可更改音色、静音或 Solo。\n片段裁剪、反转和移动在中央编辑。':
        'Select a track to change instrument, mute or solo.\nTrim, reverse and move clips in the editor.',
    '设置轨道音色': 'Set track instrument', '静音': 'Mute',
    '点击中央的步进格编写节奏。\n底鼓 Kick / 军鼓 Snare / 踩镲 Hi-hat。':
        'Click the step grid to create beats.\nKick / Snare / Hi-hat.',
    '鼓组切换': 'Drum kit', '应用鼓组': 'Apply drum kit',
    '简谱': 'Score', '每行小节': 'Bars per row', '显示源码': 'Show source',
    '隐藏源码': 'Hide source', '钢琴键盘 · 演奏与录制': 'Piano / Performance',
    '键位设置': 'Key mapping', '输入设备': 'Input device', '监听音量': 'Monitor level',
    '导出录制 MIDI': 'Export take MIDI', '● 开始录制': 'Record', '■ 结束录制': 'Stop recording', '简谱源码（Ctrl+Enter 应用）': 'Score source (Ctrl+Enter to apply)',
    '从源码更新乐谱': 'Apply source to score', '鼓点音序器': 'Drum sequencer',
    '名称': 'Name', '小节': 'Bars', '应用设置': 'Apply settings',
    '左键点亮／关闭鼓点 · 每小节 16 步 · 底鼓、军鼓、踩镲 · 可导出分轨 MIDI':
        'Click to toggle beats · 16 steps/bar · Kick, Snare, Hi-hat · MIDI export',
    '多音轨编排': 'Multitrack arrangement', '工程名称': 'Arrangement name',
    '应用': 'Apply', '片段编辑': 'Clip editor', '删除片段': 'Delete clip',
    '反转': 'Reverse', '应用到片段': 'Apply to clip',
    '文件': 'File', '编辑': 'Edit', '导出': 'Export', '工具': 'Tools', '帮助': 'Help',
    '新建项目': 'New project', '打开项目': 'Open project', '打开音乐文件': 'Open music file',
    '新建简谱': 'New score', '新建鼓点': 'New drums', '新建多轨工程': 'New multitrack',
    '保存': 'Save', '另存为': 'Save as', '关闭标签': 'Close tab',
    '图片识谱（Beta）': 'Import from image (Beta)', '内置示例': 'Built-in samples',
    '山风': 'Mountain Breeze', '荒': 'Wilderness', '可视化示例': 'Editor sample',
    '像素冒险': 'Pixel Adventure', '撤销': 'Undo', '重做': 'Redo',
    '检查节拍 / 文件': 'Validate score / file', '重命名项目文件': 'Rename project file',
    '新建子文件夹': 'New folder', '使用教程 F1': 'Tutorial  F1',
    '展开／收起项目侧栏': 'Toggle projects sidebar',
    '主题和界面': 'Appearance', '语言': 'Language', '默认保存目录': 'Default save directory',
    '浏览…': 'Browse…', '恢复默认': 'Reset', '取消': 'Cancel', '确定': 'Apply',
    '设置': 'Settings', '跟随软件默认目录': 'Use application default',
    '外观与偏好设置': 'Appearance & preferences',
    '主题': 'Theme', '音轨': 'Track', '选择项目文件夹': 'Choose project folder',
    '选择项目存放位置': 'Choose project location',
    '请选择目录': 'Choose directory', '深浅主题': 'Themes',
    '设置会保存到当前用户，重启后仍然生效。': 'Preferences are saved for your Windows user.',
    '窗口特效': 'Window material', '自动（系统支持时使用毛玻璃）': 'Automatic (native when available)',
    '关闭系统毛玻璃': 'Disable native material',
    '未命名': 'Untitled', '最近项目': 'Recent projects',
    '新建音乐文件': 'New music file', '＋ 新建音乐文件': '+ New music file',
    '项目操作': 'Project actions', '展开／收起属性面板': 'Toggle properties panel',
    '展开／收起项目侧栏': 'Toggle projects sidebar',
    '视图': 'View', '项目文件': 'Project files', '准备就绪': 'Ready',
}


def translated(text: str, language: str) -> str:
    if language != 'en': return text
    if text in EN: return EN[text]
    if text.endswith(' 拍'):
        return text[:-2] + ' beats'
    return text


def stylesheet(theme: str) -> str:
    c=COLORS[theme]
    return f"""
    * {{font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif; font-size: 12px;}}
    QWidget {{ background: {c['window']}; color: {c['ink']}; }}
    QWidget#Panel, QWidget#Sidebar, QWidget#Inspector, QWidget#Player {{
        background-color: {c['glass']}; border: 1px solid {c['glass_edge']};
        border-radius: 13px; }}
    QWidget#MainSurface {{background: {c['window']}; border: none;}}
    QWidget#KeyboardPanel {{background: {c['window']};
        border-top: 1px solid {c['line']};}}
    QWidget#KeyboardContents {{background: {c['glass']};
        border: 1px solid {c['glass_edge']};border-radius: 10px;}}
    QWidget#KeyboardToolbar, QWidget#KeyboardControlGroup {{background: transparent; border: none;}}
    QToolButton#KeyboardToggle {{background: transparent;
        color: {c['secondary']};border: none;
        text-align: left;font-weight: 600;padding: 4px 8px;}}
    QToolButton#KeyboardToggle:hover {{color:{c['ink']};background:{c['soft']};}}
    QPushButton#RecordButton {{background:{c['soft']};color:{c['ink']};}}
    QPushButton#RecordingActive {{background:{c['error']};
        color: #FFFFFF;border-color:{c['error']};font-weight:600;}}
    QLabel, QCheckBox {{ background: transparent; border: none; }}
    QLabel#Header {{font-size: 17px; font-weight: 600;}}
    QLabel#Muted {{color: {c['secondary']};}}
    QGroupBox {{border: 1px solid {c['line']}; border-radius: 12px;
        margin-top: 16px; padding: 13px 10px 10px; background: {c['glass']};}}
    QGroupBox::title {{subcontrol-origin: margin; left: 13px; padding: 0 5px;}}
    QFrame#InspectorCard {{border: 1px solid {c['line']}; border-radius: 12px;\n        background: {c['glass']};}}
    QPushButton, QToolButton {{background: {c['soft']}; border: 1px solid {c['line']};
        border-radius: 9px; padding: 6px 11px; min-height: 26px;}}
    QToolButton#IconButton {{padding: 5px; min-width: 28px; min-height: 28px;}}
    /* Never add Qt's extra menu chevron next to our explicit plus/more icons. */
    QToolButton::menu-indicator {{image: none; width: 0px; height: 0px;}}
    QPushButton:hover, QToolButton:hover {{background: {c['selected']}; border-color: {c['accent']};}}
    QPushButton:pressed, QToolButton:pressed {{background: {c['track']};}}
    QPushButton#Primary {{background: {c['accent']}; color: {c['on_accent']};
        border-color: {c['accent']}; font-weight: 600;}}
    QPushButton#Primary:hover {{border-color: {c['ink']};}}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
        border: 1px solid {c['line']}; border-radius: 8px;
        background: {c['surface']}; color: {c['ink']}; padding: 6px 8px;
        selection-background-color: {c['selected']};}}
    QComboBox::drop-down {{border: 0px; width: 22px;}}
    /* Soft, borderless spin controls replace Windows' bevelled stepper buttons.
       Arrow clicks and keyboard/wheel editing remain native and accessible. */
    QSpinBox, QDoubleSpinBox {{padding-right: 22px;}}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border; subcontrol-position: top right;
        width: 19px; border: none; background: transparent;
        border-top-right-radius: 7px;}}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border; subcontrol-position: bottom right;
        width: 19px; border: none; background: transparent;
        border-bottom-right-radius: 7px;}}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
        background: {c['soft']};}}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed,
    QDoubleSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed {{
        background: {c['selected']};}}
    QTreeWidget, QTableWidget, QGraphicsView, QListWidget {{background: {c['surface']};
        color: {c['ink']}; border: 0px; gridline-color: {c['line']}; outline: none;}}
    QTreeWidget::item {{padding: 7px 5px; border-radius: 6px;}}
    QTreeWidget::item:selected, QTableWidget::item:selected {{background: {c['selected']}; color: {c['ink']};}}
    QTreeWidget::item:hover {{background: {c['soft']};}}
    QHeaderView::section {{background: {c['soft']}; color: {c['secondary']};
        padding: 7px; border: none; border-right: 1px solid {c['line']};}}
    QTabWidget::pane {{border: 0; background: {c['window']};}}
    QTabBar::tab {{background: {c['soft']}; color: {c['secondary']};
        padding: 10px 18px; margin: 2px 3px 0; border-radius: 9px 9px 0 0;}}
    QTabBar::tab:selected {{background: {c['surface']}; color: {c['ink']};}}
    QTabBar::tab:hover {{background: {c['selected']};}}
    QSplitter::handle {{background: {c['line']}; width: 1px;}}
    QScrollArea {{border: none; background: {c['window']};}}
    QMenu {{background: {c['surface']}; border: 1px solid {c['line']}; padding: 7px;}}
    QMenu::item {{padding: 8px 26px; border-radius: 6px;}}
    QMenu::item:selected {{background: {c['selected']};}}
    QStatusBar {{background: {c['window']}; color: {c['secondary']};
        border: none; border-top: 1px solid {c['line']};}}
    QLabel#VersionLabel {{background: transparent; color: {c['secondary']};
        border: none; font-size: 11px; padding: 0 9px;}}
    QSlider::groove:horizontal {{background: {c['line']}; height: 5px; border-radius: 2px;}}
    QSlider::handle:horizontal {{background: {c['accent']}; width: 13px;
        margin: -5px 0; border-radius: 6px;}}
    QScrollBar:vertical {{background: {c['window']}; width: 9px;}}
    QScrollBar::handle:vertical {{background: {c['line']}; border-radius: 4px; min-height: 25px;}}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{height: 0px;}}
    /* DAW timeline: integrated fixed track column and clip property strip. */
    QWidget#DAWWorkspace {{background: {c['surface']};
        border: 1px solid {c['line']}; border-radius: 9px;}}
    QWidget#DAWTrackColumn, QWidget#DAWTrackRows {{background: {c['soft']};
        border: none; border-right: 1px solid {c['line']};}}
    QLabel#DAWTrackStrip {{background: {c['soft']}; color: {c['secondary']};
        border-bottom: 1px solid {c['line']};font-weight:600;}}
    QWidget#DAWTrackRow {{background: {c['soft']};
        border-bottom: 1px solid {c['line']};}}
    QWidget#DAWTrackSelected {{background: {c['selected']};
        border-bottom: 1px solid {c['line']};}}
    QPushButton#DAWTrackName {{background: transparent; border: none;
        padding: 0; min-height: 20px; text-align: left; font-weight: 600;}}
    QPushButton#DAWTrackName:hover {{color: {c['accent']};}}
    QToolButton#DAWSmallButton, QToolButton#DAWOnButton {{
        min-height: 22px;min-width: 23px;padding: 2px;border-radius: 5px;}}
    QToolButton#DAWOnButton {{background: {c['accent']}; color: {c['on_accent']};
        border: 1px solid {c['accent']};font-weight:700;}}
    QFrame#DAWClipPanel {{background: {c['glass']};
        border: 1px solid {c['line']};border-radius: 9px;}}
        /* Three-column workbench: a quiet icon rail, project list and document tabs. */
    QMenuBar#AppMenuBar {{background: {c['window']}; color: {c['secondary']};
        border-bottom: 1px solid {c['line']}; padding: 4px 6px;}}
    QMenuBar#AppMenuBar::item {{padding: 5px 11px; border-radius: 6px;}}
    QMenuBar#AppMenuBar::item:selected {{background: {c['soft']}; color: {c['ink']};}}
    QWidget#NavShell {{background: {c['window']}; border: none;}}
    QWidget#NavRail {{background: {c['soft']};
        border-right: 1px solid {c['line']};}}
    QWidget#Sidebar {{background: {c['window']};
        border: none; border-right: 1px solid {c['line']};border-radius:0;}}
    QLabel#BrandName {{font-size: 15px; font-weight: 600;
        padding: 5px 3px 10px;}}
    QLabel#SectionLabel {{color: {c['secondary']};font-size: 11px;
        font-weight: 500; padding: 8px 3px 3px;}}
    QToolButton#NewItemButton {{text-align: left;
        background: {c['soft']};border: 1px solid {c['line']};
        border-radius: 9px; min-height: 30px; padding: 5px 12px;}}
    QToolButton#NewItemButton:hover {{background:{c['selected']};}}
    QToolButton#ProjectMore {{border: none; background: transparent;}}
    QToolButton#ProjectMore:hover {{background:{c['soft']};}}
    QLineEdit#ProjectSearch {{background: {c['soft']};border: 1px solid transparent;
        padding: 8px 10px; border-radius: 8px;}}
    QLineEdit#ProjectSearch:focus {{border:1px solid {c['accent']};}}
    QListWidget#RecentProjectList, QTreeWidget#ProjectTree {{background:{c['window']};
        border: none; outline: none;}}
    QListWidget#RecentProjectList::item, QTreeWidget#ProjectTree::item {{
        padding: 7px 8px; margin: 1px 0; border-radius: 7px;}}
    QListWidget#RecentProjectList::item:selected, QTreeWidget#ProjectTree::item:selected {{
        background: {c['selected']};color:{c['ink']};}}
    QListWidget#RecentProjectList::item:hover, QTreeWidget#ProjectTree::item:hover {{
        background:{c['soft']};}}
    QTabWidget#EditorTabs {{background:{c['window']};border:none;}}
    QTabWidget#EditorTabs::pane {{border:none;background:{c['window']};}}
    QTabWidget#EditorTabs QTabBar::tab {{background: transparent;
        padding: 10px 20px; margin: 0 1px; border-radius: 0;
        border-bottom:2px solid transparent;}}
    QTabWidget#EditorTabs QTabBar::tab:selected {{background: {c['surface']};
        color:{c['ink']}; border-bottom:2px solid {c['accent']};}}
    QWidget#Inspector {{background:{c['window']};border:none;
        border-left: 1px solid {c['line']};border-radius:0;}}
    /* Inspector contents use only compact cards, no colored filler panels. */
    QStackedWidget#PropertyStack, QWidget#NoteInspector,
    QWidget#TrackInspector, QWidget#DrumInspector {{
        background: transparent; border: none;}}
    QToolButton#IconButton {{border: 1px solid transparent;
        background:transparent;border-radius:8px;}}
    QToolButton#IconButton:hover {{background:{c['selected']};border:1px solid transparent;}}
    """


def line_icon(name: str, color: str, size: int=20):
    """Vector-like line icons rendered at 3x DPR; no external icon/font assets."""
    from PySide6.QtCore import Qt, QPointF, QSize
    from PySide6.QtGui import QIcon, QColor, QPixmap, QPainter, QPen, QPainterPath
    pmap=QPixmap(72,72);pmap.setDevicePixelRatio(3);pmap.fill(Qt.GlobalColor.transparent)
    p=QPainter(pmap);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen=QPen(QColor(color));pen.setWidthF(1.75)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush)
    def line(a,b,c,d):p.drawLine(QPointF(a,b),QPointF(c,d))
    if name=='menu':
        for y in (6,12,18):line(4,y,20,y)
    elif name=='panel-left':
        p.drawRoundedRect(4,4,17,16,2,2)
        line(9,4,9,20)
    elif name=='panel-right':
        p.drawRoundedRect(4,4,17,16,2,2)
        line(15,4,15,20)
    elif name=='more':
        for x in (6,12,18):p.drawEllipse(QPointF(x,12),1,1)
    elif name=='help':
        p.drawEllipse(QPointF(12,12),9,9)
        path=QPainterPath(QPointF(9,9));path.cubicTo(9,5.5,16,5.5,16,9)
        path.cubicTo(16,11,12,11.5,12,14);p.drawPath(path)
        p.drawPoint(QPointF(12,17))
    elif name=='settings':
        # Round gear teeth; antialiased, consistent with all other glyphs.
        import math
        center=QPointF(12,12)
        for n in range(8):
            a=n*math.pi/4
            line(12+8*math.cos(a),12+8*math.sin(a),12+10.4*math.cos(a),12+10.4*math.sin(a))
        p.drawEllipse(center,7.6,7.6);p.drawEllipse(center,2.65,2.65)
    elif name=='folder':
        path=QPainterPath(QPointF(3,7));path.lineTo(10,7);path.lineTo(12,9)
        path.lineTo(21,9);path.lineTo(21,19);path.lineTo(3,19);path.closeSubpath();p.drawPath(path)
    elif name=='plus':
        line(12,4,12,20);line(4,12,20,12)
    elif name=='play':
        path=QPainterPath(QPointF(8,5));path.lineTo(19,12);path.lineTo(8,19);path.closeSubpath();p.drawPath(path)
    elif name=='pause':
        line(9,6,9,18);line(15,6,15,18)
    elif name=='stop':
        p.drawRoundedRect(6,6,12,12,2,2)
    elif name=='search':
        p.drawEllipse(QPointF(10,10),6,6);line(14.5,14.5,20,20)
    elif name=='note':
        line(15,5,15,16);line(15,5,20,6);line(20,6,20,9)
        p.drawEllipse(QPointF(11,17),3.5,2.4)
    elif name=='drum':
        p.drawRoundedRect(5,5,14,14,3,3)
        for x in (9,15):
            for y in (9,15):p.drawEllipse(QPointF(x,y),0.8,0.8)
    elif name=='tracks':
        for y in (6,12,18):
            p.drawRoundedRect(4,y-2,16,4,1.5,1.5)
    elif name=='save':
        p.drawRoundedRect(4,4,16,16,2,2);p.drawRect(8,4,8,6);p.drawRect(8,14,8,6)
    else:
        p.drawEllipse(QPointF(12,12),8,8)
    p.end()
    return QIcon(pmap)


def style_icon_button(button, glyph: str, theme: str, tooltip: str=''):
    from PySide6.QtCore import QSize
    button.setText('');button.setObjectName('IconButton')
    button.setIcon(line_icon(glyph, COLORS[theme]['secondary']))
    button.setIconSize(QSize(20,20))
    button.setFixedSize(40,40)
    if tooltip:button.setToolTip(tooltip)


def translate_widgets(parent, language: str):
    """Re-label existing live widgets in place without rebuilding (preserves edits)."""
    from PySide6.QtWidgets import QLabel, QPushButton, QToolButton, QGroupBox, QCheckBox, QLineEdit, QComboBox
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget
    items = [parent] + parent.findChildren(QWidget)
    for w in items:
        if w.property('_melody_no_translate'):
            continue
        if isinstance(w,(QLabel,QPushButton,QToolButton,QGroupBox,QCheckBox)):
            original=w.property('_melody_zh_text')
            if original is None:
                original=w.title() if isinstance(w,QGroupBox) else w.text()
                w.setProperty('_melody_zh_text',original)
            text=translated(original,language)
            if isinstance(w,QGroupBox):w.setTitle(text)
            else:w.setText(text)
        if isinstance(w,QLineEdit):
            hint=w.property('_melody_zh_hint')
            if hint is None:
                hint=w.placeholderText();w.setProperty('_melody_zh_hint',hint)
            w.setPlaceholderText(translated(hint,language))
        if isinstance(w,QComboBox) and w.objectName()=='DurationCombo':
            for i in range(w.count()):
                raw=str(w.itemData(i))
                if raw in ('None',''):raw=w.itemText(i).split()[0]
                w.setItemText(i, f'{raw} '+('beats' if language=='en' else '拍'))
    for action in parent.findChildren(QAction):
        original=action.property('_melody_zh_text')
        if original is None:
            original=action.text();action.setProperty('_melody_zh_text',original)
        action.setText(translated(original,language))


def _win32_colorref(hex_color: str) -> int:
    """Translate #RRGGBB into the Win32 COLORREF 0x00BBGGRR layout."""
    rgb = hex_color.removeprefix('#')
    if len(rgb) != 6:
        raise ValueError(f'Expected 6-digit RGB color: {hex_color}')
    red, green, blue = (int(rgb[i:i + 2], 16) for i in (0, 2, 4))
    return red | (green << 8) | (blue << 16)


def apply_native_chrome(window, theme: str, enabled: bool = True) -> bool:
    """Keep the system caption and controls, tinting them to match the Qt theme.

    Windows 11: request DWM backdrop material, rounded corners and themed
    caption/text/border colors. The OS decides the precise Acrylic/Mica visual
    (accessibility, transparency setting, power mode, OS build). Caption colors
    are deliberately solid on Windows where DWM cannot combine an exact custom
    RGB caption color with guaranteed translucent material. We never create a
    frameless replacement, so Snap Layouts and native titlebar controls survive.
    Other platforms and old Windows safely keep the system-provided caption.
    """
    if sys.platform != 'win32':
        return False
    try:
        import ctypes
        from ctypes import wintypes

        dwm = ctypes.WinDLL('dwmapi')
        hwnd = wintypes.HWND(int(window.winId()))
        function = dwm.DwmSetWindowAttribute
        function.argtypes = [wintypes.HWND, wintypes.DWORD,
                             ctypes.c_void_p, wintypes.DWORD]
        function.restype = ctypes.c_long

        def attr(index: int, value: int) -> bool:
            data = wintypes.DWORD(value)
            return function(hwnd, index, ctypes.byref(data),
                            ctypes.sizeof(data)) == 0

        colors = COLORS[theme]
        # DWM 33: rounded corners; 20: caption control dark/light treatment.
        rounded = attr(33, 2)
        attr(20, 1 if theme == 'dark' else 0)
        # DWM 38: Desktop Acrylic (3) when requested; none (1) when disabled.
        material = attr(38, 3 if enabled else 1)
        # DWM 35/36/34: themed caption/background, legible text and border.
        # Windows 11 22000+ supports these; old Windows simply ignores them.
        caption = attr(35, _win32_colorref(colors['window']))
        text = attr(36, _win32_colorref(colors['ink']))
        border = attr(34, _win32_colorref(colors['line']))
        return rounded or material or caption or text or border
    except (AttributeError, OSError, ValueError):
        return False
