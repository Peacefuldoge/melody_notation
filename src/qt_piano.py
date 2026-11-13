"""Collapsible, themed score-only piano keyboard and live MIDI input routing."""
from __future__ import annotations

import json
from time import perf_counter

from PySide6.QtCore import Qt, QObject, QTimer, Signal, QRectF, QSize, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QGridLayout,
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea,
    QToolButton, QVBoxLayout, QWidget, QSizePolicy, QSlider,
    QGroupBox, QFormLayout, QLayout)

from .qt_design import COLORS
from .performance import DEFAULT_KEYS, normalized_key, validate_mapping
from .piano_layout import (
    piano_key_layout, toolbar_row_groups, MAX_HIGH, BASE_WHITE_COUNT, DEFAULT_START_OCTAVE,
    MIN_START_OCTAVE, MAX_START_OCTAVE, octave_offset,
)
from .midi import INSTRUMENTS


class PianoKeys(QWidget):
    note_on = Signal(int, int)
    note_off = Signal(int)
    WHITE_WIDTH = 57
    HEIGHT = 148
    LOW, HIGH = 48, 72  # default visible keyboard spans C3-C5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = 'light'
        self.start_octave = DEFAULT_START_OCTAVE
        self.mapping = dict(DEFAULT_KEYS)
        self.held = set()
        self._mouse_note = None
        self.whites = list(piano_key_layout(BASE_WHITE_COUNT * self.WHITE_WIDTH + 2, self.start_octave)[0])
        self.white_width=self.WHITE_WIDTH
        self.setFixedSize(len(self.whites)*self.white_width+1, self.HEIGHT)
        self.setMouseTracking(True)
        self.setToolTip('点击琴键演奏；键位可通过「键位设置」自定义')

    def set_theme(self, name):
        self.theme = name if name in COLORS else 'light'; self.update()

    def set_mapping(self, mapping):
        # The visible mapping is transposed; stored base mappings still use
        # validate_mapping() with the stricter editor-compatible bounds.
        self.mapping = validate_mapping(mapping, min_pitch=0, max_pitch=127); self.update()

    def set_held(self, pitches):
        self.held = set(pitches); self.update()

    def fit_to_width(self, available: int):
        """Resize and reveal up to one extra octave as space permits.

        The base two octaves stay accessible even in narrow editor panes.
        Additional white keys appear at their normal width; overflow at
        genuinely small widths still uses the horizontal scrollbar.
        """
        notes, width = piano_key_layout(available, self.start_octave)
        if notes == tuple(self.whites) and width == self.white_width:
            return
        # A resize must not strand a mouse-held note outside the visible range.
        if self._mouse_note is not None and not notes[0] <= self._mouse_note <= notes[-1]:
            self.note_off.emit(self._mouse_note)
            self._mouse_note = None
        self.whites = list(notes)
        self.LOW = notes[0]
        self.HIGH = notes[-1]
        self.white_width = width
        self.setFixedSize(len(notes) * width + 1, self.HEIGHT)
        self.update()

    def set_start_octave(self, start_octave: int, available: int):
        octave_offset(start_octave)  # validate before changing any state
        self.start_octave = start_octave
        self.fit_to_width(available)

    def _geometry(self, pitch):
        idx = self.whites.index(pitch) if pitch in self.whites else None
        if idx is not None:
            return QRectF(idx*self.white_width, 0, self.white_width, self.HEIGHT), False
        # Black keys sit across the seam between their neighboring white keys.
        before = max((p for p in self.whites if p<pitch), default=None)
        if before is None:return None, True
        ix = self.whites.index(before)
        black_width=max(21,round(self.white_width*38/self.WHITE_WIDTH))
        return QRectF((ix+1)*self.white_width-black_width/2, 0, black_width, 91), True

    def _color(self, black=False, active=False):
        if self.theme == 'olive':
            return '#43583C' if black else ('#B8D5A9' if active else '#E7F1DC')
        if self.theme == 'dark':
            return '#182131' if black else ('#8DAFC6' if active else '#D5DFEA')
        if self.theme == 'beige':
            return '#554535' if black else ('#E8C797' if active else '#FFF7E8')
        return '#1D1F24' if black else ('#A8D9EF' if active else '#FFFFFF')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c=COLORS[self.theme]
        inv={pitch:key for key,pitch in self.mapping.items()}
        for pitch in self.whites:
            rect,_=self._geometry(pitch)
            painter.setPen(QPen(QColor(c['line']),1))
            painter.setBrush(QColor(self._color(active=pitch in self.held)))
            painter.drawRoundedRect(rect.adjusted(1,1,-1,-2),3,3)
            note_name=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][pitch%12]
            painter.setPen(QColor('#536171' if self.theme in ('light','dark') else c['secondary']))
            painter.setFont(QFont('Segoe UI',8))
            painter.drawText(rect.adjusted(0,0,0,-24),Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignHCenter,
                             f'{note_name}{pitch//12-1}')
            if pitch in inv:
                painter.setFont(QFont('Segoe UI',9,QFont.Weight.DemiBold))
                painter.drawText(rect.adjusted(0,0,0,-8),Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignHCenter,inv[pitch])
        for pitch in range(self.LOW, self.HIGH+1):
            if pitch in self.whites:continue
            rect,_=self._geometry(pitch)
            painter.setPen(QPen(QColor(c['ink']),1))
            painter.setBrush(QColor(c['accent'] if pitch in self.held else self._color(black=True)))
            painter.drawRoundedRect(rect.adjusted(1,0,-1,0),4,4)
            if pitch in inv:
                painter.setPen(QColor('#FFFFFF'))
                painter.setFont(QFont('Segoe UI',8,QFont.Weight.DemiBold))
                painter.drawText(rect.adjusted(0,0,0,-7),Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignHCenter,inv[pitch])
        painter.end()

    def _hit(self, x, y):
        # Test black keys first because they overlap white keys visually.
        for pitch in range(self.LOW,self.HIGH+1):
            if pitch not in self.whites:
                rect,_=self._geometry(pitch)
                if rect and rect.contains(x,y):return pitch
        for pitch in self.whites:
            rect,_=self._geometry(pitch)
            if rect.contains(x,y):return pitch
        return None

    def mousePressEvent(self, event):
        if event.button()==Qt.MouseButton.LeftButton:
            pitch=self._hit(event.position().x(),event.position().y())
            if pitch is not None:
                self._mouse_note=pitch
                self.note_on.emit(pitch,100)
                event.accept();return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._mouse_note is not None and event.buttons() & Qt.MouseButton.LeftButton:
            pitch=self._hit(event.position().x(),event.position().y())
            if pitch!=self._mouse_note:
                old=self._mouse_note
                self._mouse_note=pitch
                self.note_off.emit(old)
                if pitch is not None:self.note_on.emit(pitch,100)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self._mouse_note is not None:
            pitch=self._mouse_note;self._mouse_note=None
            self.note_off.emit(pitch)
            event.accept();return
        super().mouseReleaseEvent(event)


