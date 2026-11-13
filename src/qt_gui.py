"""Melody Notation Qt desktop workbench.

Qt is a presentation dependency, never imported by the engine or MCP server.
Three document types share a single tabbed workspace. Requires PySide6.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import sys
import os
import traceback

from PySide6.QtCore import Qt, Signal, QObject, QSize, QSettings, QUrl, QRectF, QTimer, QEvent
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QIcon, QShortcut, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSplitter,
    QScrollArea, QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QPlainTextEdit, QCheckBox, QTreeWidget, QTreeWidgetItem, QLineEdit, QTabWidget,
    QFileDialog, QInputDialog, QMessageBox, QGroupBox, QFormLayout, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsView, QGraphicsScene, QGraphicsPathItem,
    QSlider, QMenu, QSizePolicy, QAbstractItemView, QFrame, QListWidget, QListWidgetItem, QAbstractSpinBox
)

from . import __version__
from .core import parse_text, text_from_score, blank_score_text
from .editing import (DURATIONS, update_note, insert_note, delete_note,
                      add_slur, clear_slur, get_note)
from .png import render_score, export_png
from .drums import (DrumPattern, default_drum_pattern, DRUM_VOICES, DRUM_LABELS,
                    DRUM_KITS, render_drum_pattern, export_drum_audio, export_drum_midi)
from .timeline_ops import clip_length, snap_beat, change_clip_on_timeline, split_clip
from .arrangement import (Arrangement, add_clip, source_beats, resolve_source,
                          synthesize_arrangement, export_arrangement_midi, export_arrangement_audio)
from .midi import INSTRUMENTS, export_midi
from .performance import PerformanceSession, normalized_key
from .live_audio import LiveAudioSynth
from .qt_piano import KeyboardPanel
from .layout_ops import navigation_split_sizes, navigation_width_limits
from .audio import SAMPLE_RATE, synthesize, export_audio
from .workspace import (ProjectWorkspace, remember_project, load_recent_projects)

DOC_EXTENSIONS = ('.jianpu', '.drum', '.mtrack')
DEFAULT_SCORE = blank_score_text()
from .qt_design import (COLORS, stylesheet, translated, translate_widgets,
    style_icon_button, line_icon, apply_native_chrome)
from .qt_preferences import PreferencesDialog


def error(parent, title: str, exc: Exception) -> None:
    QMessageBox.critical(parent, title, str(exc))


def row(*widgets, spacing=7):
    layout = QHBoxLayout()
    layout.setContentsMargins(0,0,0,0); layout.setSpacing(spacing)
    for w in widgets: layout.addWidget(w)
    return layout


def ui_button(label: str, callback, primary=False):
    glyph=None
    if label.startswith(('＋ ','+ ')):
        glyph='plus';label=label[2:]
    elif label in ('＋','+'):glyph='plus';label=''
    elif label.startswith(('▶ ', '■ ')):
        glyph='play' if label[0]=='▶' else 'stop';label=label[2:]
    b = QPushButton(label)
    if glyph:
        b.setIcon(line_icon(glyph,COLORS['light']['secondary']))
        b.setIconSize(QSize(18,18))
        b.setProperty('_melody_glyph',glyph)
    if primary: b.setObjectName('Primary')
    b.clicked.connect(callback)
    return b


class ScoreCanvas(QWidget):
    selected = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QImage()
        self.hitboxes = []
        self._offset_x = 0.0
        self._scale = 1.0
        self._pending_height = None
        self._height_timer = QTimer(self)
        self._height_timer.setSingleShot(True)
        self._height_timer.setInterval(16)
        self._height_timer.timeout.connect(self._apply_pending_height)
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_score(self, score, selected=None, theme='light', bars_per_row=3):
        pil, boxes = render_score(score, bars_per_row=bars_per_row,
                                  width=1200, selected=selected, theme=theme)
        buf = BytesIO(); pil.save(buf, format='PNG')
        self.image = QImage.fromData(buf.getvalue())
        self.hitboxes = boxes
        # Prefer showing the chosen number of bars within a typical editor
        # width, while retaining a legible minimum zoom for dense systems.
        # If the editor gets narrower than this floor, horizontal scrolling
        # takes over rather than shrinking notation indefinitely.
        readable_scale = {2: .75, 3: .65, 4: .55, 5: .50}.get(bars_per_row, .55)
        self.setMinimumWidth(max(300, round(self.image.width() * readable_scale) + 28)
                             if self.image.width() > 1200 else 300)
        self._layout_image()
        self.update()

    def _layout_image(self, *, defer_height=False):
        if self.image.isNull(): return
        self._scale = min(1., max(.20, (max(self.width(), 360)-28)/self.image.width()))
        self._offset_x = max(0., (self.width()-self.image.width()*self._scale)/2)
        height = round(self.image.height()*self._scale+30)
        if height != self.height():
            if defer_height:
                # Layout/scrollbar changes may synchronously trigger another
                # resizeEvent. Apply the new height on the event loop instead.
                self._pending_height = height
                if not self._height_timer.isActive():
                    self._height_timer.start()
            else:
                self._height_timer.stop()
                self._pending_height = None
                self.setFixedHeight(height)

    def _apply_pending_height(self):
        height = self._pending_height
        self._pending_height = None
        if height is not None and height != self.height():
            self.setFixedHeight(height)

    def resizeEvent(self, event):
        self._layout_image(defer_height=True)
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self.image.isNull():return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        target = (self._offset_x, 10., self.image.width()*self._scale,
                  self.image.height()*self._scale)
        p.drawImage(QRectF(*target), self.image)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.image.isNull():
            x = (event.position().x()-self._offset_x)/self._scale
            y = (event.position().y()-10.)/self._scale
            for bar, index, (x0,y0,x1,y1) in self.hitboxes:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    self.selected.emit(bar,index);break
        super().mousePressEvent(event)


class ScoreEditor(QWidget):
    changed = Signal()
    selection_changed = Signal()
    error_message = Signal(str)

    def __init__(self, score, parent=None):
        super().__init__(parent)
        self.score = score
        self.history = []
        self.redo_history = []
        self.selected_note = None
        self.slur_anchor = None
        self.source_dirty = False
        self.theme = 'light'
        self.bars_per_row = 3
        self._updating_source = False
        self._record_session = None
        self._record_next_preview = 0.0
        self._record_preview_timer = QTimer(self)
        self._record_preview_timer.setSingleShot(True)
        self._record_preview_timer.timeout.connect(self._flush_recording_preview)
        self._held = set()
        self._live_audio = LiveAudioSynth()
        self.live_instrument = 'piano'

        layout = QVBoxLayout(self);layout.setContentsMargins(12,12,12,12);layout.setSpacing(8)
        toolbar = QWidget();tools=row()
        name = QLabel('简谱');name.setObjectName('Header');tools.addWidget(name)
        tools.addStretch(1)
        tools.addWidget(ui_button('＋ 添加音符', self.insert_after))
        tools.addWidget(QLabel('每行小节'))
        self.bars = QComboBox();self.bars.addItems(['2','3','4','5']);self.bars.setCurrentText('3')
        self.bars.currentTextChanged.connect(self._set_bars);tools.addWidget(self.bars)
        self.toggle_source = ui_button('显示源码', self._toggle_source)
        tools.addWidget(self.toggle_source);toolbar.setLayout(tools);layout.addWidget(toolbar)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True)
        self.canvas = ScoreCanvas();self.canvas.selected.connect(self._choose_note)
        self.scroll.setWidget(self.canvas);layout.addWidget(self.scroll,1)
        self.source_panel = QWidget();source_box=QVBoxLayout(self.source_panel)
        source_box.setContentsMargins(0,2,0,0)
        source_actions=row(QLabel('简谱源码（Ctrl+Enter 应用）'))
        source_actions.addStretch(1)
        source_actions.addWidget(ui_button('从源码更新乐谱',self.apply_source))
        source_box.addLayout(source_actions)
        self.source=QPlainTextEdit();self.source.setFont(QFont('Consolas',11))
        self.source.setPlainText(text_from_score(score))
        self.source.textChanged.connect(self._source_edited)
        self.source.setMinimumHeight(130);source_box.addWidget(self.source)
        self.source_panel.setVisible(False);layout.addWidget(self.source_panel)
        # Score-only bottom dock. Source editor remains immediately above piano.
        self.keyboard_panel=KeyboardPanel(self)
        layout.addWidget(self.keyboard_panel)
        QShortcut(QKeySequence('Ctrl+Return'),self,activated=self.apply_source)
        self.draw()

    def set_input_active(self, active: bool):
        if not active:
            self.keyboard_panel.stop_recording()
            self.keyboard_panel.set_active(False)
            self.release_keys()
            self._live_audio.stop()
        else:
            self.keyboard_panel.set_active(True)

    def start_recording(self):
        if self.source_dirty:
            self.error_message.emit('录制前请先应用源码，避免覆盖尚未保存的源码修改。')
            return False
        self._record_session=PerformanceSession(self.score)
        self._record_next_preview=0.0
        self._record_preview_timer.stop()
        self.source.setReadOnly(True)
        return True

    def finish_recording(self):
        session=self._record_session
        if session is None:return
        self.source.setReadOnly(False)
        self._record_preview_timer.stop()
        session.finish()
        if session.notes:
            self._update_performance_score()
            # All keys in one recording can be undone as a single transaction.
            self.history.append(deepcopy(session.base))
            self.redo_history.clear()
        self.release_keys()

    def _update_performance_score(self):
        if self._record_session is None:return
        try:
            new_score=self._record_session.notation()
            self.set_model(new_score,record=False)
        except Exception as exc:
            self.error_message.emit('演奏转谱失败：'+str(exc))

    def _flush_recording_preview(self):
        self._update_performance_score()
        self._record_next_preview = perf_counter() + .10

    def _schedule_recording_preview(self):
        """Limit expensive full-score PNG/source redraws during fast playing.

        The first note appears immediately; successive events are coalesced
        into a 100ms update window without delaying the MIDI event timestamps.
        """
        current = perf_counter()
        if current >= self._record_next_preview:
            self._record_preview_timer.stop()
            self._update_performance_score()
            self._record_next_preview = perf_counter() + .10
        elif not self._record_preview_timer.isActive():
            remaining = max(1, int((self._record_next_preview-current)*1000))
            self._record_preview_timer.start(remaining)

    def perform_note_on(self, pitch: int, velocity: int = 90, source: str = 'keyboard', now=None):
        stamp=perf_counter() if now is None else now
        if not 0 <= pitch <= 127:return
        k=(source,pitch)
        if k in self._held:return
        self._held.add(k)
        self._live_audio.instrument=self.live_instrument
        if not self._live_audio.note_on(source,pitch,velocity):
            # Audio-device failures must not discard or interrupt MIDI capture.
            self.keyboard_panel.set_device_status(
                self._live_audio.error or '监听不可用；演奏记录仍然有效')
        self.keyboard_panel.set_held(p for _,p in self._held)
        if self.keyboard_panel.record.isChecked() and self._record_session is not None:
            self._record_session.note_on(pitch,velocity,source,now=stamp)
            self._schedule_recording_preview()

    def perform_note_off(self, pitch: int, source: str = 'keyboard', now=None):
        stamp=perf_counter() if now is None else now
        k=(source,pitch)
        if k not in self._held:return
        self._held.remove(k)
        self._live_audio.note_off(source,pitch)
        self.keyboard_panel.set_held(p for _,p in self._held)
        if self.keyboard_panel.record.isChecked() and self._record_session is not None:
            self._record_session.note_off(pitch,source,now=stamp)
            self._schedule_recording_preview()

    def release_source(self, source):
        for src,pitch in list(self._held):
            if src==source:self.perform_note_off(pitch,src)

    def release_keys(self):
        for source,pitch in list(self._held):
            self.perform_note_off(pitch,source)
        self._live_audio.all_off()

    def export_performance(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        session=self._record_session
        if session is None or not (session.notes or session.active):
            QMessageBox.information(self,'没有录制内容','请先点击「开始录制」，再演奏一些音符。')
            return
        path,_=QFileDialog.getSaveFileName(self,'导出原始演奏 MIDI',
                str(Path.home()/'演奏记录.mid'),'MIDI (*.mid)')
        if not path:return
        try:
            session.export_midi(Path(path),self.live_instrument)
        except Exception as exc:
            self.error_message.emit('导出演奏 MIDI 失败：'+str(exc))

    def _source_edited(self):
        if self._updating_source:return
        self.source_dirty = True;self.changed.emit()

    def _set_bars(self, text):
        self.bars_per_row=int(text);self.draw()

    def _toggle_source(self):
        on=not self.source_panel.isVisible()
        self.source_panel.setVisible(on)
        zh='隐藏源码' if on else '显示源码'
        self.toggle_source.setProperty('_melody_zh_text',zh)
        self.toggle_source.setText(translated(zh,self.property('_melody_language') or 'zh'))

    def _choose_note(self, bar, note):
        self.selected_note=(bar,note);self.selection_changed.emit();self.draw()

    def draw(self):
        self.canvas.set_score(self.score,self.selected_note,self.theme,self.bars_per_row)
        self.canvas.update()

    def set_theme(self, mode):
        self.theme=mode
        self.keyboard_panel.set_theme(mode)
        self.draw()

    def _set_source_from_model(self):
        self._updating_source=True
        try: self.source.setPlainText(text_from_score(self.score));self.source_dirty=False
        finally: self._updating_source=False

    def set_model(self, score, record=True):
        if record:self.history.append(deepcopy(self.score));self.redo_history.clear()
        self.score=score
        if self.selected_note:
            try:get_note(self.score,*self.selected_note)
            except IndexError:self.selected_note=None
        self._set_source_from_model()
        self.changed.emit();self.selection_changed.emit();self.draw()

    def mutate(self, fn):
        if self.keyboard_panel.record.isChecked():
            self.error_message.emit('录制中请先结束录制，再使用音符编辑操作。')
            return
        if self.source_dirty:
            self.error_message.emit('源码尚未应用，请先按 Ctrl+Enter 更新谱面。')
            return
        try:self.set_model(fn(self.score))
        except Exception as exc:self.error_message.emit(str(exc))

    def apply_source(self):
        if self.keyboard_panel.record.isChecked():
            self.error_message.emit('录制中请先结束录制，再应用源码。')
            return
        try:
            score=parse_text(self.source.toPlainText(),strict=False)
            self.set_model(score)
        except Exception as exc:self.error_message.emit(str(exc))

    def undo(self):
        if self.keyboard_panel.record.isChecked():
            self.error_message.emit('请先结束录制，再撤销。');return
        if not self.history:return
        self.redo_history.append(deepcopy(self.score));old=self.history.pop()
        self.set_model(old,record=False)

    def redo(self):
        if self.keyboard_panel.record.isChecked():
            self.error_message.emit('请先结束录制，再重做。');return
        if not self.redo_history:return
        self.history.append(deepcopy(self.score));old=self.redo_history.pop()
        self.set_model(old,record=False)

    def score_for_save(self):
        if self.source_dirty:return parse_text(self.source.toPlainText(),strict=False)
        return self.score

    def replace_note(self, degree, octave, beats, accidental, ornament):
        if self.selected_note is None:return
        self.mutate(lambda s:update_note(s,*self.selected_note,degree=degree,octave=octave,
                 beats=beats,accidental=accidental,ornament=ornament))

    def insert_after(self):
        if self.keyboard_panel.record.isChecked():
            self.error_message.emit('录制中请先结束录制，再插入音符。');return
        # Blank new scores have no selectable notes yet. Insert the first one
        # directly, then focus it so inspector edits work immediately.
        if self.selected_note is None:
            bar=max(1,len(self.score.measures))
            note=len(self.score.measures[bar-1]) if self.score.measures else 0
        else:
            bar,note=self.selected_note
        if self.source_dirty:
            self.error_message.emit('源码尚未应用，请先按 Ctrl+Enter 更新谱面。')
            return
        try:
            new_score=insert_note(self.score,bar,note+1)
            self.set_model(new_score)
            self.selected_note=(bar,note+1)
            self.selection_changed.emit()
            self.draw()
        except Exception as exc:self.error_message.emit(str(exc))

    def delete_selected(self):
        if self.selected_note is None:return
        self.mutate(lambda s:delete_note(s,*self.selected_note))

    def slur_start(self):
        self.slur_anchor=self.selected_note

    def slur_finish(self):
        if self.slur_anchor is None or self.selected_note is None:
            self.error_message.emit('先选择连音起点，然后选择终点。');return
        a,b=self.slur_anchor,self.selected_note
        self.mutate(lambda s:add_slur(s,*a,*b));self.slur_anchor=None

    def slur_remove(self):
        if self.selected_note is not None:
            self.mutate(lambda s:clear_slur(s,*self.selected_note))

class DrumEditor(QWidget):
    changed = Signal()
    error_message = Signal(str)

    def __init__(self, pattern: DrumPattern, parent=None):
        super().__init__(parent)
        self.pattern=pattern
        self.theme='light'
        self.history=[];self.redo_history=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(12,12,12,12);layout.setSpacing(10)
        heading=QLabel('鼓点音序器');heading.setObjectName('Header');layout.addWidget(heading)
        options=QHBoxLayout()
        self.title_edit=QLineEdit(pattern.title);self.title_edit.setPlaceholderText('名称')
        self.bpm_edit=QSpinBox();self.bpm_edit.setRange(20,400);self.bpm_edit.setValue(pattern.bpm)
        self.bars_edit=QSpinBox();self.bars_edit.setRange(1,64);self.bars_edit.setValue(pattern.bars)
        self.kit_edit=QComboBox();self.kit_edit.addItems(list(DRUM_KITS));self.kit_edit.setCurrentText(pattern.kit)
        for label,widget in [('名称',self.title_edit),('BPM',self.bpm_edit),('小节',self.bars_edit),('鼓组',self.kit_edit)]:
            options.addWidget(QLabel(label));options.addWidget(widget)
        options.addWidget(ui_button('应用设置',self.apply_options));options.addStretch(1)
        layout.addLayout(options)
        help_=QLabel('点击格子编辑节奏 · 点击 + 添加鼓轨 · 右键轨道名可重命名、选鼓声或删除 · 每小节 16 步')
        help_.setObjectName('Muted');layout.addWidget(help_)
        self.table=QTableWidget(len(pattern.tracks),pattern.steps)
        header=self.table.verticalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._track_context_menu)
        header.sectionDoubleClicked.connect(self.rename_track)
        self.table.verticalHeader().setDefaultSectionSize(68)
        self.table.horizontalHeader().setDefaultSectionSize(32)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.cellClicked.connect(self.toggle)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        layout.addWidget(self.table)
        self.add_track_button=ui_button('＋ 添加鼓轨',self.add_track)
        self.add_track_button.setToolTip('在末尾新增鼓点音轨；默认名称为“新建鼓点 4、5……”')
        self.add_track_button.setMaximumWidth(165)
        layout.addWidget(self.add_track_button,alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        self._refresh_table()

    def _snapshot(self):
        self.history.append(deepcopy(self.pattern));self.redo_history.clear();self.changed.emit()

    def apply_options(self):
        try:
            new=deepcopy(self.pattern)
            new.title=self.title_edit.text().strip();new.bpm=self.bpm_edit.value()
            new.kit=self.kit_edit.currentText()
            bars=self.bars_edit.value()
            if bars<self.pattern.bars and any(step>=bars*16 for hits in self.pattern.hits.values() for step in hits):
                answer=QMessageBox.question(self,'缩短鼓点',
                    '缩短小节会丢弃末尾鼓击，确定继续吗？',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
                if answer!=QMessageBox.StandardButton.Yes:return
            new.resize_bars(bars);new.validate()
            self._snapshot();self.pattern=new;self._refresh_table()
        except Exception as exc:self.error_message.emit(str(exc))

    def toggle(self, r, c):
        try:
            track_id=self.pattern.tracks[r].id
            self._snapshot();self.pattern.toggle(track_id,c)
            self._paint_cell(r,c)
        except Exception as exc:self.error_message.emit(str(exc))

    def add_track(self):
        try:
            if len(self.pattern.tracks)>=64:
                raise ValueError('最多支持 64 条鼓点音轨')
            self._snapshot()
            self.pattern.add_track()
            self._refresh_table()
        except Exception as exc:self.error_message.emit(str(exc))

    def rename_track(self, row):
        if not 0 <= row < len(self.pattern.tracks):return
        track=self.pattern.tracks[row]
        name,accepted=QInputDialog.getText(self,'重命名鼓点音轨','音轨名称：',
                                          QLineEdit.EchoMode.Normal,track.name)
        if not accepted or name.strip()==track.name:return
        try:
            if not name.strip():raise ValueError('音轨名称不能为空')
            self._snapshot();self.pattern.rename_track(track.id,name)
            self._refresh_table()
        except Exception as exc:self.error_message.emit(str(exc))

    def remove_track(self,track_id):
        try:
            track=self.pattern.track(track_id)
            if self.pattern.hits[track_id]:
                answer=QMessageBox.question(self,'删除鼓点音轨',
                    f'删除“{track.name}”将永久移除这一行的所有鼓点。确定删除吗？',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
                if answer!=QMessageBox.StandardButton.Yes:return
            self._snapshot();self.pattern.remove_track(track_id)
            self._refresh_table()
        except Exception as exc:self.error_message.emit(str(exc))

    def _change_track_sound(self,track_id,sound):
        try:
            if self.pattern.track(track_id).sound==sound:return
            self._snapshot();self.pattern.set_track_sound(track_id,sound)
            self._refresh_table()
        except Exception as exc:self.error_message.emit(str(exc))

    def _track_context_menu(self,pos):
        row=self.table.verticalHeader().logicalIndexAt(pos)
        if not 0 <= row < len(self.pattern.tracks):return
        track=self.pattern.tracks[row]
        menu=QMenu(self)
        menu.addAction('重命名',lambda:self.rename_track(row))
        sound_menu=menu.addMenu('鼓声类型')
        for sound in DRUM_VOICES:
            action=sound_menu.addAction(DRUM_LABELS[sound])
            action.setCheckable(True);action.setChecked(sound==track.sound)
            action.triggered.connect(lambda checked=False,key=sound,tid=track.id:
                                     self._change_track_sound(tid,key))
        menu.addSeparator()
        menu.addAction('删除鼓点音轨',lambda:self.remove_track(track.id))
        menu.exec(self.table.verticalHeader().mapToGlobal(pos))

    def _refresh_table(self):
        self.table.setRowCount(len(self.pattern.tracks))
        self.table.setColumnCount(self.pattern.steps)
        self.table.setVerticalHeaderLabels([t.name for t in self.pattern.tracks])
        for row,track in enumerate(self.pattern.tracks):
            item=self.table.verticalHeaderItem(row)
            if item:
                item.setToolTip(f'鼓声：{DRUM_LABELS[track.sound]}\n双击重命名，右键管理')
        self.table.setHorizontalHeaderLabels([str(i//4+1) if i%4==0 else '·'
                                              for i in range(self.pattern.steps)])
        # Align the '+' immediately under the last drum row, not after a huge white table.
        visible=min(8,max(1,len(self.pattern.tracks)))
        self.table.setFixedHeight(self.table.horizontalHeader().height()+visible*68+5)
        for r in range(len(self.pattern.tracks)):
            for c in range(self.pattern.steps):self._paint_cell(r,c)

    def _paint_cell(self,r,c):
        item=self.table.item(r,c)
        if item is None:item=QTableWidgetItem();self.table.setItem(r,c,item)
        track_id=self.pattern.tracks[r].id
        active=c in self.pattern.hits[track_id]
        item.setText('●' if active else ' ')
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        palette=COLORS[self.theme]
        if active:
            item.setBackground(QBrush(QColor(palette['accent'])))
            item.setForeground(QBrush(QColor(palette['on_accent'])))
        else:
            item.setBackground(QBrush(QColor(palette['soft'] if c//4%2==0 else palette['surface'])))
            item.setForeground(QBrush(QColor(palette['secondary'])))

    def set_theme(self,theme):
        self.theme=theme
        self._refresh_table()

    def undo(self):
        if not self.history:return
        self.redo_history.append(deepcopy(self.pattern));self.pattern=self.history.pop()
        self._sync_fields();self._refresh_table();self.changed.emit()

    def redo(self):
        if not self.redo_history:return
        self.history.append(deepcopy(self.pattern));self.pattern=self.redo_history.pop()
        self._sync_fields();self._refresh_table();self.changed.emit()

    def _sync_fields(self):
        self.title_edit.setText(self.pattern.title);self.bpm_edit.setValue(self.pattern.bpm)
        self.bars_edit.setValue(self.pattern.bars);self.kit_edit.setCurrentText(self.pattern.kit)


class ArrangementTimeline(QGraphicsView):
    """Interactive DAW clip surface: click, drag, trim edges, Ctrl-drag copy."""
    RULER = 42
    LANE = 70

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._drag = None
        self._drag_item = None
        self._drag_bounds = None
        self._ghost = None
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _clip_item(self, pos):
        item = self.itemAt(pos)
        while item is not None:
            identity = item.data(0)
            if isinstance(identity, tuple) and len(identity) == 2:
                return item, identity
            item = item.parentItem()
        return None, None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item, identity = self._clip_item(event.pos())
            scene_pos = self.mapToScene(event.pos())
            if identity:
                ti, ci = identity
                self.editor.select_clip(ti, ci)
                # Selection redraws the scene; fetch the *new* item.
                item, identity = self._clip_item(event.pos())
                if item is not None:
                    bounds = item.sceneBoundingRect()
                    edge = min(11., bounds.width() / 3)
                    mode = ('trim_left' if scene_pos.x() <= bounds.left() + edge else
                            'trim_right' if scene_pos.x() >= bounds.right() - edge else 'move')
                    duplicate = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                    self._drag = (ti, ci, mode, scene_pos.x(), scene_pos.y(), duplicate)
                    self._drag_item = item
                    self._drag_bounds = item.path().boundingRect()
                    if duplicate and mode == 'move':
                        self._ghost = self.scene().addPath(item.path(),item.pen(),item.brush())
                        self._ghost.setOpacity(.50)
                        self._ghost.setZValue(30)
                    self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor if mode == 'move'
                                              else Qt.CursorShape.SizeHorCursor)
            else:
                # A click on an empty lane selects the track without creating a clip.
                ti = int((scene_pos.y() - self.RULER) // self.LANE)
                if 0 <= ti < len(self.editor.arrangement.tracks):
                    self.editor.select_track(ti)
                self._drag = None
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag:
            ti, ci, mode, startx, starty, duplicate = self._drag
            x = self.mapToScene(event.pos()).x()
            dx = x - startx
            try:
                clip = self.editor.arrangement.tracks[ti].clips[ci]
                edited = change_clip_on_timeline(clip, mode, dx/self.editor.beat_width,
                    self.editor._source_length(clip),self.editor._snap_step())
                if mode == 'move':
                    offset_x = (edited.start_beat-clip.start_beat)*self.editor.beat_width
                    target = int((self.mapToScene(event.pos()).y()-self.RULER)//self.LANE)
                    valid = (0 <= target < len(self.editor.arrangement.tracks) and
                        self.editor.arrangement.tracks[target].kind ==
                        self.editor.arrangement.tracks[ti].kind)
                    offset_y = (target-ti)*self.LANE if valid else 0
                    target_item = self._ghost if self._ghost is not None else self._drag_item
                    if target_item is not None:target_item.setPos(offset_x,offset_y)
                elif self._drag_item is not None and self._drag_bounds is not None:
                    shape=QPainterPath()
                    bx=edited.start_beat*self.editor.beat_width
                    bw=clip_length(edited,self.editor._source_length(edited))*self.editor.beat_width
                    shape.addRoundedRect(QRectF(bx,self._drag_bounds.y(),
                                                max(8.,bw),self._drag_bounds.height()),7,7)
                    self._drag_item.setPath(shape)
                    self._drag_item.setOpacity(.75)
            except (IndexError,ValueError):pass
            self.editor.show_drag_hint(ti, ci, mode, dx / self.editor.beat_width, duplicate)
            event.accept()
            return
        item, identity = self._clip_item(event.pos())
        if identity:
            x = self.mapToScene(event.pos()).x()
            rect = item.sceneBoundingRect()
            edge = min(11., rect.width()/3)
            self.viewport().setCursor(Qt.CursorShape.SizeHorCursor if
                x <= rect.left()+edge or x >= rect.right()-edge else Qt.CursorShape.OpenHandCursor)
        else:self.viewport().unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            ti, ci, mode, x0, y0, duplicate = self._drag
            position = self.mapToScene(event.pos())
            delta = (position.x() - x0) / self.editor.beat_width
            target = int((position.y() - self.RULER) // self.LANE)
            self._drag = None
            self._drag_item = None
            self._drag_bounds = None
            self._ghost = None
            self.viewport().unsetCursor()
            if abs(position.x() - x0) > 4 or abs(position.y()-y0) > self.LANE/2:
                self.editor.timeline_change(ti, ci, mode, delta, target, duplicate and mode=='move')
            else:self.editor.update_hint()
            # Also restore the original shape after a sub-grid/no-op drag.
            self.editor._draw_timeline()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self,event):
        item,identity = self._clip_item(event.pos())
        if identity:
            self.editor.select_clip(*identity)
            self.editor.open_selected_source()
            event.accept();return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self,event):
        item, identity = self._clip_item(event.pos())
        if identity:
            self.editor.select_clip(*identity)
            position = self.mapToScene(event.pos()).x()/self.editor.beat_width
            menu = QMenu(self)
            menu.addAction('在这里切开片段', lambda:self.editor.split_selected(position))
            menu.addAction('复制片段  Ctrl+D',self.editor.duplicate_clip)
            menu.addAction('打开源文件',self.editor.open_selected_source)
            menu.addSeparator()
            menu.addAction('删除片段  Delete',self.editor.delete_clip)
            menu.exec(event.globalPos())
            event.accept();return
        super().contextMenuEvent(event)

    def wheelEvent(self,event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 1 if event.angleDelta().y() > 0 else -1
            self.editor.zoom_control.setValue(self.editor.zoom_control.value() + delta * 5)
            event.accept();return
        super().wheelEvent(event)


class TrackEditor(QWidget):
    """DAW-style editor: fixed track headers, flexible timeline, compact inspector."""
    changed = Signal()
    error_message = Signal(str)
    selection_changed = Signal()
    open_source_requested = Signal(str)

    def __init__(self, arrangement: Arrangement, path: Path, parent=None):
        super().__init__(parent)
        self.arrangement=arrangement
        self.path=Path(path)
        self.theme='light'
        self.history=[]
        self.redo_history=[]
        self.selected_track=0 if arrangement.tracks else -1
        self.selected_clip_index=None
        self._setting=False
        self.beat_width=48.0
        self._source_cache={}
        self._is_drawing=False

        layout=QVBoxLayout(self)
        layout.setContentsMargins(10,8,10,8)
        layout.setSpacing(8)
        header=row(spacing=9)
        self.title_edit=QLineEdit(arrangement.title)
        self.title_edit.setPlaceholderText('编排名称')
        self.title_edit.setMaximumWidth(350)
        self.bpm_edit=QSpinBox()
        self.bpm_edit.setRange(20,400)
        self.bpm_edit.setValue(arrangement.bpm)
        self.bpm_edit.setFixedWidth(88)
        header.addWidget(QLabel('编排'))
        header.addWidget(self.title_edit,2)
        header.addWidget(QLabel('BPM'))
        header.addWidget(self.bpm_edit)
        header.addWidget(ui_button('保存设置',self.apply_settings))
        header.addStretch(1)
        layout.addLayout(header)

        tools=row(spacing=7)
        tools.addWidget(ui_button('＋ 添加素材',self.add_source,True))
        tools.addWidget(ui_button('复制片段',self.duplicate_clip))
        tools.addWidget(ui_button('切割片段',lambda:self.split_selected()))
        tools.addWidget(ui_button('删除',self.delete_selected))
        tools.addStretch(1)
        layout.addLayout(tools)
        viewtools=row(spacing=7)
        viewtools.addStretch(1)
        viewtools.addWidget(QLabel('吸附'))
        self.snap=QComboBox()
        self.snap.addItem('1/4 拍',0.25)
        self.snap.addItem('1/2 拍',0.5)
        self.snap.addItem('1 拍',1.0)
        self.snap.addItem('1 小节',4.0)
        self.snap.addItem('关闭',0.0)
        self.snap.setToolTip('移动与裁剪时吸附到拍点网格')
        self.snap.setFixedWidth(105)
        viewtools.addWidget(self.snap)
        viewtools.addWidget(QLabel('缩放'))
        self.zoom_control=QSlider(Qt.Orientation.Horizontal)
        self.zoom_control.setRange(14,128)
        self.zoom_control.setValue(48)
        self.zoom_control.setFixedWidth(112)
        self.zoom_control.setToolTip('Ctrl + 鼠标滚轮也可以缩放时间线')
        self.zoom_control.valueChanged.connect(self._zoom_changed)
        viewtools.addWidget(self.zoom_control)
        viewtools.addWidget(ui_button('适应',self.fit_timeline))
        layout.addLayout(viewtools)

        # One integrated timeline instead of the original three separate
        # timeline/track/clip tables and their large, unused empty surfaces.
        work=QWidget()
        work.setObjectName('DAWWorkspace')
        workrow=QHBoxLayout(work)
        workrow.setContentsMargins(0,0,0,0)
        workrow.setSpacing(0)
        left=QWidget()
        left.setObjectName('DAWTrackColumn')
        left.setFixedWidth(215)
        leftbox=QVBoxLayout(left)
        leftbox.setContentsMargins(0,0,0,0)
        leftbox.setSpacing(0)
        strip=QLabel('  音轨  /  控制')
        strip.setObjectName('DAWTrackStrip')
        strip.setFixedHeight(ArrangementTimeline.RULER)
        leftbox.addWidget(strip)
        self.track_scroll=QScrollArea()
        self.track_scroll.setWidgetResizable(True)
        self.track_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.track_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.track_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.track_rows=QWidget()
        self.track_rows.setObjectName('DAWTrackRows')
        self.track_rows_layout=QVBoxLayout(self.track_rows)
        self.track_rows_layout.setContentsMargins(0,0,0,0)
        self.track_rows_layout.setSpacing(0)
        self.track_scroll.setWidget(self.track_rows)
        leftbox.addWidget(self.track_scroll,1)
        workrow.addWidget(left)
        self.timeline=ArrangementTimeline(self)
        workrow.addWidget(self.timeline,1)
        self.timeline.verticalScrollBar().valueChanged.connect(
            self.track_scroll.verticalScrollBar().setValue)
        layout.addWidget(work,1)

        self.help_label=QLabel('拖动片段移动 · 拖动左右边缘裁剪 · Ctrl+拖动复制 · 双击打开素材 · Ctrl+滚轮缩放')
        self.help_label.setObjectName('Muted')
        layout.addWidget(self.help_label)

        # A slim, contextual clip property strip; never a second empty table.
        self.clip_panel=QFrame()
        self.clip_panel.setObjectName('DAWClipPanel')
        inspector=QVBoxLayout(self.clip_panel)
        inspector.setContentsMargins(11,8,11,9)
        inspector.setSpacing(7)
        top=row(QLabel('片段属性'))
        self.clip_name=QLabel('点击时间线里的片段进行编辑')
        self.clip_name.setObjectName('Muted')
        top.addWidget(self.clip_name,1)
        inspector.addLayout(top)
        controls=row(spacing=7)
        self.start=QDoubleSpinBox();self.start.setRange(0,100000);self.start.setDecimals(2)
        self.trim_start=QDoubleSpinBox();self.trim_start.setRange(0,100000);self.trim_start.setDecimals(2)
        self.trim_end=QDoubleSpinBox();self.trim_end.setRange(0,100000);self.trim_end.setDecimals(2)
        self.gain=QDoubleSpinBox();self.gain.setRange(0,2);self.gain.setDecimals(2)
        self.gain.setSingleStep(.1)
        self.reversed=QCheckBox('反转')
        self._clip_fields=(self.start,self.trim_start,self.trim_end,self.gain,self.reversed)
        for label, widget in [('位置(拍)',self.start),('裁剪起',self.trim_start),
                              ('裁剪止',self.trim_end),('增益',self.gain)]:
            controls.addWidget(QLabel(label));controls.addWidget(widget)
            widget.setMinimumWidth(62)
        controls.addWidget(self.reversed)
        self.apply_clip_button=ui_button('应用修改',self.apply_clip,True)
        controls.addWidget(self.apply_clip_button)
        controls.addStretch(1)
        inspector.addLayout(controls)
        layout.addWidget(self.clip_panel,0)

        QShortcut(QKeySequence('Ctrl+D'),self,activated=self.duplicate_clip)
        QShortcut(QKeySequence('Delete'),self,activated=self.delete_clip)
        QShortcut(QKeySequence('Ctrl+E'),self,activated=lambda:self.split_selected())
        self.refresh()
        QTimer.singleShot(0,self.fit_timeline)

    def _snapshot(self):
        self.history.append(deepcopy(self.arrangement))
        self.redo_history.clear()
        self.changed.emit()

    def _source_length(self, clip):
        key=clip.source
        if key not in self._source_cache:
            try:
                source=resolve_source(self.path,key)
                self._source_cache[key]=source_beats(source)
            except Exception:
                self._source_cache[key]=max(4.,(clip.trim_end or 4.))
        return self._source_cache[key]

    def _length(self,clip):
        return max(.25,clip_length(clip,self._source_length(clip)))

    def _end_beat(self):
        return max([16.] + [cl.start_beat+self._length(cl)
                            for t in self.arrangement.tracks for cl in t.clips])

    def _snap_step(self):return float(self.snap.currentData() or 0.)

    def apply_settings(self):
        try:
            newer=deepcopy(self.arrangement)
            newer.title=self.title_edit.text().strip()
            newer.bpm=self.bpm_edit.value()
            newer.validate()
            if newer==self.arrangement:return
            self._snapshot()
            self.arrangement=newer
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def refresh(self):
        self._setting=True
        try:
            if self.selected_track>=len(self.arrangement.tracks):
                self.selected_track=len(self.arrangement.tracks)-1
            if self.selected_track<0 and self.arrangement.tracks:
                self.selected_track=0
            if self.selected_clip_index is not None:
                if self.selected_track<0 or self.selected_clip_index>=len(
                    self.arrangement.tracks[self.selected_track].clips):
                    self.selected_clip_index=None
            self.title_edit.setText(self.arrangement.title)
            self.bpm_edit.setValue(self.arrangement.bpm)
            self._build_track_headers()
            self._sync_clip_fields()
            self._draw_timeline()
        finally:self._setting=False
        self.selection_changed.emit()

    def _build_track_headers(self):
        while self.track_rows_layout.count():
            item=self.track_rows_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        for index, track in enumerate(self.arrangement.tracks):
            shell=QWidget()
            shell.setObjectName('DAWTrackSelected' if index==self.selected_track else 'DAWTrackRow')
            shell.setFixedHeight(ArrangementTimeline.LANE)
            outer=QHBoxLayout(shell)
            outer.setContentsMargins(7,7,5,7)
            outer.setSpacing(5)
            number=QLabel(f'{index+1:02}')
            number.setObjectName('Muted')
            number.setFixedWidth(21)
            outer.addWidget(number)
            names=QVBoxLayout()
            names.setContentsMargins(0,0,0,0)
            names.setSpacing(1)
            name=QPushButton(track.name)
            name.setObjectName('DAWTrackName')
            name.setToolTip('点击选中音轨，右键可重命名与排序')
            name.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            name.customContextMenuRequested.connect(
                lambda point,i=index,widget=name:
                    self.track_context_menu(i,widget.mapToGlobal(point)))
            name.clicked.connect(lambda checked=False,i=index:self.select_track(i))
            names.addWidget(name)
            subtitle=QLabel(('旋律 · ' + track.instrument) if track.kind=='melody' else '节奏 · 鼓点')
            subtitle.setObjectName('Muted')
            names.addWidget(subtitle)
            outer.addLayout(names,1)
            for txt, enabled, action in [('M',track.muted,self.toggle_mute),
                                         ('S',track.solo,self.toggle_solo)]:
                b=QToolButton()
                b.setText(txt)
                b.setCheckable(True)
                b.setChecked(enabled)
                b.setObjectName('DAWOnButton' if enabled else 'DAWSmallButton')
                b.setToolTip('静音 Mute' if txt=='M' else '独奏 Solo')
                b.clicked.connect(lambda checked=False,i=index,fn=action:
                                  self._quick_track_action(i,fn))
                outer.addWidget(b)
            self.track_rows_layout.addWidget(shell)
        self.track_rows.setMinimumHeight(max(ArrangementTimeline.LANE,
            len(self.arrangement.tracks)*ArrangementTimeline.LANE))
        self.track_rows_layout.addStretch(1)

    def track_context_menu(self,index,global_pos):
        self.select_track(index)
        menu=QMenu(self)
        menu.addAction('重命名音轨…',self.rename_track)
        menu.addAction('上移音轨',lambda:self.move_track(-1))
        menu.addAction('下移音轨',lambda:self.move_track(1))
        menu.addSeparator()
        menu.addAction('删除音轨',self.delete_track)
        menu.exec(global_pos)

    def rename_track(self):
        if self.selected_track<0:return
        track=self.arrangement.tracks[self.selected_track]
        name,ok=QInputDialog.getText(self,'重命名音轨','新名称',text=track.name)
        if not ok or not name.strip() or name.strip()==track.name:return
        changed=deepcopy(self.arrangement)
        changed.tracks[self.selected_track].name=name.strip()
        changed.validate()
        self._snapshot()
        self.arrangement=changed
        self.refresh()

    def _quick_track_action(self,index,fn):
        self.selected_track=index
        self.selected_clip_index=None
        fn()

    def select_track(self,index):
        if not 0<=index<len(self.arrangement.tracks):return
        if self.selected_track==index and self.selected_clip_index is None:return
        self.selected_track=index
        self.selected_clip_index=None
        self.refresh()

    def select_clip(self,track_index,clip_index):
        if not (0<=track_index<len(self.arrangement.tracks) and
                0<=clip_index<len(self.arrangement.tracks[track_index].clips)):
            return
        if (track_index,clip_index)==(self.selected_track,self.selected_clip_index):return
        self.selected_track=track_index
        self.selected_clip_index=clip_index
        self.refresh()

    def current_clip(self):
        if self.selected_clip_index is None:return None
        if not 0<=self.selected_track<len(self.arrangement.tracks):return None
        clips=self.arrangement.tracks[self.selected_track].clips
        if not 0<=self.selected_clip_index<len(clips):return None
        return clips[self.selected_clip_index]

    def _sync_clip_fields(self):
        clip=self.current_clip()
        enabled=clip is not None
        for w in self._clip_fields:w.setEnabled(enabled)
        self.apply_clip_button.setEnabled(enabled)
        if clip is None:
            self.clip_name.setText('点击时间线里的片段进行编辑')
            return
        self.clip_name.setText(Path(clip.source).name)
        self.start.setValue(clip.start_beat)
        self.trim_start.setValue(clip.trim_start)
        self.trim_end.setValue(clip.trim_end if clip.trim_end is not None else
                               self._source_length(clip))
        self.gain.setValue(clip.gain)
        self.reversed.setChecked(clip.reversed)

    def _draw_timeline(self):
        if self._is_drawing:return
        self._is_drawing=True
        try:
            c=COLORS[self.theme]
            scene=self.timeline.scene()
            sx=self.timeline.horizontalScrollBar().value()
            sy=self.timeline.verticalScrollBar().value()
            scene.clear()
            total=max(self._end_beat()+8,24.)
            height=ArrangementTimeline.RULER + max(1,len(self.arrangement.tracks))*ArrangementTimeline.LANE
            width=max(float(self.timeline.viewport().width()),total*self.beat_width)
            scene.setSceneRect(0,0,width,max(height,float(self.timeline.viewport().height())))
            ink=QColor(c['ink']);muted=QColor(c['secondary'])
            line=QColor(c['line']);back=QColor(c['surface'])
            scene.addRect(0,0,width,ArrangementTimeline.RULER,
                          QPen(Qt.PenStyle.NoPen),QBrush(QColor(c['soft'])))
            for i,t in enumerate(self.arrangement.tracks):
                y=ArrangementTimeline.RULER+i*ArrangementTimeline.LANE
                bg=QColor(c['selected'] if i==self.selected_track else
                          c['surface'] if i%2==0 else c['window'])
                scene.addRect(0,y,width,ArrangementTimeline.LANE,
                              QPen(Qt.PenStyle.NoPen),QBrush(bg))
                scene.addLine(0,y+ArrangementTimeline.LANE,width,y+ArrangementTimeline.LANE,
                              QPen(line))
            n=int(width/self.beat_width)+2
            major=4  # .mtrack v1 has BPM but no time-signature field: 4 beats/bar.
            # Keep enormous scores responsive; always retain 4-beat bars.
            grid_step=max(4,4*((n//2000)+1)) if n>2000 else 1
            for beat in range(0,n,grid_step):
                x=beat*self.beat_width
                if x>width:break
                isbar=beat%major==0
                pen=QPen(line if isbar else muted)
                if not isbar:pen.setColor(QColor(c['line']))
                pen.setWidthF(1.15 if isbar else .5)
                scene.addLine(x,ArrangementTimeline.RULER,x,height,pen)
                if isbar:
                    label=scene.addText(f'{beat//major+1:02}')
                    label.setDefaultTextColor(muted)
                    label.setPos(x+6,7)
            for ti, track in enumerate(self.arrangement.tracks):
                y=ArrangementTimeline.RULER+ti*ArrangementTimeline.LANE
                for ci,clip in enumerate(track.clips):
                    length=self._length(clip)
                    x=clip.start_beat*self.beat_width
                    w=max(8.,length*self.beat_width)
                    active=(ti==self.selected_track and ci==self.selected_clip_index)
                    clipcolor=QColor(c['accent'] if track.kind=='melody' else c['track'])
                    border=QColor(c['ink'] if active else c['accent'])
                    path=QPainterPath()
                    path.addRoundedRect(QRectF(x,y+8,w,ArrangementTimeline.LANE-17),7,7)
                    item=scene.addPath(path,QPen(border,2.4 if active else 1.0),QBrush(clipcolor))
                    item.setData(0,(ti,ci))
                    item.setZValue(2 if active else 1)
                    if w >= 40:
                        label=scene.addText(Path(clip.source).stem[:max(2,int((w-20)/11))] +
                                           (' ↶' if clip.reversed and w>80 else ''))
                        label.setDefaultTextColor(QColor(c['on_accent'] if track.kind=='melody'
                                                         else c['ink']))
                        label.setPos(x+6,y+11)
                        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                        label.setParentItem(item)
                    if w >= 108:
                        sub=scene.addText(f'{clip.start_beat:g}–{clip.start_beat+length:g} 拍')
                        sub.setDefaultTextColor(QColor(c['on_accent'] if track.kind=='melody'
                                                       else c['secondary']))
                        sub.setScale(.75)
                        sub.setPos(x+8,y+37)
                        sub.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                        sub.setParentItem(item)
                    if w >= 27:
                        for edge_x in (x+3,x+w-3):
                            grip=scene.addLine(edge_x,y+20,edge_x,y+43,
                                               QPen(QColor(c['on_accent'] if track.kind=='melody'
                                                           else c['secondary']),1.2))
                            grip.setParentItem(item)
                            grip.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            if not self.arrangement.tracks:
                msg=scene.addText('＋ 点击上方「添加素材」开始创建音轨')
                msg.setDefaultTextColor(muted)
                msg.setPos(32,ArrangementTimeline.RULER+46)
            self.timeline.horizontalScrollBar().setValue(sx)
            self.timeline.verticalScrollBar().setValue(sy)
            self.track_scroll.verticalScrollBar().setValue(
                self.timeline.verticalScrollBar().value())
        finally:self._is_drawing=False

    def _zoom_changed(self,value):
        old=self.beat_width
        self.beat_width=float(value)
        x=self.timeline.horizontalScrollBar().value()/old if old>0 else 0
        self._draw_timeline()
        self.timeline.horizontalScrollBar().setValue(round(x*self.beat_width))

    def fit_timeline(self):
        # Preserve a useful minimum width even if the song is short.
        available=max(440,self.timeline.viewport().width()-36)
        target=max(16.,self._end_beat()+2)
        self.zoom_control.setValue(max(14,min(128,round(available/target))))
        self.timeline.horizontalScrollBar().setValue(0)

    def update_hint(self):
        self.help_label.setText('拖动片段移动 · 拖动左右边缘裁剪 · Ctrl+拖动复制 · 双击打开素材 · Ctrl+滚轮缩放')

    def show_drag_hint(self,ti,ci,mode,delta,duplicate):
        description={'move':'移动','trim_left':'裁剪起点','trim_right':'裁剪终点'}[mode]
        if duplicate:description='复制并移动'
        self.help_label.setText(f'{description} · 偏移 {delta:+.2f} 拍 · 松开鼠标应用（可撤销）')

    def timeline_change(self,ti,ci,mode,delta,target,duplicate=False):
        self.update_hint()
        try:
            if not 0<=ti<len(self.arrangement.tracks):return
            original=self.arrangement.tracks[ti].clips[ci]
            changed=change_clip_on_timeline(original,mode,delta,
                                            self._source_length(original),self._snap_step())
            dst=ti
            if mode=='move' and 0<=target<len(self.arrangement.tracks):
                if self.arrangement.tracks[target].kind==self.arrangement.tracks[ti].kind:
                    dst=target
            if not duplicate and changed==original and dst==ti:return
            updated=deepcopy(self.arrangement)
            if duplicate:
                updated.tracks[dst].clips.append(changed)
                chosen=len(updated.tracks[dst].clips)-1
            elif dst!=ti:
                del updated.tracks[ti].clips[ci]
                updated.tracks[dst].clips.append(changed)
                chosen=len(updated.tracks[dst].clips)-1
            else:
                updated.tracks[ti].clips[ci]=changed
                chosen=ci
            updated.validate()
            self._snapshot()
            self.arrangement=updated
            self.selected_track=dst
            self.selected_clip_index=chosen
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def add_source(self):
        from .arrangement import find_project_root
        root=find_project_root(self.path)
        path,_=QFileDialog.getOpenFileName(self,'添加素材',str(root),
                                           'Melody 音乐文件 (*.jianpu *.drum)')
        if not path:return
        try:
            newer=deepcopy(self.arrangement)
            target=None
            kind='melody' if Path(path).suffix.lower()=='.jianpu' else 'drum'
            if 0<=self.selected_track<len(newer.tracks) and newer.tracks[self.selected_track].kind==kind:
                answer=QMessageBox.question(self,'插入方式',
                    '追加到选中音轨末尾？\n选择「否」会创建一条新音轨。',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
                if answer==QMessageBox.StandardButton.Yes:target=self.selected_track
            start=max((c.start_beat+self._length(c) for c in newer.tracks[target].clips),default=0.) if target is not None else 0.
            target=add_clip(newer,self.path,path,track_index=target,start_beat=start,project_root=root)
            self._snapshot()
            self.arrangement=newer
            self.selected_track=target
            self.selected_clip_index=len(newer.tracks[target].clips)-1
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def delete_selected(self):
        if self.current_clip() is not None:self.delete_clip()
        else:self.delete_track()

    def delete_clip(self):
        if self.current_clip() is None:return
        if QMessageBox.question(self,'删除片段','从编排中移除此片段？源文件不会被删除。',
             QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self._snapshot()
        del self.arrangement.tracks[self.selected_track].clips[self.selected_clip_index]
        self.selected_clip_index=None
        self.refresh()

    def duplicate_clip(self):
        clip=self.current_clip()
        if clip is None:return
        changed=deepcopy(self.arrangement)
        copy=deepcopy(clip)
        copy.start_beat=snap_beat(clip.start_beat+self._length(clip),self._snap_step())
        changed.tracks[self.selected_track].clips.insert(self.selected_clip_index+1,copy)
        changed.validate()
        self._snapshot()
        self.arrangement=changed
        self.selected_clip_index+=1
        self.refresh()

    def split_selected(self,position=None):
        clip=self.current_clip()
        if clip is None:return
        try:
            if position is None:position=clip.start_beat+self._length(clip)/2
            a,b=split_clip(clip,position,self._source_length(clip),self._snap_step())
            changed=deepcopy(self.arrangement)
            clips=changed.tracks[self.selected_track].clips
            clips[self.selected_clip_index:self.selected_clip_index+1]=[a,b]
            changed.validate()
            self._snapshot()
            self.arrangement=changed
            self.selected_clip_index+=1
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def open_selected_source(self):
        clip=self.current_clip()
        if clip is None:return
        try:self.open_source_requested.emit(str(resolve_source(self.path,clip.source)))
        except Exception as exc:self.error_message.emit(str(exc))

    def move_track(self,delta):
        if self.selected_track<0:return
        changed=deepcopy(self.arrangement)
        try:
            changed.move_track(self.selected_track,delta)
            self._snapshot()
            self.arrangement=changed
            self.selected_track+=delta
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def delete_track(self):
        if self.selected_track<0:return
        track=self.arrangement.tracks[self.selected_track]
        if QMessageBox.question(self,'删除音轨',f'删除「{track.name}」及其全部片段？\n素材文件不会删除。',
           QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self._snapshot()
        del self.arrangement.tracks[self.selected_track]
        self.selected_track=min(self.selected_track,len(self.arrangement.tracks)-1)
        self.selected_clip_index=None
        self.refresh()

    def apply_clip(self):
        clip=self.current_clip()
        if clip is None:return
        try:
            changed=deepcopy(self.arrangement)
            current=changed.tracks[self.selected_track].clips[self.selected_clip_index]
            current.start_beat=self.start.value()
            current.trim_start=self.trim_start.value()
            current.trim_end=self.trim_end.value()
            current.gain=self.gain.value()
            current.reversed=self.reversed.isChecked()
            changed.validate()
            if current.trim_end>self._source_length(current)+.0001:
                raise ValueError('裁剪终点不能超过素材长度')
            if changed==self.arrangement:return
            self._snapshot()
            self.arrangement=changed
            self.refresh()
        except Exception as exc:self.error_message.emit(str(exc))

    def toggle_mute(self):
        if self.selected_track<0:return
        self._snapshot()
        track=self.arrangement.tracks[self.selected_track]
        track.muted=not track.muted
        self.refresh()

    def toggle_solo(self):
        if self.selected_track<0:return
        self._snapshot()
        track=self.arrangement.tracks[self.selected_track]
        track.solo=not track.solo
        self.refresh()

    def set_track_instrument(self,value):
        if self.selected_track<0:return
        track=self.arrangement.tracks[self.selected_track]
        if track.kind!='melody' or track.instrument==value:return
        if value not in INSTRUMENTS:return
        self._snapshot()
        track.instrument=value
        self.refresh()

    def undo(self):
        if not self.history:return
        self.redo_history.append(deepcopy(self.arrangement))
        self.arrangement=self.history.pop()
        self.selected_clip_index=None
        self.refresh()
        self.changed.emit()

    def redo(self):
        if not self.redo_history:return
        self.history.append(deepcopy(self.arrangement))
        self.arrangement=self.redo_history.pop()
        self.selected_clip_index=None
        self.refresh()
        self.changed.emit()

    def set_theme(self,theme):
        self.theme=theme
        self.refresh()

@dataclass
class OpenDocument:
    path: Path | None
    kind: str
    widget: QWidget
    dirty: bool = False
    label: str = '未命名'
    instrument: str = 'piano'
    speed: str = '1.00×'

    @property
    def title(self):return self.path.name if self.path else self.label


class AsyncAudioSignals(QObject):
    ready=Signal(int,str,str)


class AsyncVisionSignals(QObject):
    ready=Signal(object,str,str)


from .preview_engine import render_preview
from .playback import WindowsMCIPlayer, PlaybackError


def synthesis_spinner_icon(theme: str, phase: int, size: int = 18) -> QIcon:
    """Draw a crisp 12-spoke spinner for the play button (at 2x DPI).

    No GIF/resource file: the QTimer rotates its opacity head while rendering
    runs on the worker thread. The spinner uses the active theme's foreground.
    """
    px=QPixmap(size*2,size*2)
    px.setDevicePixelRatio(2)
    px.fill(Qt.GlobalColor.transparent)
    painter=QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(size/2,size/2)
    painter.setPen(Qt.PenStyle.NoPen)
    for spoke in range(12):
        age=(phase-spoke)%12
        color=QColor(COLORS[theme]['on_accent'])
        color.setAlphaF(max(.13,1.-age*.079))
        painter.save()
        painter.rotate(spoke*30.)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(QRectF(-1.65,-8.0,3.3,5.0),1.65,1.65)
        painter.restore()
    painter.end()
    return QIcon(px)


class MelodyMainWindow(QMainWindow):
    def __init__(self, initial_project: Path | None = None):
        super().__init__()
        self.setWindowTitle('Melody Notation — PySide6 工作台')
        self.setWindowIcon(line_icon('note',COLORS['light']['accent']))
        self.resize(1520,940);self.setMinimumSize(980,620)
        self.settings=QSettings('MelodyNotation','Desktop')
        self._pc_keys_held={}  # Qt key-code -> MIDI pitch; held until key release
        QApplication.instance().installEventFilter(self)
        saved_theme=self.settings.value('theme','light')
        self.theme=saved_theme if saved_theme in COLORS else 'light'
        self.language=self.settings.value('language','zh')
        if self.language not in ('zh','en'):self.language='zh'
        self.default_save_directory=str(self.settings.value('default_save_directory','') or '')
        self.native_material=self.settings.value('native_material',True,type=bool)
        self.inspector_visible=self.settings.value('inspector_visible',True,type=bool)
        self.project: ProjectWorkspace | None=None
        self.open_docs: list[OpenDocument]=[]
        self._render_id=0
        self._executor=ThreadPoolExecutor(max_workers=1)
        self._audio_dir=TemporaryDirectory(prefix='melody-preview-')
        self.audio_signals=AsyncAudioSignals(self)
        self.audio_signals.ready.connect(self._on_audio_ready)
        self.vision_signals=AsyncVisionSignals(self)
        self.vision_signals.ready.connect(self._on_vision_ready)
        self.media=QMediaPlayer(self)
        self.output=QAudioOutput(self)
        self.media.setAudioOutput(self.output);self.output.setVolume(.8)
        self.media.positionChanged.connect(self._on_audio_position)
        self.media.durationChanged.connect(self._on_audio_duration)
        self.media.playbackStateChanged.connect(self._on_playback_state)
        self.media.errorOccurred.connect(self._audio_error)
        self._seek_dragging=False
        self._seek_after_render=0.
        self._pending_seek_ratio=0.
        # Windows uses the built-in WinMM/MCI waveaudio player first. Qt
        # Multimedia remains the fallback (and the normal backend elsewhere).
        self._mci_player: WindowsMCIPlayer | None = None
        self._using_mci = False
        self._qt_audio_requested = False
        self._mci_timer = QTimer(self)
        self._mci_timer.setInterval(150)
        self._mci_timer.timeout.connect(self._refresh_mci)
        self._rendering=False
        self._spinner_phase=0
        self._spinner_timer=QTimer(self)
        self._spinner_timer.setInterval(85)
        self._spinner_timer.timeout.connect(self._spin_preview_icon)

        # Native window titlebar + one menu row; no duplicate document chrome.
        # The inspector toggle lives in the editor tab corner instead.
        root=QWidget();root.setObjectName('MainSurface');self.setCentralWidget(root)
        outer=QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)

        self.sides=QSplitter(Qt.Orientation.Horizontal)
        self.sides.setChildrenCollapsible(False)
        self.sides.setHandleWidth(1)
        outer.addWidget(self.sides,1)
        self.nav_shell=QWidget();self.nav_shell.setObjectName('NavShell')
        self._sidebar_expanded_width=310
        nav_layout=QHBoxLayout(self.nav_shell)
        nav_layout.setContentsMargins(0,0,0,0);nav_layout.setSpacing(0)
        self.rail=self._make_nav_rail();nav_layout.addWidget(self.rail)
        self.sidebar=self._make_sidebar();nav_layout.addWidget(self.sidebar,1)
        # Keep the *outer* splitter pane within the combined widths of its
        # children: the sidebar has a max width and otherwise dragging the
        # separator exposes an unusable blank strip inside NavShell.
        self._nav_width_min,self._nav_width_max=navigation_width_limits(
            self.rail.width(),self.sidebar.minimumWidth(),self.sidebar.maximumWidth())
        self.nav_shell.setMinimumWidth(self._nav_width_min)
        self.nav_shell.setMaximumWidth(self._nav_width_max)
        self.sides.addWidget(self.nav_shell)

        self.tabs=QTabWidget();self.tabs.setObjectName('EditorTabs')
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True);self.tabs.setMovable(True)
        self.inspector_toggle=QToolButton()
        style_icon_button(self.inspector_toggle,'panel-right',self.theme)
        self.inspector_toggle.setFixedSize(34,34)
        self.inspector_toggle.clicked.connect(self.toggle_inspector)
        self.tabs.setCornerWidget(self.inspector_toggle,Qt.Corner.TopRightCorner)
        self.tabs.currentChanged.connect(self._change_tab)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.sides.addWidget(self.tabs)
        self.inspector=self._make_inspector();self.sides.addWidget(self.inspector)
        self.inspector.setVisible(self.inspector_visible)
        self.sides.setStretchFactor(0,0);self.sides.setStretchFactor(1,1)
        self.sides.setStretchFactor(2,0)
        self.sides.setSizes([310,920,290] if self.inspector_visible else [310,1210,0])
        # Permanent status-bar widget keeps the version visible with or without
        # the right inspector, while ordinary status messages stay on the left.
        self.version_label=QLabel(f'Melody Notation v{__version__}')
        self.version_label.setObjectName('VersionLabel')
        self.version_label.setProperty('_melody_no_translate',True)
        self.version_label.setToolTip(f'Melody Notation v{__version__}')
        self.statusBar().addPermanentWidget(self.version_label)
        self.statusBar().showMessage('准备就绪')
        self._setup_menu()
        self._apply_theme()
        self._apply_language()
        if initial_project:
            self.open_project(initial_project)
        else:
            recents=load_recent_projects()
            if recents:self.open_project(recents[0])
            else:
                demo=Path(__file__).resolve().parent.parent/'demo_projects'/'我的第一份工程'
                if demo.is_dir():self.open_project(demo)
        if not self.open_docs:
            self.open_sample()

    def eventFilter(self, obj, event):
        """Keyboard-play only in the active score; never hijack text input.

        QEvent filters track press/release, so held keys can sustain notes.
        Ignore auto-repeat and global commands, as well as modal dialogues.
        """
        kind=event.type()
        if kind==QEvent.Type.ApplicationDeactivate:
            # Losing focus mid-note should never leave a hanging live voice.
            doc=self._doc() if hasattr(self,'tabs') else None
            if doc is not None and doc.kind=='jianpu':doc.widget.release_source('keyboard')
            self._pc_keys_held.clear()
        if kind not in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
            return super().eventFilter(obj,event)
        doc=self._doc() if hasattr(self,'tabs') else None
        if doc is None or doc.kind!='jianpu' or QApplication.activeModalWidget():
            return super().eventFilter(obj,event)
        if QApplication.activeWindow() not in (None,self):
            return super().eventFilter(obj,event)
        focused=QApplication.focusWidget()
        if isinstance(focused,(QLineEdit,QPlainTextEdit,QComboBox,QAbstractSpinBox)):
            return super().eventFilter(obj,event)
        if event.isAutoRepeat():return super().eventFilter(obj,event)
        key_code=event.key()
        # Release held notes even when Ctrl/Alt was pressed after the onset.
        if kind==QEvent.Type.KeyRelease and key_code in self._pc_keys_held:
            pitch=self._pc_keys_held.pop(key_code)
            doc.widget.perform_note_off(pitch,'keyboard')
            return True
        if event.modifiers() & (Qt.KeyboardModifier.ControlModifier |
                                Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
            return super().eventFilter(obj,event)
        if kind==QEvent.Type.KeyPress:
            try:key=normalized_key(event.text())
            except ValueError:return super().eventFilter(obj,event)
            pitch=doc.widget.keyboard_panel.pitch_for_key(key)
            if pitch is not None and key_code not in self._pc_keys_held:
                self._pc_keys_held[key_code]=pitch
                doc.widget.perform_note_on(pitch,90,'keyboard')
                return True
        return super().eventFilter(obj,event)

    def _rail_button(self, glyph: str, tip: str, click=None):
        button=QToolButton()
        style_icon_button(button,glyph,self.theme,tip)
        if click is not None:button.clicked.connect(click)
        return button

    def _make_nav_rail(self):
        rail=QWidget();rail.setObjectName('NavRail');rail.setFixedWidth(54)
        col=QVBoxLayout(rail);col.setContentsMargins(7,12,7,12);col.setSpacing(5)
        self.sidebar_toggle=self._rail_button('panel-left','展开／收起项目侧栏',self.toggle_sidebar)
        col.addWidget(self.sidebar_toggle)
        self.rail_new=self._rail_button('plus','新建音乐文件')
        # Menu opens on click without Qt drawing a second dropdown chevron.
        col.addWidget(self.rail_new)
        self.rail_search=self._rail_button('search','搜索项目文件',self.focus_search)
        col.addWidget(self.rail_search)
        col.addStretch(1)
        self.help_button=self._rail_button('help','帮助 / Help  F1',self.show_help)
        col.addWidget(self.help_button)
        self.settings_button=self._rail_button('settings','设置 / Settings',self.show_settings)
        col.addWidget(self.settings_button)
        return rail

    def _make_sidebar(self):
        sidebar=QWidget();sidebar.setObjectName('Sidebar')
        sidebar.setMinimumWidth(206);sidebar.setMaximumWidth(345)
        main=QVBoxLayout(sidebar)
        main.setContentsMargins(13,15,13,14);main.setSpacing(9)
        brand=QLabel('Melody Notation');brand.setObjectName('BrandName')
        main.addWidget(brand)
        self.new_menu_button=QToolButton()
        self.new_menu_button.setObjectName('NewItemButton')
        self.new_menu_button.setText('新建音乐文件')
        self.new_menu_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.new_menu_button.setIcon(line_icon('plus',COLORS[self.theme]['secondary']))
        # Keep the whole button clickable; no native dropdown arrow decoration.
        main.addWidget(self.new_menu_button)
        self.search=QLineEdit();self.search.setPlaceholderText('搜索项目文件')
        self.search.setObjectName('ProjectSearch')
        self.search.textChanged.connect(self._filter_project)
        main.addWidget(self.search)
        main.addSpacing(7)
        recent_head=QLabel('最近项目');recent_head.setObjectName('SectionLabel')
        main.addWidget(recent_head)
        self.recent_selector=QListWidget();self.recent_selector.setObjectName('RecentProjectList')
        self.recent_selector.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_selector.itemClicked.connect(self._open_recent_item)
        self.recent_selector.setMaximumHeight(136)
        main.addWidget(self.recent_selector)
        project_head=row()
        project_label=QLabel('项目文件');project_label.setObjectName('SectionLabel')
        project_head.addWidget(project_label);project_head.addStretch(1)
        self.operations=QToolButton()
        self.operations.setObjectName('ProjectMore')
        # A plain icon action opens the menu without an extra dropdown marker.
        style_icon_button(self.operations,'more',self.theme,'项目操作')
        self.operations.setObjectName('ProjectMore')
        self.operations.setFixedSize(32,32)
        project_head.addWidget(self.operations)
        main.addLayout(project_head)
        self.project_tree=QTreeWidget();self.project_tree.setHeaderHidden(True)
        self.project_tree.setObjectName('ProjectTree')
        self.project_tree.setIndentation(14)
        self.project_tree.itemClicked.connect(self._item_open)
        self.project_tree.itemDoubleClicked.connect(self._item_open)
        self.project_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self._item_menu)
        main.addWidget(self.project_tree,1)
        self.refresh_recents()
        return sidebar

    def focus_search(self):
        if not self.sidebar.isVisible():self.toggle_sidebar()
        self.search.setFocus()
        self.search.selectAll()

    def _open_recent_item(self,item):
        raw=item.data(Qt.ItemDataRole.UserRole)
        if raw:self.open_project(Path(raw))

    def toggle_inspector(self):
        self.inspector.setVisible(not self.inspector.isVisible())
        self.inspector_visible=self.inspector.isVisible()
        self.settings.setValue('inspector_visible',self.inspector_visible)
        if self.inspector.isVisible():
            # Restoring the inspector must not reset a user-resized sidebar.
            widths=self.sides.sizes()
            nav=self.rail.width() if not self.sidebar.isVisible() else max(
                self._nav_width_min,min(self._nav_width_max,widths[0]))
            self.sides.setSizes([nav,max(1,sum(widths)-nav-290),290])


    def _make_inspector(self):
        side=QWidget();side.setObjectName('Inspector');side.setMinimumWidth(242);side.setMaximumWidth(430)
        lay=QVBoxLayout(side);lay.setContentsMargins(11,12,11,12);lay.setSpacing(12)
        playbox=QFrame();playbox.setObjectName('InspectorCard');pb=QVBoxLayout(playbox)
        controls=row()
        self.play_button=ui_button('播放',self.play);self.play_button.setObjectName('Primary')
        self.play_button.setIcon(line_icon('play',COLORS[self.theme]['on_accent']))
        self.stop_button=ui_button('停止',self.stop)
        self.stop_button.setIcon(line_icon('stop',COLORS[self.theme]['secondary']))
        controls.addWidget(self.play_button,2);controls.addWidget(self.stop_button,1);pb.addLayout(controls)
        self.scrubber=QSlider(Qt.Orientation.Horizontal);self.scrubber.setRange(0,1000)
        self.scrubber.sliderPressed.connect(lambda:setattr(self,'_seek_dragging',True))
        self.scrubber.sliderReleased.connect(self._seek_release)
        pb.addWidget(self.scrubber)
        self.time_label=QLabel('00:00 / 00:00');self.time_label.setObjectName('Muted');pb.addWidget(self.time_label)
        options=QFormLayout()
        self.instrument=QComboBox();self.instrument.addItems(INSTRUMENTS.keys())
        self.instrument.currentTextChanged.connect(self._instrument_changed)
        options.addRow('音色',self.instrument)
        self.speed=QComboBox();self.speed.addItems(['1.00×','1.25×','1.50×','1.75×','2.00×'])
        self.speed.currentTextChanged.connect(self._speed_changed)
        options.addRow('倍速',self.speed)
        pb.addLayout(options);lay.addWidget(playbox)
        self.properties=QFrame();self.properties.setObjectName('InspectorCard');props=QVBoxLayout(self.properties)
        self.property_stack=QStackedWidget()
        self.property_stack.setObjectName('PropertyStack')
        self.property_stack.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
        props.addWidget(self.property_stack)
        # Never stretch the properties card into a giant tinted rectangle.
        # Keep its natural height and leave the rest of the sidebar clear.
        self.properties.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
        lay.addWidget(self.properties,0,Qt.AlignmentFlag.AlignTop)
        lay.addStretch(1)
        blank=QLabel('选择乐谱音符、鼓点或音轨，以编辑属性。')
        blank.setWordWrap(True);blank.setObjectName('Muted')
        self.property_stack.addWidget(blank)
        self.note_inspector=self._make_note_inspector()
        self.property_stack.addWidget(self.note_inspector)
        self.track_inspector=self._make_track_inspector()
        self.property_stack.addWidget(self.track_inspector)
        self.drum_inspector=self._make_drum_inspector()
        self.property_stack.addWidget(self.drum_inspector)
        return side

    def _make_note_inspector(self):
        container=QWidget();container.setObjectName('NoteInspector')
        v=QVBoxLayout(container);v.setContentsMargins(0,0,0,0)
        self.note_location=QLabel('尚未选中音符');self.note_location.setObjectName('Muted');v.addWidget(self.note_location)
        form=QFormLayout()
        self.note_degree=QComboBox();self.note_degree.addItems([str(n) for n in range(8)])
        self.note_octave=QSpinBox();self.note_octave.setRange(-3,3)
        self.note_duration=QComboBox();self.note_duration.setObjectName('DurationCombo')
        for n in DURATIONS:self.note_duration.addItem(f'{n:g} 拍',f'{n:g}')
        self.note_accidental=QComboBox();self.note_accidental.addItems(['♭ 降半音','♮ 自然','♯ 升半音'])
        self.note_ornament=QComboBox();self.note_ornament.addItems(['无','tr','mordent','lower_mordent','turn','staccato','accent','tenuto','tremolo'])
        for t,w in [('音级 / 休止',self.note_degree),('八度',self.note_octave),
                    ('时值',self.note_duration),('升降号',self.note_accidental),('演奏记号',self.note_ornament)]:
            form.addRow(t,w)
        v.addLayout(form)
        v.addWidget(ui_button('应用到音符',self.apply_note,True))
        actions=row(ui_button('后插入',lambda:self._score_command('insert_after')),
                    ui_button('删除音符',lambda:self._score_command('delete_selected')))
        v.addLayout(actions)
        v.addWidget(QLabel('连音线'))
        v.addLayout(row(ui_button('设起点',lambda:self._score_command('slur_start')),
                        ui_button('连接',lambda:self._score_command('slur_finish')),
                        ui_button('移除',lambda:self._score_command('slur_remove'))))
        return container

    def _make_track_inspector(self):
        widget=QWidget();widget.setObjectName('TrackInspector')
        v=QVBoxLayout(widget);v.setContentsMargins(0,0,0,0)
        hint=QLabel('选中轨道后可更改音色、静音或 Solo。\n片段裁剪、反转和移动在中央编辑。')
        hint.setObjectName('Muted');hint.setWordWrap(True);v.addWidget(hint)
        self.track_instrument=QComboBox();self.track_instrument.addItems(INSTRUMENTS.keys())
        v.addWidget(self.track_instrument)
        v.addWidget(ui_button('设置轨道音色',self.apply_track_instrument))
        v.addLayout(row(ui_button('静音',lambda:self._track_command('toggle_mute')),
                        ui_button('Solo',lambda:self._track_command('toggle_solo'))))
        return widget

    def _make_drum_inspector(self):
        widget=QWidget();widget.setObjectName('DrumInspector')
        v=QVBoxLayout(widget);v.setContentsMargins(0,0,0,0)
        info=QLabel('点击中央的步进格编写节奏。\n底鼓 Kick / 军鼓 Snare / 踩镲 Hi-hat。')
        info.setWordWrap(True);info.setObjectName('Muted');v.addWidget(info)
        v.addWidget(QLabel('鼓组切换'))
        self.drum_kit=QComboBox();self.drum_kit.addItems(DRUM_KITS);v.addWidget(self.drum_kit)
        v.addWidget(ui_button('应用鼓组',self.apply_drum_kit))
        return widget
    def _setup_menu(self):
        # Keep application commands in one ordinary desktop menubar, not in
        # duplicate popups in the sidebar and header.
        bar=self.menuBar()
        bar.setObjectName('AppMenuBar')
        file_=bar.addMenu('文件')
        for text,fn,shortcut in [
            ('新建项目',self.new_project,None),('打开项目',self.choose_project,None),
            ('打开音乐文件',self.choose_file,'Ctrl+O'),
            ('新建简谱',lambda:self.new_doc('jianpu'),'Ctrl+N'),
            ('新建鼓点',lambda:self.new_doc('drum'),None),
            ('新建多轨工程',lambda:self.new_doc('mtrack'),None),
            ('保存',self.save_current,'Ctrl+S'),
            ('另存为',self.save_as,'Ctrl+Shift+S'),
            ('关闭标签',lambda:self.close_tab(self.tabs.currentIndex()),'Ctrl+W')]:
            action=file_.addAction(text);action.triggered.connect(fn)
            if shortcut:action.setShortcut(QKeySequence(shortcut))
        file_.addSeparator()
        file_.addAction('图片识谱（Beta）',self.open_ocr)
        samples=file_.addMenu('内置示例')
        for filename,label in [('shanfeng.jianpu','山风'),('huang.jianpu','荒'),
                               ('visual_demo.jianpu','可视化示例'),('chiptune_ornaments.jianpu','像素冒险'),('yueguang.jianpu','月光（图片样例）')]:
            samples.addAction(label,lambda checked=False,name=filename:self.open_sample(name))
        edit=bar.addMenu('编辑')
        for text,fn,shortcut in [('撤销',self.undo,'Ctrl+Z'),('重做',self.redo,'Ctrl+Y'),
                                 ('检查节拍 / 文件',self.validate_current,None)]:
            action=edit.addAction(text);action.triggered.connect(fn)
            if shortcut:action.setShortcut(QKeySequence(shortcut))
        view=bar.addMenu('视图')
        view.addAction('展开／收起项目侧栏',self.toggle_sidebar)
        view.addAction('展开／收起属性面板',self.toggle_inspector)
        export=bar.addMenu('导出')
        for extension in ('.mid','.wav','.mp3','.png'):
            a=export.addAction(extension.upper().lstrip('.'))
            a.triggered.connect(lambda checked=False,ext=extension:self.export_current(ext))
        help_menu=bar.addMenu('帮助')
        help_menu.addAction('使用教程 F1',self.show_help)
        help_menu.addAction('设置',self.show_settings)
        # Only project-scoped actions appear in the project ellipsis menu.
        project_menu=QMenu(self)
        project_menu.addAction('新建项目',self.new_project)
        project_menu.addAction('打开项目',self.choose_project)
        project_menu.addSeparator()
        project_menu.addAction('新建子文件夹',self.new_folder)
        project_menu.addAction('重命名项目文件',self.rename_selected)
        project_menu.addAction('删除选中项目项…',self.delete_selected_project_item)
        self.operations.clicked.connect(
            lambda: project_menu.popup(self.operations.mapToGlobal(
                self.operations.rect().bottomLeft())))
        new_menu=QMenu(self)
        new_menu.addAction('新建简谱',lambda:self.new_doc('jianpu'))
        new_menu.addAction('新建鼓点',lambda:self.new_doc('drum'))
        new_menu.addAction('新建多轨工程',lambda:self.new_doc('mtrack'))
        new_menu.addSeparator()
        new_menu.addAction('新建项目',self.new_project)
        self.new_menu_button.clicked.connect(
            lambda: new_menu.popup(self.new_menu_button.mapToGlobal(
                self.new_menu_button.rect().bottomLeft())))
        rail_menu=QMenu(self)
        rail_menu.addAction('新建简谱',lambda:self.new_doc('jianpu'))
        rail_menu.addAction('新建鼓点',lambda:self.new_doc('drum'))
        rail_menu.addAction('新建多轨工程',lambda:self.new_doc('mtrack'))
        rail_menu.addSeparator()
        rail_menu.addAction('新建项目',self.new_project)
        self.rail_new.clicked.connect(
            lambda: rail_menu.popup(self.rail_new.mapToGlobal(
                self.rail_new.rect().bottomLeft())))
        QShortcut(QKeySequence('F1'),self,activated=self.show_help)
        QShortcut(QKeySequence('Ctrl+Tab'),self,activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Space'),self,activated=self.play)
        QShortcut(QKeySequence('Ctrl+Shift+F'),self,activated=self.focus_search)
        QShortcut(QKeySequence('Ctrl+I'),self,activated=self.toggle_inspector)

    def _apply_theme(self):
        self.setStyleSheet(stylesheet(self.theme))
        for doc in self.open_docs:
            if hasattr(doc.widget,'set_theme'):doc.widget.set_theme(self.theme)
        # Qt vector glyphs are regenerated at 3x DPR, centered on the same rail grid.
        for widget,glyph,tooltip in (
            (self.sidebar_toggle,'panel-left','展开／收起项目侧栏'),
            (self.rail_new,'plus','新建音乐文件'),
            (self.rail_search,'search','搜索项目文件'),
            (self.help_button,'help','帮助 F1'),
            (self.settings_button,'settings','设置'),
            (self.inspector_toggle,'panel-right','展开／收起属性面板'),
            (self.operations,'more','项目操作')):
            style_icon_button(widget,glyph,self.theme,tooltip)
            if widget is self.inspector_toggle:
                widget.setFixedSize(34,34)
            if widget is self.operations:
                widget.setObjectName('ProjectMore');widget.setFixedSize(32,32)
        self.new_menu_button.setIcon(line_icon('plus',COLORS[self.theme]['secondary']))
        self._set_play_button(False)
        self.stop_button.setIcon(line_icon('stop',COLORS[self.theme]['secondary']))
        for button in self.findChildren(QPushButton):
            glyph=button.property('_melody_glyph')
            if glyph:button.setIcon(line_icon(glyph,COLORS[self.theme]['secondary']))
        if self.project is not None:self._update_tree_icons()
        apply_native_chrome(self,self.theme,self.native_material)
        self.settings.setValue('theme',self.theme)

    def _apply_language(self):
        translate_widgets(self,self.language)
        for doc in self.open_docs:doc.widget.setProperty('_melody_language',self.language)
        self._set_play_button(self._using_mci and self._mci_player is not None
                              and self._mci_player.state=='playing'
                              or (not self._using_mci and self.media.playbackState()
                                  == QMediaPlayer.PlaybackState.PlayingState))
        self.setWindowTitle('Melody Notation — 项目工作台' if self.language=='zh'
                            else 'Melody Notation — Workbench')
        names={'文件':'File','编辑':'Edit','视图':'View','导出':'Export','帮助':'Help'}
        for menu in [a.menu() for a in self.menuBar().actions() if a.menu() is not None]:
            zh=menu.property('_melody_menu_zh')
            if zh is None:
                zh=menu.title();menu.setProperty('_melody_menu_zh',zh)
            menu.setTitle(names.get(zh,zh) if self.language=='en' else zh)
        self.sidebar_toggle.setToolTip('展开／收起项目侧栏' if self.language=='zh' else 'Toggle projects sidebar')
        self.inspector_toggle.setToolTip('展开／收起属性面板' if self.language=='zh' else 'Toggle properties panel')
        self.help_button.setToolTip('帮助 F1' if self.language=='zh' else 'Help F1')
        self.settings_button.setToolTip('设置' if self.language=='zh' else 'Settings')
        self.settings.setValue('language',self.language)

    def show_settings(self):
        dialog=PreferencesDialog(self,theme=self.theme,language=self.language,
                  directory=self.default_save_directory,native_material=self.native_material)
        if dialog.exec()!=dialog.DialogCode.Accepted:return
        values=dialog.values()
        self.theme=values['theme'];self.language=values['language']
        self.default_save_directory=values['default_save_directory']
        self.native_material=values['native_material']
        self.settings.setValue('default_save_directory',self.default_save_directory)
        self.settings.setValue('native_material',self.native_material)
        self._apply_theme();self._apply_language()
        self.statusBar().showMessage('设置已保存' if self.language=='zh'
                                     else 'Preferences saved',4000)

    def _preferred_dir(self):
        folder=Path(self.default_save_directory).expanduser() if self.default_save_directory else None
        if folder and folder.is_dir():return folder
        return self.project.root if self.project else Path.home()

    def toggle_sidebar(self):
        """Collapse the *splitter pane*, not merely its sidebar child.

        Hiding the inner QWidget alone leaves the outer NavShell at the old
        splitter width (a dead blank region to the left of the editor).
        Temporarily fixing the shell to the 54 px rail makes Qt reflow the
        editor; reopening restores the user's previous sidebar width.
        """
        show=not self.sidebar.isVisible()
        sizes=self.sides.sizes()
        if show:
            self.sidebar.setVisible(True)
            self.nav_shell.setMinimumWidth(self._nav_width_min)
            self.nav_shell.setMaximumWidth(self._nav_width_max)
            target=max(self._nav_width_min,min(self._nav_width_max,
                                               self._sidebar_expanded_width))
            self.sides.setSizes(navigation_split_sizes(sizes,target))
        else:
            self._sidebar_expanded_width=max(self._nav_width_min,
                                              min(self._nav_width_max,sizes[0]))
            self.sidebar.setVisible(False)
            self.nav_shell.setFixedWidth(self.rail.width())
            self.sides.setSizes(navigation_split_sizes(sizes,self.rail.width()))
        self.nav_shell.updateGeometry()

    def toggle_theme(self):
        # Kept for existing compatibility tests/shortcuts; all themes live in Settings.
        self.theme='dark' if self.theme=='light' else 'light'
        self._apply_theme()

    def refresh_recents(self):
        current=self.recent_selector.currentItem()
        current_path=current.data(Qt.ItemDataRole.UserRole) if current else None
        self.recent_selector.blockSignals(True);self.recent_selector.clear()
        for project in load_recent_projects():
            item=QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole,str(project))
            item.setToolTip(str(project))
            item.setIcon(line_icon('folder',COLORS[self.theme]['secondary']))
            self.recent_selector.addItem(item)
            if current_path==str(project):self.recent_selector.setCurrentItem(item)
        self.recent_selector.blockSignals(False)

    def _choose_recent(self,index):
        item=self.recent_selector.item(index)
        if item:self._open_recent_item(item)

    def open_project(self,path):
        try:
            project=ProjectWorkspace(Path(path));self.project=project
            remember_project(project.root);self.refresh_recents()
            self.refresh_project_tree()
            self.statusBar().showMessage('项目：'+str(project.root),6000)
        except Exception as exc:error(self,'打开项目失败',exc)

    def choose_file(self):
        parent=str(self._preferred_dir())
        path,_=QFileDialog.getOpenFileName(self,'打开音乐文件',parent,
                              'Melody 文件 (*.jianpu *.drum *.mtrack)')
        if path:self.open_file(path)

    def choose_project(self):
        path=QFileDialog.getExistingDirectory(self,'选择项目文件夹',str(self._preferred_dir()))
        if path:self.open_project(path)

    def new_project(self):
        parent=QFileDialog.getExistingDirectory(self,'选择项目存放位置',str(self._preferred_dir()))
        if not parent:return
        name,ok=QInputDialog.getText(self,'新建项目','项目名称')
        if not ok or not name.strip():return
        try:self.open_project(ProjectWorkspace.create(Path(parent),name).root)
        except Exception as exc:error(self,'新建项目失败',exc)

    def refresh_project_tree(self):
        self.project_tree.clear()
        if self.project is None:return
        root=QTreeWidgetItem([self.project.name]);root.setData(0,Qt.ItemDataRole.UserRole,str(self.project.root))
        root.setData(0,Qt.ItemDataRole.UserRole+1,True)
        self.project_tree.addTopLevelItem(root)
        lookup={self.project.root:root}
        for p in self.project.list_dirs():
            node=QTreeWidgetItem([p.name]);node.setData(0,Qt.ItemDataRole.UserRole,str(p))
            node.setData(0,Qt.ItemDataRole.UserRole+1,True)
            lookup[p]=node
            lookup.get(p.parent,root).addChild(node)
        for p in self.project.list_assets():
            node=QTreeWidgetItem([p.name]);node.setData(0,Qt.ItemDataRole.UserRole,str(p))
            node.setData(0,Qt.ItemDataRole.UserRole+1,False)
            lookup.get(p.parent,root).addChild(node)
        root.setExpanded(True)
        for p,node in lookup.items():
            if p!=self.project.root:node.setExpanded(True)
        self._update_tree_icons()
        self._filter_project(self.search.text())

    def _update_tree_icons(self):
        def walk(item):
            raw=item.data(0,Qt.ItemDataRole.UserRole)
            if raw:
                path=Path(raw)
                icon=('folder' if path.is_dir() else
                      {'.jianpu':'note','.drum':'drum','.mtrack':'tracks'}.get(path.suffix.lower(),'folder'))
                item.setIcon(0,line_icon(icon,COLORS[self.theme]['secondary']))
            for i in range(item.childCount()):walk(item.child(i))
        for i in range(self.project_tree.topLevelItemCount()):walk(self.project_tree.topLevelItem(i))

    def _filter_project(self,text):
        needle=text.strip().casefold()
        def walk(item):
            matches=needle in item.text(0).casefold()
            for i in range(item.childCount()):matches=walk(item.child(i)) or matches
            item.setHidden(not matches)
            if needle and matches:item.setExpanded(True)
            return matches
        for i in range(self.project_tree.topLevelItemCount()):walk(self.project_tree.topLevelItem(i))

    def _item_open(self,item,column=0):
        raw=item.data(0,Qt.ItemDataRole.UserRole)
        if not raw:return
        p=Path(raw)
        if p.is_file() and p.suffix.lower() in DOC_EXTENSIONS:self.open_file(p)
        # Qt handles expand/collapse on folder double clicks itself.

    def _item_menu(self,point):
        item=self.project_tree.itemAt(point)
        if not item:return
        # Context actions must operate on the row the user right-clicked,
        # not on a previously selected item elsewhere in the tree.
        self.project_tree.setCurrentItem(item)
        path=item.data(0,Qt.ItemDataRole.UserRole)
        target=Path(path)
        menu=QMenu(self)
        if target.is_file():menu.addAction('打开',lambda:self.open_file(target))
        if self.project is not None and target!=self.project.root:
            menu.addAction('重命名',self.rename_selected)
        if target.is_dir():menu.addAction('新建子文件夹',self.new_folder)
        menu.addSeparator()
        label=('删除项目（移至回收站）…' if self.project is not None and target==self.project.root
               else '删除文件夹（移至回收站）…' if target.is_dir()
               else '删除文件（移至回收站）…')
        menu.addAction(label,self.delete_selected_project_item)
        menu.exec(self.project_tree.viewport().mapToGlobal(point))

    def delete_selected_project_item(self):
        """Delete the selected disk item, closing only tabs beneath that path."""
        if self.project is None:return
        item=self.project_tree.currentItem()
        if item is None:return
        raw=item.data(0,Qt.ItemDataRole.UserRole)
        if not raw:return
        target=Path(raw)
        root=self.project.root
        is_project=target==root
        is_folder=target.is_dir()
        affected=[doc for doc in self.open_docs if doc.path is not None and
                  (doc.path==target or (is_folder and doc.path.is_relative_to(target)))]
        dirty=[doc for doc in affected if doc.dirty or getattr(doc.widget,'source_dirty',False)]
        kind='整个项目' if is_project else ('文件夹' if is_folder else '文件')
        details=(f'“{target.name}”及其所有内容将移入系统回收站。' if is_folder else
                 f'“{target.name}”将移入系统回收站。')
        if dirty:
            details+=f'\n\n注意：{len(dirty)} 个打开的文档有未保存修改，确认删除后这些草稿会丢失。'
        elif affected:
            details+=f'\n\n将同时关闭 {len(affected)} 个打开的编辑标签。'
        if not is_project and (is_folder or target.suffix.lower() in ('.jianpu','.drum')):
            details+='\n\n提示：如果其他多轨编排引用了这些素材，删除后对应片段可能无法播放。'
        choice=QMessageBox.question(
            self,f'删除{kind}',details+'\n\n确定继续吗？',
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if choice!=QMessageBox.StandardButton.Yes:return
        try:
            if is_project:self.project.delete_project()
            else:self.project.delete(target.relative_to(root))
        except Exception as exc:
            error(self,'删除失败',exc)
            return
        if affected:
            self.stop()
        for doc in affected:
            if doc.kind=='jianpu':doc.widget.set_input_active(False)
            index=self.tabs.indexOf(doc.widget)
            self.open_docs.remove(doc)
            if index>=0:self.tabs.removeTab(index)
            doc.widget.deleteLater()
        if is_project:
            self.project=None
            self.refresh_recents()
        self.refresh_project_tree()
        self._update_tab_labels()
        self.statusBar().showMessage(f'已移入系统回收站：{target.name}',6000)

    def _selected_dir(self):
        if self.project is None:raise ValueError('请先打开或创建项目')
        item=self.project_tree.currentItem()
        if item is None:return self.project.root
        path=Path(item.data(0,Qt.ItemDataRole.UserRole))
        if path.is_file():return path.parent
        if path.is_dir():return path
        return self.project.root

    def new_folder(self):
        if self.project is None:
            self.statusBar().showMessage('请先创建或打开项目');return
        name,ok=QInputDialog.getText(self,'新建子文件夹','文件夹名称')
        if not ok or not name.strip():return
        try:
            parent=self._selected_dir()
            self.project.new_folder(str((parent/name).relative_to(self.project.root)))
            self.refresh_project_tree()
        except Exception as exc:error(self,'创建文件夹失败',exc)

    def new_doc(self,kind):
        if self.project is None:
            QMessageBox.information(self,'选择项目','请先创建或打开一个项目。')
            return
        ext='.'+kind
        hint={'jianpu':'新简谱','drum':'新鼓点','mtrack':'新多轨工程'}[kind]
        name,ok=QInputDialog.getText(self,'新建文件','文件名称',text=hint)
        if not ok or not name.strip():return
        if not name.lower().endswith(ext):name+=ext
        try:
            p=self._selected_dir()/name
            relative=p.relative_to(self.project.root).as_posix()
            if kind=='jianpu':
                data=blank_score_text(p.stem)
                p=self.project.new_score(relative,data)
            else:p=self.project.new_asset(relative,kind)
            self.refresh_project_tree();self.open_file(p)
        except Exception as exc:error(self,'新建文件失败',exc)

    def rename_selected(self):
        if self.project is None:return
        item=self.project_tree.currentItem()
        if item is None:return
        path=Path(item.data(0,Qt.ItemDataRole.UserRole))
        if path==self.project.root:
            QMessageBox.information(self,'重命名项目','如需重命名项目根目录，请先在文件管理器中关闭并重命名。');return
        name,ok=QInputDialog.getText(self,'重命名','新名称',text=path.stem if path.is_file() else path.name)
        if not ok or not name.strip():return
        try:
            new=self.project.rename(path.relative_to(self.project.root),name)
            for doc in self.open_docs:
                if doc.path==path:doc.path=new
                elif path.is_dir() and doc.path and doc.path.is_relative_to(path):
                    doc.path=new/doc.path.relative_to(path)
                if doc.kind=='mtrack':
                    doc.widget.path=doc.path
                    # Reload only when tab has no edits; avoid replacing unsaved state.
                    if not doc.dirty and doc.path and doc.path.is_file():
                        doc.widget.arrangement=Arrangement.load(doc.path);doc.widget.path=doc.path
                        doc.widget.refresh()
            self.refresh_project_tree();self._update_tab_labels()
        except Exception as exc:error(self,'重命名失败',exc)

    def open_sample(self, name='shanfeng.jianpu'):
        from importlib import resources
        try:
            if name not in {'shanfeng.jianpu','huang.jianpu','visual_demo.jianpu','chiptune_ornaments.jianpu','yueguang.jianpu'}:
                raise ValueError('未知示例文件')
            path=resources.files(__package__).joinpath('samples', name)
            sample=parse_text(path.read_text(encoding='utf-8'),strict=False)
            w=ScoreEditor(sample)
            self._add_doc(OpenDocument(None,'jianpu',w,False,sample.title+'（示例）'))
        except Exception as exc:error(self,'打开示例失败',exc)

    def open_file(self,path):
        path=Path(path).resolve()
        for i,doc in enumerate(self.open_docs):
            if doc.path==path:self.tabs.setCurrentIndex(i);return
        try:
            suffix=path.suffix.lower()
            if suffix=='.jianpu':
                score=parse_text(path.read_text(encoding='utf-8'),strict=False)
                widget=ScoreEditor(score)
            elif suffix=='.drum':widget=DrumEditor(DrumPattern.load(path))
            elif suffix=='.mtrack':widget=TrackEditor(Arrangement.load(path),path)
            else:raise ValueError('仅支持 .jianpu、.drum、.mtrack')
            self._add_doc(OpenDocument(path,suffix[1:],widget))
        except Exception as exc:error(self,'打开文件失败',exc)

    def _add_doc(self,doc):
        self.open_docs.append(doc)
        doc.widget.changed.connect(lambda d=doc:self._mark_dirty(d))
        doc.widget.setProperty('_melody_language',self.language)
        translate_widgets(doc.widget,self.language)
        doc.widget.error_message.connect(lambda msg:self.statusBar().showMessage(msg,8000))
        if doc.kind=='jianpu':doc.widget.selection_changed.connect(self._sync_note_inspector)
        if doc.kind=='mtrack':
            doc.widget.selection_changed.connect(self._sync_track_inspector)
            doc.widget.open_source_requested.connect(lambda path:self.open_file(Path(path)))
        if hasattr(doc.widget,'set_theme'):doc.widget.set_theme(self.theme)
        index=self.tabs.addTab(doc.widget,doc.title)
        self.tabs.setCurrentIndex(index)
        self._change_tab(index)

    def _doc(self):
        i=self.tabs.currentIndex()
        if i<0:return None
        widget=self.tabs.widget(i)
        return next((d for d in self.open_docs if d.widget is widget),None)

    def _update_tab_labels(self):
        for i in range(self.tabs.count()):
            widget=self.tabs.widget(i)
            doc=next((d for d in self.open_docs if d.widget is widget),None)
            if doc:self.tabs.setTabText(i,('● ' if doc.dirty or getattr(widget,'source_dirty',False) else '')+doc.title)

    def _mark_dirty(self,doc):
        self.stop()
        doc.dirty=True
        self._update_tab_labels()
        self.statusBar().showMessage('有尚未保存的修改',2500)

    def _change_tab(self,index):
        if hasattr(self,'_pc_keys_held'):
            self._pc_keys_held.clear()
        doc=self._doc()
        self._render_id+=1;self._set_rendering(False)
        self._close_mci();self.media.stop()
        self.instrument.blockSignals(True);self.speed.blockSignals(True)
        try:
            self.instrument.setCurrentText(doc.instrument if doc else 'piano')
            self.speed.setCurrentText(doc.speed if doc else '1.00×')
        finally:
            self.instrument.blockSignals(False);self.speed.blockSignals(False)
        # Only the currently visible score owns live MIDI ports and audio.
        for opened in self.open_docs:
            if opened.kind=='jianpu':
                opened.widget.set_input_active(opened is doc)
        if doc is None:
            self.property_stack.setCurrentIndex(0);return
        if doc.kind=='jianpu':
            # The bottom performance keyboard owns its own instrument.
            # Switching tabs must not overwrite it with the preview instrument.
            self.property_stack.setCurrentIndex(1);self._sync_note_inspector()
        elif doc.kind=='mtrack':
            self.property_stack.setCurrentIndex(2)
            self._sync_track_inspector()
        elif doc.kind=='drum':
            self.property_stack.setCurrentIndex(3)
            self.drum_kit.setCurrentText(doc.widget.pattern.kit)
        self.statusBar().showMessage(f'{doc.title}  ·  {doc.kind}',3000)

    def _sync_note_inspector(self):
        doc=self._doc()
        if doc is None or doc.kind!='jianpu':return
        pos=doc.widget.selected_note
        if pos is None:
            self.note_location.setText('请点击谱面中的音符' if self.language=='zh'
                                   else 'Click a note in the score');return
        try:note=get_note(doc.widget.score,*pos)
        except Exception:return
        self.note_location.setText(f'第 {pos[0]} 小节 · 第 {pos[1]} 个音符' if self.language=='zh'
                                   else f'Bar {pos[0]} · Note {pos[1]}')
        self.note_degree.setCurrentText(str(note.degree))
        self.note_octave.setValue(note.octave)
        self.note_duration.setCurrentIndex(next((i for i in range(self.note_duration.count())
            if self.note_duration.itemData(i)==f'{note.beats:g}'),0))
        self.note_accidental.setCurrentIndex(note.accidental+1)
        self.note_ornament.setCurrentText(note.ornament or '无')

    def apply_note(self):
        doc=self._doc()
        if doc and doc.kind=='jianpu':
            doc.widget.replace_note(int(self.note_degree.currentText()),self.note_octave.value(),
                float(self.note_duration.currentData()),self.note_accidental.currentIndex()-1,
                '' if self.note_ornament.currentText()=='无' else self.note_ornament.currentText())

    def _score_command(self,name):
        doc=self._doc()
        if doc and doc.kind=='jianpu':getattr(doc.widget,name)()

    def _track_command(self,name):
        doc=self._doc()
        if doc and doc.kind=='mtrack':getattr(doc.widget,name)()

    def _sync_track_inspector(self):
        doc=self._doc()
        if doc is None or doc.kind!='mtrack':return
        ti=doc.widget.selected_track
        if not 0<=ti<len(doc.widget.arrangement.tracks):return
        track=doc.widget.arrangement.tracks[ti]
        if track.kind=='melody':self.track_instrument.setCurrentText(track.instrument)
        self.track_instrument.setEnabled(track.kind=='melody')

    def apply_track_instrument(self):
        doc=self._doc()
        if doc and doc.kind=='mtrack':doc.widget.set_track_instrument(self.track_instrument.currentText())

    def apply_drum_kit(self):
        doc=self._doc()
        if doc and doc.kind=='drum':
            doc.widget.kit_edit.setCurrentText(self.drum_kit.currentText())
            doc.widget.apply_options()

    def _instrument_changed(self,text):
        doc=self._doc()
        if doc:
            doc.instrument=text
            # Preview instrument is independent from live performance tone.
            self.stop()

    def _speed_changed(self,text):
        doc=self._doc()
        if doc:doc.speed=text
        if (self._using_mci and self._mci_player is not None
                and self._mci_player.state=='playing') or (
                self.media.playbackState()==QMediaPlayer.PlaybackState.PlayingState):
            self.play(force=True)

    def save_current(self):
        doc=self._doc()
        if doc is None:return False
        if doc.path is None:return self.save_as()
        try:
            if doc.kind=='jianpu':
                score=doc.widget.score_for_save()
                doc.path.write_text(text_from_score(score),encoding='utf-8')
                if doc.widget.source_dirty:doc.widget.set_model(score,record=False)
            elif doc.kind=='drum':doc.widget.pattern.save(doc.path)
            else:doc.widget.arrangement.save(doc.path)
            doc.dirty=False;self._update_tab_labels();self.refresh_project_tree()
            self.statusBar().showMessage('已保存：'+doc.title,4000)
            return True
        except Exception as exc:error(self,'保存失败',exc);return False

    def save_as(self):
        doc=self._doc()
        if doc is None:return False
        filename=(doc.path.name if doc.path else doc.label+'.'+doc.kind)
        path,_=QFileDialog.getSaveFileName(self,'另存为',str(self._preferred_dir()/filename),
                                          f'{doc.kind.upper()} (*.{doc.kind})')
        if not path:return False
        target=Path(path)
        if target.suffix.lower()!='.'+doc.kind:target=target.with_suffix('.'+doc.kind)
        if target.exists():
            if QMessageBox.question(self,'覆盖确认',f'文件已存在，确定覆盖？\n{target}')!=QMessageBox.StandardButton.Yes:
                return False
        if doc.kind=='mtrack' and doc.path is not None:
            from .arrangement import find_project_root
            project_root=find_project_root(doc.path)
            if not target.resolve().is_relative_to(project_root):
                QMessageBox.warning(self,'多轨文件路径','多轨工程必须另存为到当前项目内部，以保持素材引用有效。')
                return False
        # Save As only changes the path after successful writing.
        old=doc.path;doc.path=target
        if doc.kind=='mtrack':doc.widget.path=target
        if self.save_current():return True
        doc.path=old
        if doc.kind=='mtrack':doc.widget.path=old
        return False

    def _ask_close(self,doc):
        if not doc.dirty and not getattr(doc.widget,'source_dirty',False):return True
        choice=QMessageBox.question(self,'未保存修改',f'{doc.title} 有未保存的修改，是否保存？',
             QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if choice==QMessageBox.StandardButton.Cancel:return False
        if choice==QMessageBox.StandardButton.Save:
            self.tabs.setCurrentWidget(doc.widget)
            return self.save_current()
        return True

    def close_tab(self,index):
        if index<0 or index>=self.tabs.count():return
        widget=self.tabs.widget(index)
        doc=next((d for d in self.open_docs if d.widget is widget),None)
        if doc is None or not self._ask_close(doc):return
        if doc.kind=='jianpu':doc.widget.set_input_active(False)
        self.tabs.removeTab(index);self.open_docs.remove(doc)
        widget.deleteLater()

    def closeEvent(self,event):
        for doc in list(self.open_docs):
            if not self._ask_close(doc):event.ignore();return
        self.stop();self._executor.shutdown(wait=False,cancel_futures=True)
        for doc in self.open_docs:
            if doc.kind=='jianpu':doc.widget.set_input_active(False)
        QApplication.instance().removeEventFilter(self)
        self._audio_dir.cleanup();event.accept()

    def undo(self):
        doc=self._doc()
        if doc and hasattr(doc.widget,'undo'):doc.widget.undo()

    def redo(self):
        doc=self._doc()
        if doc and hasattr(doc.widget,'redo'):doc.widget.redo()

    def validate_current(self):
        doc=self._doc()
        if doc is None:return
        try:
            if doc.kind=='jianpu':doc.widget.score_for_save().validate(strict=True)
            elif doc.kind=='drum':doc.widget.pattern.validate()
            else:doc.widget.arrangement.validate()
            QMessageBox.information(self,'检查通过','当前文档的数据结构与节拍检查通过。')
        except Exception as exc:error(self,'检查发现问题',exc)

    def export_current(self,extension):
        doc=self._doc()
        if doc is None:return
        if doc.kind!='jianpu' and extension=='.png':
            QMessageBox.information(self,'暂不支持','PNG 导出目前仅用于简谱文件。');return
        if doc.kind=='mtrack' and doc.path is None:
            QMessageBox.information(self,'请先保存','多音轨工程需要先保存到项目目录。');return
        default_path=(self._preferred_dir()/ (doc.path.stem if doc.path else doc.label)).with_suffix(extension)
        target,_=QFileDialog.getSaveFileName(self,'导出',str(default_path),f'{extension} (*{extension})')
        if not target:return
        target=Path(target)
        if target.suffix.lower()!=extension:target=target.with_suffix(extension)
        if target.exists() and QMessageBox.question(self,'覆盖确认',f'覆盖已有文件？\n{target}')!=QMessageBox.StandardButton.Yes:
            return
        try:
            if doc.kind=='jianpu':
                score=doc.widget.score_for_save()
                if extension=='.mid':export_midi(score,target,self.instrument.currentText())
                elif extension=='.png':export_png(score,target)
                else:export_audio(score,target,self.instrument.currentText())
            elif doc.kind=='drum':
                if extension=='.mid':export_drum_midi(doc.widget.pattern,target)
                else:export_drum_audio(doc.widget.pattern,target)
            else:
                if extension=='.mid':export_arrangement_midi(doc.widget.arrangement,doc.path,target)
                else:export_arrangement_audio(doc.widget.arrangement,doc.path,target)
            self.statusBar().showMessage('已导出：'+str(target),6000)
        except Exception as exc:error(self,'导出失败',exc)

    def open_ocr(self):
        image_path,_=QFileDialog.getOpenFileName(self,'识别简谱图片',str(self._preferred_dir()),
                                             '图片 (*.png *.jpg *.jpeg *.webp)')
        if not image_path:return
        self.statusBar().showMessage('正在识别简谱图片…结果需人工校对。')
        def worker():
            from .vision import transcribe_image
            return transcribe_image(image_path)
        future=self._executor.submit(worker)
        def done(f):
            try:
                score,notes=f.result();self.vision_signals.ready.emit(score,notes,'')
            except Exception as exc:self.vision_signals.ready.emit(None,'',str(exc))
        future.add_done_callback(done)

    def _on_vision_ready(self,score,uncertainty,err):
        if err:
            error(self,'图片识谱失败',ValueError(err));return
        editor=ScoreEditor(score)
        doc=OpenDocument(None,'jianpu',editor,True,score.title+'（识谱草稿）')
        self._add_doc(doc)
        self._update_tab_labels()
        self.statusBar().showMessage('识谱草稿已生成，必须逐小节核对后再保存。',10000)
        if uncertainty:
            QMessageBox.warning(self,'请检查识谱结果',uncertainty)

    def _on_audio_position(self,ms):
        if not self._seek_dragging:self.scrubber.setValue(ms)
        self.time_label.setText(self._time(ms)+' / '+self._time(self.media.duration()))

    def _on_audio_duration(self,ms):
        self.scrubber.setRange(0,max(1,ms))
        if ms>0 and self._pending_seek_ratio>0:
            ratio=self._pending_seek_ratio;self._pending_seek_ratio=0.
            self.media.setPosition(round(ratio*ms))
        self._on_audio_position(self.media.position())

    @staticmethod
    def _time(ms):
        total=int(ms/1000);return f'{total//60:02d}:{total%60:02d}'

    def _seek_release(self):
        self._seek_dragging=False
        if self._using_mci and self._mci_player is not None:
            try:
                self._mci_player.seek(self.scrubber.value()/1000.)
                self._refresh_mci()
            except Exception as exc:
                self._playback_failure(str(exc))
        else:
            self.media.setPosition(self.scrubber.value())

    def _set_play_button(self, playing: bool) -> None:
        if self._rendering:
            self.play_button.setText('合成中…' if self.language=='zh' else 'Rendering…')
            self.play_button.setIcon(synthesis_spinner_icon(self.theme,self._spinner_phase))
            return
        self.play_button.setText(('暂停' if playing else '播放') if self.language=='zh'
                                 else ('Pause' if playing else 'Play'))
        self.play_button.setIcon(line_icon('pause' if playing else 'play',
                                           COLORS[self.theme]['on_accent']))

    def _spin_preview_icon(self) -> None:
        if self._rendering:
            self._spinner_phase=(self._spinner_phase+1)%12
            self.play_button.setIcon(synthesis_spinner_icon(self.theme,self._spinner_phase))

    def _set_rendering(self, rendering: bool) -> None:
        self._rendering=bool(rendering)
        if rendering:
            self._spinner_phase=0
            self._spinner_timer.start()
        else:
            self._spinner_timer.stop()
        # Keep button painted in the primary color (disabled Qt buttons dim icons).
        # While working, repeat clicks are ignored by play(); Stop cancels the job.
        self._set_play_button(False)

    def _on_playback_state(self,state):
        if not self._using_mci and not self._rendering:
            self._set_play_button(state==QMediaPlayer.PlaybackState.PlayingState)

    def _playback_failure(self, message: str) -> None:
        """Failures must be visible; the status bar alone was easy to miss."""
        synthesis_failed = message.startswith('合成音频失败：') or message.startswith('Audio synthesis failed:')
        if synthesis_failed:
            detail = ('这是音频合成阶段的错误，与 Windows 输出设备无关。请检查音轨和音色设置。'
                      if self.language == 'zh' else
                      'Audio synthesis failed before playback. Check the track and sound settings.')
        else:
            detail = ('请检查 Windows 默认音频输出设备，或尝试重新启动应用。'
                      if self.language == 'zh' else
                      'Check your default audio output device or restart the app.')
        self.statusBar().showMessage('试听失败：'+message,15000)
        QMessageBox.warning(self,'试听播放失败' if self.language=='zh' else 'Playback failed',
                            f'{message}\n\n{detail}')

    def _audio_error(self,code,text):
        if self._using_mci or not self._qt_audio_requested or not text:return
        self._qt_audio_requested=False
        self._set_play_button(False)
        self._playback_failure('Qt Multimedia: '+text)

    def _close_mci(self) -> None:
        self._mci_timer.stop()
        player=self._mci_player
        self._mci_player=None
        self._using_mci=False
        if player is not None:
            try:player.close()
            except PlaybackError:pass

    def _refresh_mci(self) -> None:
        player=self._mci_player
        if not self._using_mci or player is None:return
        try:
            state=player.state
            pos_ms=round(player.position*1000)
            duration_ms=round(player.duration*1000)
            self.scrubber.setRange(0,max(1,duration_ms))
            if not self._seek_dragging:self.scrubber.setValue(pos_ms)
            self.time_label.setText(self._time(pos_ms)+' / '+self._time(duration_ms))
            self._set_play_button(state=='playing')
            if state=='stopped':
                self._mci_timer.stop()
                self.statusBar().showMessage('试听结束',2500)
        except Exception as exc:
            self._close_mci()
            self._set_play_button(False)
            self._playback_failure(str(exc))

    def play(self,force=False):
        if self._rendering:return  # Avoid scheduling duplicate synthesis jobs.
        # QPushButton.clicked passes its checked bool as the first argument;
        # keep the force parameter for speed-change restarts too.
        if not force and self._using_mci and self._mci_player is not None:
            try:
                state=self._mci_player.state
                if state=='playing':
                    self._mci_player.pause()
                else:
                    self._mci_player.play()
                    self._mci_timer.start()
                self._refresh_mci()
            except Exception as exc:self._playback_failure(str(exc))
            return
        if not force and self.media.playbackState()==QMediaPlayer.PlaybackState.PlayingState:
            self.media.pause();return
        if not force and self.media.playbackState()==QMediaPlayer.PlaybackState.PausedState:
            self.media.play();return
        doc=self._doc()
        if doc is None:
            self._playback_failure('没有打开的音乐文件')
            return
        try:
            if doc.kind=='jianpu':data=deepcopy(doc.widget.score_for_save());data.validate(strict=True)
            elif doc.kind=='drum':data=deepcopy(doc.widget.pattern);data.validate()
            else:data=deepcopy(doc.widget.arrangement);data.validate()
            if force and self._using_mci and self._mci_player is not None and self._mci_player.duration>0:
                self._seek_after_render=self._mci_player.position/self._mci_player.duration
            elif force and self.media.duration()>0:
                self._seek_after_render=self.media.position()/self.media.duration()
            else:self._seek_after_render=0.
            self._close_mci()
            self._qt_audio_requested=False
            self.media.stop();self._render_id+=1;rid=self._render_id
            path=str(Path(self._audio_dir.name)/f'preview_{rid}.wav')
            speed=float(self.speed.currentText().replace('×',''))
            ins=self.instrument.currentText()
            self.statusBar().showMessage('正在合成试听音频…')
            self._set_rendering(True)
            future=self._executor.submit(render_preview,doc.kind,data,doc.path,ins,speed,path)
            def complete(f):
                try:self.audio_signals.ready.emit(rid,f.result(),'')
                except Exception as exc:self.audio_signals.ready.emit(rid,'',str(exc))
            future.add_done_callback(complete)
        except Exception as exc:
            self._set_rendering(False)
            self._playback_failure(str(exc))

    def _on_audio_ready(self,rid,path,exc):
        if rid!=self._render_id:return
        self._set_rendering(False)
        if exc:
            self._playback_failure('合成音频失败：'+exc)
            return
        wav=Path(path)
        if not wav.is_file() or wav.stat().st_size<=44:
            self._playback_failure('未能生成有效的 WAV 音频')
            return
        seek_ratio=max(0.,min(.999,self._seek_after_render))
        self._seek_after_render=0.
        if os.name=='nt':
            try:
                player=WindowsMCIPlayer()
                try:
                    player.load_file(wav)
                    if seek_ratio:player.seek(player.duration*seek_ratio)
                    player.play()
                except Exception:
                    player.close()
                    raise
                self._qt_audio_requested=False
                self.media.stop()
                self._mci_player=player
                self._using_mci=True
                self._mci_timer.start()
                self._refresh_mci()
                self.statusBar().showMessage('正在试听 · Windows 系统音频',3500)
                return
            except Exception as mci_error:
                self.statusBar().showMessage('Windows 系统音频不可用，尝试 Qt 播放：'+str(mci_error),9000)
        # Qt Multimedia is also used as the fallback when MCI is unavailable.
        self._pending_seek_ratio=seek_ratio
        self._qt_audio_requested=True
        self.media.setSource(QUrl.fromLocalFile(str(wav)))
        self.media.play()
        self.statusBar().showMessage('正在启动 Qt 音频试听…',5000)
        # Some Qt multimedia installations silently stay in StoppedState
        # instead of emitting errorOccurred. Report that instead of a dead UI.
        QTimer.singleShot(1800, lambda token=rid: self._check_qt_audio_started(token))

    def _check_qt_audio_started(self,rid):
        if rid!=self._render_id or self._using_mci or not self._qt_audio_requested:return
        if self.media.playbackState()==QMediaPlayer.PlaybackState.PlayingState:return
        if self.media.duration()>0 and self.media.position()>=self.media.duration()-100:
            return  # Very short clip legitimately finished already.
        msg=self.media.errorString() or '音频驱动没有开始播放，请检查输出设备及 Qt Multimedia 安装。'
        self._playback_failure(msg)


    def stop(self):
        self._render_id+=1;self._seek_after_render=0.;self._pending_seek_ratio=0.
        self._set_rendering(False)
        self._close_mci()
        self._qt_audio_requested=False
        self.media.stop();self.scrubber.setValue(0)
        self.time_label.setText('00:00 / 00:00')
        self._set_play_button(False)

    def showEvent(self,event):
        super().showEvent(event)
        apply_native_chrome(self,self.theme,self.native_material)

    def next_tab(self):
        count=self.tabs.count()
        if count:self.tabs.setCurrentIndex((self.tabs.currentIndex()+1)%count)

    def show_help(self):
        from .qt_help import QtHelpDialog
        self._help_dialog=QtHelpDialog(self,language=self.language)
        self._help_dialog.setStyleSheet(stylesheet(self.theme))
        self._help_dialog.show()


def main(argv=None):
    app=QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setApplicationName('Melody Notation')
    app.setWindowIcon(line_icon('note',COLORS['light']['accent']))
    app.setOrganizationName('MelodyNotation')
    project=None
    args=list(sys.argv[1:] if argv is None else argv[1:])
    if args:
        candidate=Path(args[0]).expanduser()
        if candidate.is_dir():project=candidate
    window=MelodyMainWindow(project)
    window.show()
    return app.exec()


if __name__=='__main__':
    sys.exit(main())
