# -*- coding: utf-8 -*-
import os
import sys
from PyQt5 import QtCore, QtWidgets

from .constants import FILM_SIZES, ORIENTATIONS, FILM_TYPES


class PrintSettingsPanel(QtWidgets.QWidget):
    layout_changed = QtCore.pyqtSignal(int)
    settings_changed = QtCore.pyqtSignal()

    _K = {
        "ip": "printer/ip", "aet": "printer/aet", "port": "printer/port",
        "film_size": "printer/film_size", "orientation": "printer/orientation",
        "film_type": "printer/film_type",
        "tags": "printer/print_tags", "overlays": "printer/print_overlays",
        "footer": "printer/print_footer",
        "no_border": "print/no_border", "white_bg": "print/white_bg",
        "layout": "ui/layout_mode",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        inner = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(inner)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(12)

        # ── DICOM-принтер ──
        g = QtWidgets.QGroupBox("DICOM-принтер")
        f = QtWidgets.QFormLayout(g)
        f.setSpacing(8)
        f.setLabelAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.ip = QtWidgets.QLineEdit("127.0.0.1")
        self.aet = QtWidgets.QLineEdit("DICOM_PRINTER")
        self.port = QtWidgets.QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(104)
        self.film_size = QtWidgets.QComboBox()
        self.film_size.addItems(FILM_SIZES)
        self.orientation = QtWidgets.QComboBox()
        self.orientation.addItems(ORIENTATIONS)
        self.film_type = QtWidgets.QComboBox()
        self.film_type.addItems(FILM_TYPES)
        for lbl, w in [("IP:", self.ip), ("AET:", self.aet),
                       ("PORT:", self.port),
                       ("Размер пленки:", self.film_size),
                       ("Ориентация:", self.orientation),
                       ("Тип пленки:", self.film_type)]:
            f.addRow(lbl, w)
        v.addWidget(g)

        # ── Раскладка ──
        g2 = QtWidgets.QGroupBox("Раскладка")
        h = QtWidgets.QHBoxLayout(g2)
        h.setSpacing(6)
        self._layout_btns = []
        for mode in (1, 2, 4):
            b = QtWidgets.QPushButton(str(mode))
            b.setCheckable(True)
            b.setMinimumHeight(36)
            b.clicked.connect(lambda _, m=mode: self._select(m))
            h.addWidget(b)
            self._layout_btns.append((mode, b))
        self._layout_btns[0][1].setChecked(True)
        v.addWidget(g2)

        # ── Действия ──
        g3 = QtWidgets.QGroupBox("Действия")
        vv = QtWidgets.QVBoxLayout(g3)
        vv.setSpacing(8)
        self.open_btn = QtWidgets.QPushButton("Открыть файл / ZIP")
        self.open_folder_btn = QtWidgets.QPushButton("Открыть папку")
        self.test_btn = QtWidgets.QPushButton("Тест связи с DICOM-принтером")
        self.save_calib_btn = QtWidgets.QPushButton(
            "Записать калибровку в теги")
        self.print_btn = QtWidgets.QPushButton("Печать на DICOM")
        for w in (self.open_btn, self.open_folder_btn, self.test_btn,
                  self.save_calib_btn, self.print_btn):
            vv.addWidget(w)
        v.addWidget(g3)

        v.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)

        # ── скрытые "носители состояния" (управляются из тулбара предпросмотра) ──
        self.print_tags = QtWidgets.QCheckBox("Теги")
        self.print_tags.setChecked(True)
        self.print_overlays = QtWidgets.QCheckBox("Описание")
        self.print_overlays.setChecked(True)
        self.print_footer = QtWidgets.QCheckBox("Подвал")
        self.print_footer.setChecked(True)
        self.no_border = QtWidgets.QCheckBox("Без рамки")
        self.no_border.setChecked(False)
        self.white_bg = QtWidgets.QCheckBox("Белый фон")
        self.white_bg.setChecked(False)

        # ── сигналы ──
        for w in (self.film_size, self.orientation, self.film_type):
            w.currentTextChanged.connect(self.settings_changed.emit)
        self.ip.textChanged.connect(self.settings_changed.emit)
        self.aet.textChanged.connect(self.settings_changed.emit)
        self.port.valueChanged.connect(self.settings_changed.emit)

        self._load_settings()

    def _settings_path(self):
        try:
            base = os.path.dirname(os.path.abspath(sys.argv[0]))
        except Exception:
            base = os.path.expanduser("~")
        portable = os.path.join(base, "settings.ini")
        try:
            with open(portable, "a", encoding="utf-8"):
                pass
            return portable
        except Exception:
            pass
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(appdata, "DicomViewer")
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
        return os.path.join(folder, "settings.ini")

    def _qsettings(self):
        return QtCore.QSettings(self._settings_path(),
                                QtCore.QSettings.IniFormat)

    def _load_settings(self):
        try:
            s = self._qsettings()
            self.ip.setText(str(s.value(self._K["ip"], "127.0.0.1")))
            self.aet.setText(str(s.value(self._K["aet"], "DICOM_PRINTER")))
            try:
                port_val = int(s.value(self._K["port"], 104))
            except (TypeError, ValueError):
                port_val = 104
            if 1 <= port_val <= 65535:
                self.port.setValue(port_val)
            for key, cb in (("film_size", self.film_size),
                            ("orientation", self.orientation),
                            ("film_type", self.film_type)):
                val = str(s.value(self._K[key], ""))
                if val:
                    idx = cb.findText(val)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
            for key, widget, default in (
                    ("tags", self.print_tags, True),
                    ("overlays", self.print_overlays, True),
                    ("footer", self.print_footer, True),
                    ("no_border", self.no_border, False),
                    ("white_bg", self.white_bg, False)):
                try:
                    v = s.value(self._K[key], default)
                    if isinstance(v, str):
                        v = v.lower() in ("true", "1", "yes")
                    widget.setChecked(bool(v))
                except Exception:
                    pass
            try:
                lm = int(s.value(self._K["layout"], 1))
            except (TypeError, ValueError):
                lm = 1
            if lm in (1, 2, 4):
                for m, b in self._layout_btns:
                    b.setChecked(m == lm)
        except Exception:
            pass

    def save_settings(self):
        try:
            s = self._qsettings()
            s.setValue(self._K["ip"], self.ip.text().strip() or "127.0.0.1")
            s.setValue(self._K["aet"],
                       self.aet.text().strip() or "DICOM_PRINTER")
            s.setValue(self._K["port"], int(self.port.value()))
            s.setValue(self._K["film_size"], self.film_size.currentText())
            s.setValue(self._K["orientation"], self.orientation.currentText())
            s.setValue(self._K["film_type"], self.film_type.currentText())
            s.setValue(self._K["tags"], bool(self.print_tags.isChecked()))
            s.setValue(self._K["overlays"],
                       bool(self.print_overlays.isChecked()))
            s.setValue(self._K["footer"], bool(self.print_footer.isChecked()))
            s.setValue(self._K["no_border"], bool(self.no_border.isChecked()))
            s.setValue(self._K["white_bg"], bool(self.white_bg.isChecked()))
            mode = 1
            for m, b in self._layout_btns:
                if b.isChecked():
                    mode = m
                    break
            s.setValue(self._K["layout"], int(mode))
            s.sync()
        except Exception:
            pass

    def _select(self, mode):
        for m, b in self._layout_btns:
            b.setChecked(m == mode)
        self.layout_changed.emit(mode)
        self.settings_changed.emit()

    def collect(self):
        return {"ip": self.ip.text().strip(),
                "aet": self.aet.text().strip(),
                "port": self.port.value(),
                "film_size": self.film_size.currentText(),
                "orientation": self.orientation.currentText(),
                "film_type": self.film_type.currentText(),
                "print_tags": self.print_tags.isChecked(),
                "print_overlays": self.print_overlays.isChecked(),
                "print_footer": self.print_footer.isChecked(),
                "no_border": self.no_border.isChecked()}