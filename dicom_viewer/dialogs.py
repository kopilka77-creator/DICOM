# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from .constants import TEXT_SIZE_CHOICES


class WindowLevelDialog(QtWidgets.QDialog):
    def __init__(self, wc, ww, viewport, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Window / Level")
        self.resize(440, 300)
        self.viewport = viewport
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        f = QtWidgets.QFormLayout(); f.setSpacing(10)
        self.wc_spin = QtWidgets.QDoubleSpinBox()
        self.wc_spin.setRange(-100000.0, 100000.0)
        self.wc_spin.setDecimals(2); self.wc_spin.setSingleStep(0.1)
        self.wc_spin.setValue(float(wc))
        self.ww_spin = QtWidgets.QDoubleSpinBox()
        self.ww_spin.setRange(0.01, 100000.0)
        self.ww_spin.setDecimals(2); self.ww_spin.setSingleStep(0.1)
        self.ww_spin.setValue(float(ww))
        self.wc_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wc_slider.setRange(-50000, 50000)
        self.wc_slider.setValue(int(float(wc) * 10))
        self.ww_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ww_slider.setRange(10, 50000)
        self.ww_slider.setValue(int(float(ww) * 10))
        f.addRow("WC (Level):", self.wc_spin); f.addRow(self.wc_slider)
        f.addRow("WW (Width):", self.ww_spin); f.addRow(self.ww_slider)
        v.addLayout(f)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        v.addWidget(btns)
        self._updating = False
        self.wc_spin.valueChanged.connect(self._on_wc_spin)
        self.ww_spin.valueChanged.connect(self._on_ww_spin)
        self.wc_slider.valueChanged.connect(self._on_wc_slider)
        self.ww_slider.valueChanged.connect(self._on_ww_slider)

    def _apply(self):
        if self._updating: return
        self.viewport.set_window_level(self.wc_spin.value(), self.ww_spin.value())

    def _on_wc_spin(self, v):
        self._updating = True
        try: self.wc_slider.setValue(int(v * 10))
        finally: self._updating = False
        self._apply()

    def _on_ww_spin(self, v):
        self._updating = True
        try: self.ww_slider.setValue(int(v * 10))
        finally: self._updating = False
        self._apply()

    def _on_wc_slider(self, v):
        if self._updating: return
        self._updating = True
        try: self.wc_spin.setValue(v / 10.0)
        finally: self._updating = False
        self._apply()

    def _on_ww_slider(self, v):
        if self._updating: return
        self._updating = True
        try: self.ww_spin.setValue(v / 10.0)
        finally: self._updating = False
        self._apply()


class TextAnnotationDialog(QtWidgets.QDialog):
    ACTION_OK = 1
    ACTION_DELETE = 2

    def __init__(self, parent=None, initial_text="", initial_mult=1.0,
                 allow_delete=False):
        super().__init__(parent)
        self._action = self.ACTION_OK
        self._is_edit = bool(initial_text) or allow_delete
        self.setWindowTitle("Редактировать текст"
                            if self._is_edit else "Добавить текст")
        self.resize(380, 200)
        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(16, 16, 16, 16)
        f = QtWidgets.QFormLayout(); f.setSpacing(10)
        self.text_edit = QtWidgets.QLineEdit(initial_text)
        self.size_combo = QtWidgets.QComboBox()
        for label, mult in TEXT_SIZE_CHOICES:
            self.size_combo.addItem(label, mult)
        best_idx, best_diff = 1, 999
        for i, (_lbl, m) in enumerate(TEXT_SIZE_CHOICES):
            d = abs(m - float(initial_mult))
            if d < best_diff:
                best_diff, best_idx = d, i
        self.size_combo.setCurrentIndex(best_idx)
        f.addRow("Текст:", self.text_edit)
        f.addRow("Размер:", self.size_combo)
        v.addLayout(f)
        h = QtWidgets.QHBoxLayout(); h.addStretch(1)
        if allow_delete:
            btn_del = QtWidgets.QPushButton("Удалить")
            btn_del.clicked.connect(self._do_delete); h.addWidget(btn_del)
        btn_cancel = QtWidgets.QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject); h.addWidget(btn_cancel)
        btn_ok = QtWidgets.QPushButton("OK"); btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept); h.addWidget(btn_ok)
        v.addLayout(h)
        self.text_edit.setFocus(); self.text_edit.selectAll()

    def _do_delete(self):
        self._action = self.ACTION_DELETE
        self.accept()

    def result_text(self):
        return (self.text_edit.text().strip(),
                float(self.size_combo.currentData()))

    def result_action(self):
        return self._action