class ResponsivePianoScrollArea(QScrollArea):
    """Coalesce keyboard-size updates; never resize a widget inside resizeEvent.

    Qt delivers resize events synchronously. Changing widget geometry from
    inside a resize handler can cause a nested scrollbar/layout resize loop,
    especially while a splitter or the native window frame is being dragged.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fit_timer = QTimer(self)
        self._fit_timer.setSingleShot(True)
        self._fit_timer.setInterval(16)
        self._fit_timer.timeout.connect(self._fit_keyboard)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._fit_timer.isActive():
            self._fit_timer.start()

    def _fit_keyboard(self):
        keyboard = self.widget()
        if isinstance(keyboard, PianoKeys):
            keyboard.fit_to_width(max(1, self.viewport().width()))


class _StableWrapLayout(QLayout):
    """Flow layout that retains its child widgets and items across resizes.

    It uses Qt's height-for-width negotiation instead of deleting nested
    QHBoxLayouts and calling setFixedHeight() in resizeEvent(). That also
    avoids accumulating pending deleteLater() layout objects during a rapid
    Windows border-drag or splitter-drag.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(8)

    def addItem(self, item):
        self._items.append(item)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def _widths(self):
        return tuple(max(1, item.sizeHint().width()) for item in self._items)

    def rows_for_width(self, width):
        return toolbar_row_groups(max(1, width), self._widths(), spacing=self.spacing())

    def heightForWidth(self, width):
        rows = self.rows_for_width(width)
        if not rows:
            return 0
        return sum(max(self._items[i].sizeHint().height() for i in indices)
                   for indices in rows) + self.spacing() * (len(rows) - 1)

    def sizeHint(self):
        # The actual height depends on the editor width. Do not claim a wide
        # minimum that prevents QSplitter from reducing the central pane.
        widths = self._widths()
        one_row = sum(widths) + self.spacing() * max(0, len(widths) - 1)
        return QSize(one_row, self.heightForWidth(one_row))

    def minimumSize(self):
        return QSize(0, max((item.minimumSize().height() for item in self._items), default=0))

    def setGeometry(self, rect):
        super().setGeometry(rect)
        rows = self.rows_for_width(rect.width())
        widths = self._widths()
        y = rect.y()
        last = self.count() - 1
        for indices in rows:
            row_height = max(self._items[i].sizeHint().height() for i in indices)
            x = rect.x()
            for i in indices:
                width = widths[i]
                if i == last:
                    # Settings stays right-aligned on a sufficiently wide row.
                    x = max(x, rect.x() + rect.width() - width)
                self._items[i].setGeometry(QRect(x, y, width, row_height))
                x += width + self.spacing()
            y += row_height + self.spacing()


