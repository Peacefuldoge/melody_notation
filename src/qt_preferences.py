"""Single preferences window for theme, UI language and default output folder."""
from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLabel, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
    QFrame, QWidget)
from .qt_design import COLORS, THEME_NAMES, stylesheet, apply_native_chrome


class PreferencesDialog(QDialog):
    def __init__(self, parent, theme='light', language='zh', directory='', native_material=True):
        super().__init__(parent)
        self.setObjectName('PreferencesDialog')
        self.setWindowTitle('设置' if language=='zh' else 'Settings')
        self.setMinimumWidth(490)
        self.setModal(True)
        self.setStyleSheet(stylesheet(theme))
        lay=QVBoxLayout(self);lay.setContentsMargins(24,22,24,20);lay.setSpacing(17)
        title=QLabel('外观与偏好设置' if language=='zh' else 'Appearance & preferences')
        title.setObjectName('Header');lay.addWidget(title)
        hint=QLabel('设置会保存到当前用户，重启后仍然生效。' if language=='zh' else
                    'Preferences are saved for your Windows user.')
        hint.setObjectName('Muted');lay.addWidget(hint)
        form=QFormLayout();form.setSpacing(12);form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.theme_select=QComboBox()
        for key,(zh,en) in THEME_NAMES.items():
            self.theme_select.addItem(zh if language=='zh' else en,key)
        self.theme_select.setCurrentIndex(self.theme_select.findData(theme))
        form.addRow('主题' if language=='zh' else 'Theme',self.theme_select)
        self.language_select=QComboBox()
        self.language_select.addItem('简体中文','zh');self.language_select.addItem('English','en')
        self.language_select.setCurrentIndex(self.language_select.findData(language))
        form.addRow('语言' if language=='zh' else 'Language',self.language_select)
        self.material_select=QComboBox()
        self.material_select.addItem('自动（系统支持时使用毛玻璃）' if language=='zh' else
                                     'Automatic (native when available)',True)
        self.material_select.addItem('关闭系统毛玻璃' if language=='zh' else 'Disable native material',False)
        self.material_select.setCurrentIndex(self.material_select.findData(bool(native_material)))
        form.addRow('窗口特效' if language=='zh' else 'Window material',self.material_select)
        lay.addLayout(form)
        label=QLabel('默认保存目录' if language=='zh' else 'Default save directory');lay.addWidget(label)
        directory_row=QHBoxLayout();directory_row.setSpacing(7)
        self.folder=QLineEdit(str(directory or ''))
        self.folder.setPlaceholderText('跟随软件默认目录' if language=='zh' else 'Use application default')
        directory_row.addWidget(self.folder,1)
        browse=QPushButton('浏览…' if language=='zh' else 'Browse…')
        browse.clicked.connect(self._browse);directory_row.addWidget(browse)
        reset=QPushButton('恢复默认' if language=='zh' else 'Reset')
        reset.clicked.connect(self.folder.clear);directory_row.addWidget(reset)
        lay.addLayout(directory_row)
        lay.addSpacing(4)
        self.preview=QFrame();self.preview.setFixedHeight(44)
        self.preview.setObjectName('ThemePreview')
        lay.addWidget(self.preview)
        self.theme_select.currentIndexChanged.connect(self._preview)
        self._preview()
        footer=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        footer.button(QDialogButtonBox.StandardButton.Ok).setText('保存设置' if language=='zh' else 'Save settings')
        footer.button(QDialogButtonBox.StandardButton.Cancel).setText('取消' if language=='zh' else 'Cancel')
        footer.accepted.connect(self._confirm);footer.rejected.connect(self.reject)
        lay.addWidget(footer)
        apply_native_chrome(self,theme,enabled=native_material)

    def _preview(self):
        c=COLORS[self.theme_select.currentData()]
        self.preview.setStyleSheet(f'QFrame#ThemePreview {{background: {c["paper"]};'
            f'border: 2px solid {c["accent"]}; border-radius: 10px;}}')

    def _browse(self):
        start=self.folder.text().strip()
        if not start or not Path(start).is_dir():start=str(Path.home())
        folder=QFileDialog.getExistingDirectory(self,'请选择目录',start)
        if folder:self.folder.setText(folder)

    def _confirm(self):
        folder=self.folder.text().strip()
        if folder and not Path(folder).expanduser().is_dir():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self,'Invalid directory','Directory does not exist: '+folder)
            return
        self.accept()

    def values(self):
        folder=self.folder.text().strip()
        return {
            'theme':self.theme_select.currentData(),
            'language':self.language_select.currentData(),
            'default_save_directory':str(Path(folder).expanduser().resolve()) if folder else '',
            'native_material':self.material_select.currentData(),
        }