class AdaptivePerformanceToolbar(QWidget):
    """One stable, responsive toolbar; no dynamic layout destruction."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('KeyboardToolbar')
        self.setMinimumWidth(0)
        policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self._sections = []
        self._layout = _StableWrapLayout(self)

    @property
    def row_count(self):
        return len(self._layout.rows_for_width(self.width()))

    def sizeHint(self):
        return self._layout.sizeHint()

    def minimumSizeHint(self):
        return self._layout.minimumSize()

    def set_sections(self, sections):
        while self._layout.count():
            self._layout.takeAt(0)
        self._sections = list(sections)
        for part in self._sections:
            self._layout.addWidget(part)
        self.refresh()

    def refresh(self):
        self._layout.invalidate()
        self.updateGeometry()
        self.update()


class CaptureKeyButton(QPushButton):
    captured = Signal(str)

    def __init__(self, label):
        super().__init__(label)
        self._regular=label
        self.clicked.connect(self._start)

    def _start(self):
        self.setText('按下按键…')
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def keyPressEvent(self, event):
        if self.text()!='按下按键…':
            return super().keyPressEvent(event)
        if event.key()==Qt.Key.Key_Escape:
            self.setText(self._regular);return
        if event.key() in (Qt.Key.Key_Delete,Qt.Key.Key_Backspace):
            self.setText('—')
            self._regular='—'
            self.captured.emit('')
            event.accept();return
        if event.modifiers() & (Qt.KeyboardModifier.ControlModifier |
                                Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
            return
        try:
            key=normalized_key(event.text())
        except ValueError:
            return
        self.setText(key)
        self._regular=key
        self.captured.emit(key)
        event.accept()


class MappingDialog(QDialog):
    def __init__(self, mapping, theme, parent=None, *, start_octave=DEFAULT_START_OCTAVE):
        super().__init__(parent)
        self.setWindowTitle('自定义电脑键盘映射')
        self.setModal(True)
        self.resize(660,510)
        self.mapping=dict(mapping)
        self.theme=theme
        self.start_octave=start_octave
        self.offset=octave_offset(start_octave)
        main=QVBoxLayout(self)
        main.addWidget(QLabel(f'当前音域 C{start_octave}–C{start_octave+3}。点击键位重新绑定；Delete/Backspace 可解绑。'))
        # Extra notes up to C7 are available for custom computer-key mappings.
        # Keep the dialog usable on smaller monitors by scrolling its grid.
        self.mapping_scroll=QScrollArea()
        self.mapping_scroll.setWidgetResizable(True)
        self.mapping_scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder=QWidget()
        self.grid=QGridLayout(holder);self.grid.setSpacing(7)
        self.mapping_scroll.setWidget(holder)
        main.addWidget(self.mapping_scroll,1)
        self._build()
        foot=QHBoxLayout()
        reset=QPushButton('恢复默认键位')
        reset.clicked.connect(self._reset)
        foot.addWidget(reset)
        foot.addStretch(1)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
        foot.addWidget(self.buttons);main.addLayout(foot)

    def _build(self):
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for idx,pitch in enumerate(range(60, MAX_HIGH+1)):
            r,c=divmod(idx,5)
            box=QWidget();lay=QHBoxLayout(box);lay.setContentsMargins(3,3,3,3)
            actual_pitch=pitch+self.offset
            label=QLabel(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][actual_pitch%12]+str(actual_pitch//12-1))
            label.setMinimumWidth(30);lay.addWidget(label)
            reverse={p:k for k,p in self.mapping.items()}
            button=CaptureKeyButton(reverse.get(pitch,'—'))
            button.setFixedWidth(70)
            button.captured.connect(lambda key,n=pitch:self._assign(n,key))
            lay.addWidget(button)
            self.grid.addWidget(box,r,c)

    def _assign(self,pitch,key):
        if not key:
            self.mapping={k:p for k,p in self.mapping.items() if p!=pitch}
            self._build();return
        # One key cannot silently override another note's shortcut.
        existing=self.mapping.get(key)
        if existing is not None and existing!=pitch:
            answer=QMessageBox.question(self,'键位冲突',
                f'{key} 已绑定到 MIDI 音符 {existing}。是否将它改绑到当前音符？',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:
                self._build();return
        self.mapping={k:p for k,p in self.mapping.items() if p!=pitch and k!=key}
        self.mapping[key]=pitch
        self._build()

    def _reset(self):
        self.mapping=dict(DEFAULT_KEYS);self._build()


class MidiInputRouter(QObject):
    event_received=Signal(int,int,bool,float)
    ports_changed=Signal(list)
    status_changed=Signal(str)
    disconnected=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self._active=False
        self._ports=[]
        self._selected='auto'
        self._opened=None
        self._port=None
        self._timer=QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.refresh)

    def set_active(self,yes):
        if self._active==yes:return
        self._active=yes
        if yes:
            self.refresh();self._timer.start()
        else:
            self._timer.stop();self._close()

    def select(self,selected):
        self._selected=selected or 'auto'
        if self._active:self.refresh()

    def _close(self):
        had_port=self._port is not None
        if self._port:
            try:self._port.close()
            except Exception:pass
        self._port=None;self._opened=None
        if had_port:self.disconnected.emit()

    def refresh(self):
        if not self._active:return
        failure=False
        try:
            import mido
            # Explicitly import backend; a machine may have mido but not RtMidi.
            import rtmidi  # noqa: F401
            names=mido.get_input_names()
        except Exception:
            failure=True
            names=[]
            self.status_changed.emit('电脑键盘可用 · MIDI 驱动未就绪（安装 python-rtmidi）')
        if names!=self._ports:
            self._ports=list(names)
            self.ports_changed.emit(list(self._ports))
        target=(next(iter(names),None) if self._selected=='auto' else
                self._selected if self._selected in names else None)
        if target==self._opened:return
        self._close()
        if target is None:
            if not failure:
                self.status_changed.emit('电脑键盘可用 · 未连接 MIDI 乐器')
            return
        try:
            import mido
            self._port=mido.open_input(target,callback=self._message)
            self._opened=target
            self.status_changed.emit('已连接 MIDI：'+target)
        except Exception as exc:
            self._close()
            self.status_changed.emit('MIDI 设备打开失败：'+str(exc))

    def _message(self,message):
        kind=getattr(message,'type','')
        pitch=getattr(message,'note',-1)
        if kind=='note_on':
            velocity=int(getattr(message,'velocity',0))
            self.event_received.emit(pitch,velocity,velocity>0,perf_counter())
        elif kind=='note_off':
            self.event_received.emit(pitch,0,False,perf_counter())


class PerformanceSettingsDialog(QDialog):
    """Non-modal settings window: the piano remains playable while it is open.

    Move the *same control instances* out of the piano toolbar. Their existing
    signals and the keyboard/audio/MIDI state remain the single source of truth.
    """
    closed = Signal()

    def __init__(self, panel, parent=None):
        super().__init__(parent or panel)
        self.setObjectName('KeyboardSettingsDialog')
        self.setWindowTitle('演奏设置')
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(355)
        self.resize(430, 400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        sound_box = QGroupBox('音色与监听')
        sound_form = QFormLayout(sound_box)
        sound_form.setContentsMargins(12, 18, 12, 12)
        sound_form.setSpacing(10)
        panel.keyboard_instrument.setMaximumWidth(16777215)
        panel.keyboard_instrument.setMinimumWidth(150)
        sound_form.addRow('键盘音色', panel.keyboard_instrument)
        monitor_row = QWidget(self)
        monitor_layout = QHBoxLayout(monitor_row)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.setSpacing(8)
        panel.monitor_level.setMinimumWidth(120)
        panel.monitor_level.setMaximumWidth(16777215)
        panel.monitor_level.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.monitor_value = QLabel(f'{panel.monitor_level.value()}%')
        self.monitor_value.setMinimumWidth(38)
        self.monitor_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        panel.monitor_level.valueChanged.connect(lambda value: self.monitor_value.setText(f'{value}%'))
        monitor_layout.addWidget(panel.monitor_level, 1)
        monitor_layout.addWidget(self.monitor_value)
        sound_form.addRow('监听音量', monitor_row)
        layout.addWidget(sound_box)

        octave_box = QGroupBox('音域调节')
        octave_layout = QVBoxLayout(octave_box)
        octave_layout.setContentsMargins(12, 18, 12, 12)
        octave_row = QHBoxLayout()
        octave_row.setSpacing(9)
        octave_row.addWidget(panel.octave_down)
        octave_row.addStretch(1)
        octave_row.addWidget(panel.octave_range)
        octave_row.addStretch(1)
        octave_row.addWidget(panel.octave_up)
        octave_layout.addLayout(octave_row)
        octave_hint = QLabel('每次平移一个八度；宽屏会向右自动扩展琴键。')
        octave_hint.setObjectName('Muted')
        octave_hint.setWordWrap(True)
        octave_layout.addWidget(octave_hint)
        layout.addWidget(octave_box)

        midi_box = QGroupBox('MIDI 设备与键位')
        midi_layout = QVBoxLayout(midi_box)
        midi_layout.setContentsMargins(12, 18, 12, 12)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        panel.refresh_devices.setText('↻ 重新扫描设备')
        actions.addWidget(panel.refresh_devices)
        actions.addWidget(panel.mapping_button)
        actions.addStretch(1)
        midi_layout.addLayout(actions)
        self.device_state = QLabel('')
        self.device_state.setObjectName('Muted')
        self.device_state.setWordWrap(True)
        midi_layout.addWidget(self.device_state)
        layout.addWidget(midi_box)

        export_box = QGroupBox('录制文件')
        export_layout = QHBoxLayout(export_box)
        export_layout.setContentsMargins(12, 18, 12, 12)
        export_layout.addWidget(panel.export)
        export_layout.addStretch(1)
        layout.addWidget(export_box)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        close_button = QPushButton('关闭')
        close_button.clicked.connect(self.close)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()


class KeyboardPanel(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor=editor
        self.theme='light'
        self.setObjectName('KeyboardPanel')
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        outer=QVBoxLayout(self);outer.setContentsMargins(0,2,0,0);outer.setSpacing(6)
        self.toggle=QToolButton()
        self.toggle.setText('⌄  钢琴键盘 · 演奏与录制')
        self.toggle.setCheckable(True);self.toggle.setChecked(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toggle.setObjectName('KeyboardToggle')
        self.toggle.toggled.connect(self._toggle)
        outer.addWidget(self.toggle)
        self.contents=QWidget();self.contents.setObjectName('KeyboardContents')
        v=QVBoxLayout(self.contents);v.setContentsMargins(8,6,8,9);v.setSpacing(5)
        # One responsive toolbar: no nested scroll view or separately pinned
        # overlay. Control groups wrap as *whole units* when the pane shrinks.
        self.toolbar = AdaptivePerformanceToolbar(self.contents)

        def control_group(*widgets):
            group = QWidget(self.toolbar)
            group.setObjectName('KeyboardControlGroup')
            group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            line = QHBoxLayout(group)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(6)
            for widget in widgets:
                line.addWidget(widget)
            return group

        self.record = QPushButton('● 开始录制')
        self.record.setCheckable(True)
        self.record.setObjectName('RecordButton')
        self.record.toggled.connect(self._record)
        record_group = control_group(self.record)

        self.devices = QComboBox()
        self.devices.setMinimumWidth(138)
        self.devices.setMaximumWidth(210)
        self.devices.addItem('自动检测 / 自动切换', 'auto')
        self.devices.addItem('仅电脑键盘', 'computer')
        self.devices.currentIndexChanged.connect(self._change_device)
        devices_group = control_group(QLabel('输入设备'), self.devices)

        self.keyboard_instrument = QComboBox()
        self.keyboard_instrument.setObjectName('KeyboardInstrument')
        self.keyboard_instrument.addItems(list(INSTRUMENTS))
        self.keyboard_instrument.setCurrentText(self.editor.live_instrument)
        self.keyboard_instrument.setMinimumWidth(90)
        self.keyboard_instrument.setMaximumWidth(130)
        self.keyboard_instrument.setToolTip('只改变键盘实时演奏与演奏 MIDI 的音色，不影响右侧乐谱试听音色')
        self.keyboard_instrument.currentTextChanged.connect(self._instrument_changed)
        self.refresh_devices = QPushButton('↻')
        self.refresh_devices.setToolTip('重新扫描外接 MIDI 输入设备')
        self.refresh_devices.clicked.connect(self._scan)
        self.mapping_button = QPushButton('键位设置')
        self.mapping_button.clicked.connect(self.open_mapping)
        self.export = QPushButton('导出录制 MIDI')
        self.export.clicked.connect(self.editor.export_performance)
        self.monitor_level = QSlider(Qt.Orientation.Horizontal)
        self.monitor_level.setRange(0, 100)
        self.monitor_level.setValue(80)
        self.monitor_level.setFixedWidth(75)
        self.monitor_level.valueChanged.connect(
            lambda value: setattr(self.editor._live_audio, 'volume', value/100))
        self.octave_down = QToolButton()
        self.octave_down.setText('−')
        self.octave_down.setObjectName('KeyboardOctaveDown')
        self.octave_down.setToolTip('键盘整体降低一个八度')
        self.octave_down.clicked.connect(lambda: self.set_start_octave(self.start_octave - 1))
        self.octave_range = QLabel()
        self.octave_range.setObjectName('KeyboardOctaveRange')
        self.octave_range.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.octave_range.setMinimumWidth(76)
        self.octave_up = QToolButton()
        self.octave_up.setText('+')
        self.octave_up.setObjectName('KeyboardOctaveUp')
        self.octave_up.setToolTip('键盘整体升高一个八度')
        self.octave_up.clicked.connect(lambda: self.set_start_octave(self.start_octave + 1))
        # One compact main-row action opens the complete non-modal settings
        # window; no duplicate controls, overlay or horizontal scroll bar.
        self.settings_button = QPushButton('⚙ 演奏设置')
        self.settings_button.setObjectName('KeyboardSettingsButton')
        self.settings_button.setCheckable(True)
        self.settings_button.setToolTip('设置实时音色、监听音量、音域、MIDI 设备与键位；导出演奏 MIDI')
        settings_group = control_group(self.settings_button)
        self.toolbar.set_sections((record_group, devices_group, settings_group))
        v.addWidget(self.toolbar)
        self.settings_dialog = PerformanceSettingsDialog(self)
        self.settings_button.toggled.connect(self._toggle_settings)
        self.settings_dialog.closed.connect(self._settings_closed)
        # Device/monitor warnings remain accessible without a permanent
        # explanatory row stealing height from the keyboard.
        self._device_status='电脑键盘可用 · 正在检测外接 MIDI 设备…'
        self.set_device_status(self._device_status)
        self.piano=PianoKeys()
        self.piano.note_on.connect(lambda pitch,velocity:self.editor.perform_note_on(pitch,velocity,'mouse'))
        self.piano.note_off.connect(lambda pitch:self.editor.perform_note_off(pitch,'mouse'))
        self.scroller=ResponsivePianoScrollArea();self.scroller.setWidgetResizable(False)
        self.scroller.setMinimumWidth(0)
        self.scroller.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Reserve stable height for an optional horizontal scrollbar. Do not
        # change this height from inside a native/Qt resize callback.
        scrollbar_height = self.scroller.horizontalScrollBar().sizeHint().height()
        self.scroller.setFixedHeight(PianoKeys.HEIGHT + scrollbar_height +
                                     2*self.scroller.frameWidth() + 2)
        self.scroller.setWidget(self.piano)
        QTimer.singleShot(0,lambda:self.piano.fit_to_width(self.scroller.viewport().width()))
        v.addWidget(self.scroller)
        outer.addWidget(self.contents)
        self.router=MidiInputRouter(self)
        self.router.ports_changed.connect(self._ports)
        self.router.status_changed.connect(self.set_device_status)
        self.router.event_received.connect(self._from_midi)
        self.router.disconnected.connect(lambda:self.editor.release_source('midi'))
        self.start_octave=DEFAULT_START_OCTAVE
        self._octave_ready=False
        self.mapping=dict(DEFAULT_KEYS)
        self.load_mapping()
        # Remember the selected keyboard octave across sessions.
        self.set_start_octave(self._read_start_octave(), persist=False)
        self._octave_ready=True

    def _toggle_settings(self, visible: bool):
        if visible:
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
        else:
            self.settings_dialog.hide()

    def _settings_closed(self):
        # Closing the floating window with its native X also resets the button.
        self.settings_button.setChecked(False)

    @staticmethod
    def _read_start_octave() -> int:
        from PySide6.QtCore import QSettings
        raw=QSettings('MelodyNotation','Desktop').value(
            'keyboard_start_octave', DEFAULT_START_OCTAVE)
        try:
            value=int(raw)
            octave_offset(value)
            return value
        except (ValueError, TypeError):
            return DEFAULT_START_OCTAVE

    def pitch_for_key(self, key: str):
        """Transpose computer shortcuts; external MIDI stays at absolute pitch."""
        base=self.mapping.get(key)
        if base is None:return None
        return base + octave_offset(self.start_octave)

    def _update_piano_mapping(self):
        shift=octave_offset(self.start_octave)
        self.piano.set_mapping({key:pitch+shift for key,pitch in self.mapping.items()})

    def set_start_octave(self, start_octave: int, *, persist=True):
        octave_offset(start_octave)  # fail fast on invalid range
        if self._octave_ready and self.start_octave != start_octave:
            # Release held notes BEFORE the pitch mapping moves, preserving
            # correct note-off events in the live synth and MIDI recording.
            self.editor.release_keys()
        self.start_octave=start_octave
        self.piano.set_start_octave(start_octave, self.scroller.viewport().width())
        self._update_piano_mapping()
        self.octave_range.setText(f'C{start_octave}–C{start_octave+2}')
        self.octave_range.setToolTip(
            f'基础：C{start_octave}–C{start_octave+2}；宽屏最多 C{start_octave+3}')
        self.octave_down.setEnabled(start_octave>MIN_START_OCTAVE)
        self.octave_up.setEnabled(start_octave<MAX_START_OCTAVE)
        if persist:
            from PySide6.QtCore import QSettings
            settings=QSettings('MelodyNotation','Desktop')
            settings.setValue('keyboard_start_octave',start_octave)
            settings.sync()

    def set_device_status(self, text):
        self._device_status=str(text)
        self.devices.setToolTip(self._device_status)
        self.refresh_devices.setToolTip('重新扫描外接 MIDI 设备\n'+self._device_status)
        self.settings_dialog.device_state.setText(self._device_status)

    def _instrument_changed(self, name):
        if name not in INSTRUMENTS:
            return
        # Finish held notes before changing voice, including during recording.
        # A live MIDI export uses the currently selected keyboard instrument.
        self.editor.release_keys()
        self.editor.live_instrument=name
        self.editor._live_audio.instrument=name

    def _toggle(self,yes):
        self.contents.setVisible(yes)
        if not yes:
            self.settings_dialog.close()
        self.toggle.setText(('⌄' if yes else '›')+'  钢琴键盘 · 演奏与录制')

    def _record(self,yes):
        if yes and not self.editor.start_recording():
            self.record.blockSignals(True);self.record.setChecked(False);self.record.blockSignals(False)
            return
        if not yes:self.editor.finish_recording()
        self.record.setText('■ 结束录制' if yes else '● 开始录制')
        self.record.setObjectName('RecordingActive' if yes else 'RecordButton')
        self.record.style().unpolish(self.record);self.record.style().polish(self.record)

    def stop_recording(self):
        if self.record.isChecked():self.record.setChecked(False)

    def _from_midi(self,pitch,velocity,on,stamp):
        if not self.router._active:return  # queued events after disconnect/tab switch
        if on:self.editor.perform_note_on(pitch,velocity,'midi',now=stamp)
        else:self.editor.perform_note_off(pitch,'midi',now=stamp)

    def _ports(self,names):
        selected=self.devices.currentData()
        self.devices.blockSignals(True)
        self.devices.clear()
        self.devices.addItem('自动检测 / 自动切换','auto')
        self.devices.addItem('仅电脑键盘','computer')
        for name in names:self.devices.addItem(name,name)
        index=self.devices.findData(selected)
        self.devices.setCurrentIndex(max(0,index))
        self.devices.blockSignals(False)
        self.toolbar.refresh()  # device names can change the selector's width
        self.router.select(self.devices.currentData())

    def _change_device(self):self.router.select(self.devices.currentData())

    def _scan(self):self.router.refresh()

    def set_active(self,yes):
        self.router.set_active(yes)
        if not yes:
            self.settings_dialog.close()
            self.editor.release_keys()

    def set_theme(self,theme):
        self.theme=theme;self.piano.set_theme(theme)
        self.toolbar.refresh()

    def set_held(self,pitches):self.piano.set_held(pitches)

    def load_mapping(self):
        from PySide6.QtCore import QSettings
        settings=QSettings('MelodyNotation','Desktop')
        raw=settings.value('keyboard_mapping','')
        if raw:
            try:self.mapping=validate_mapping(json.loads(raw))
            except (ValueError,TypeError,json.JSONDecodeError):self.mapping=dict(DEFAULT_KEYS)
        self._update_piano_mapping()

    def open_mapping(self):
        dialog=MappingDialog(self.mapping,self.theme,self,start_octave=self.start_octave)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.mapping=validate_mapping(dialog.mapping)
            self._update_piano_mapping()
            from PySide6.QtCore import QSettings
            QSettings('MelodyNotation','Desktop').setValue('keyboard_mapping',json.dumps(self.mapping))

    def cleanup(self):
        self.settings_dialog.close()
        self.router.set_active(False)
