# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from ..constants import CT_PRESETS, FONT_SCALES


class _UIMixin:
    def _build_toolbar(self):
        tb = QtWidgets.QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QtCore.QSize(18, 18))
        tb.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.addToolBar(QtCore.Qt.TopToolBarArea, tb)
        st = self.style()

        def add(text, slot, shortcut=None, tip=None, icon=None):
            if icon is not None:
                a = tb.addAction(icon, text, slot)
            else:
                a = tb.addAction(text, slot)
            if shortcut:
                a.setShortcut(shortcut)
            if tip:
                a.setToolTip(tip)
            return a

        add("Открыть", self._open_file, "Ctrl+O",
            "Открыть DICOM / ZIP",
            st.standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        add("Папка", self._open_folder, "Ctrl+Shift+O", "Открыть папку",
            st.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        tb.addSeparator()
        add("Печать", self._print_regular, "Ctrl+P", "Windows-принтер")
        add("Печать DICOM", self._print_dicom, "Ctrl+D",
            "DICOM-принтер")
        add("PDF", self._save_as_pdf, "Ctrl+Shift+P", "Сохранить в PDF",
            st.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        tb.addSeparator()
        for mode in (1, 2, 4):
            a = tb.addAction(str(mode))
            a.setToolTip("Раскладка: %d" % mode)
            a.triggered.connect(
                lambda checked=False, m=mode: self.panel._select(m))
        tb.addSeparator()
        add("+", self._zoom_in, "Ctrl+=", "Приблизить")
        add("Fit", self._zoom_fit, "Ctrl+0", "По размеру окна")
        add("-", self._zoom_out, "Ctrl+-", "Отдалить")
        add("1:1", self._zoom_1to1, "Ctrl+Shift+0", "Масштаб 1:1")
        tb.addSeparator()
        add("Auto W/L", self._auto_wl, "Ctrl+Shift+A",
            "Auto Window/Level")
        add("W/L", self._adjust_wl, "Ctrl+W", "Настроить Window/Level")
        add("Инверсия", self._invert, "Ctrl+I", "Инвертировать")
        tb.addSeparator()

        self._act_ruler_tb = QtWidgets.QAction("Линейка", self)
        self._act_ruler_tb.setCheckable(True)
        self._act_ruler_tb.toggled.connect(self._toggle_ruler_mode)
        tb.addAction(self._act_ruler_tb)

        self._act_calib_tb = QtWidgets.QAction("Калибровка", self)
        self._act_calib_tb.setCheckable(True)
        self._act_calib_tb.toggled.connect(self._toggle_calib_mode)
        tb.addAction(self._act_calib_tb)

        tb.addSeparator()
        self._act_text_tb = QtWidgets.QAction("Текст", self)
        self._act_text_tb.setCheckable(True)
        self._act_text_tb.setShortcut("Ctrl+T")
        self._act_text_tb.toggled.connect(self._toggle_text_mode)
        tb.addAction(self._act_text_tb)

    def _build_status_bar(self):
        sb = self.statusBar()
        self._wl_status = QtWidgets.QLabel("")
        self._wl_status.setStyleSheet(
            "color:#a0a0a0; padding:0 12px; border-left:1px solid #3c3c3c;")
        self._zoom_status = QtWidgets.QLabel("")
        self._zoom_status.setStyleSheet(
            "color:#a0a0a0; padding:0 12px; border-left:1px solid #3c3c3c;")
        self._cal_status = QtWidgets.QLabel("")
        self._cal_status.setStyleSheet(
            "color:#4aff9e; padding:0 12px; border-left:1px solid #3c3c3c;")
        sb.addPermanentWidget(self._wl_status)
        sb.addPermanentWidget(self._zoom_status)
        sb.addPermanentWidget(self._cal_status)

    def _update_status_info(self, vp=None):
        vp = vp or self.viewports.active_viewport
        try:
            if vp is not None and vp._series:
                wc, ww = vp._effective_wl()
                self._wl_status.setText("W: %.1f  L: %.1f" % (ww, wc))
                self._zoom_status.setText(
                    "Zoom: Fit" if vp._zoom <= 0
                    else "Zoom: %.0f%%" % (vp._zoom * 100))
                self._cal_status.setText(
                    ("Cal: %.4f мм/px" % vp.get_calibration())
                    if vp.has_calibration() else "Cal: —")
            else:
                self._wl_status.setText("")
                self._zoom_status.setText("")
                self._cal_status.setText("")
        except Exception:
            pass

    def _build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu("Файл")
        self._add_action(m, "Открыть файл / ZIP", self._open_file, "Ctrl+O")
        self._add_action(m, "Открыть папку", self._open_folder,
                         "Ctrl+Shift+O")
        m.addSeparator()
        self._add_action(m, "Печать (Windows)...", self._print_regular,
                         "Ctrl+P")
        self._add_action(m, "Печать на DICOM...", self._print_dicom,
                         "Ctrl+D")
        self._add_action(m, "Сохранить в PDF...", self._save_as_pdf,
                         "Ctrl+Shift+P")
        m.addSeparator()
        self._add_action(m, "Выход", self.close, "Ctrl+Q")

        m = mb.addMenu("Изображение")
        self._add_action(m, "Auto W/L", self._auto_wl, "Ctrl+Shift+A")
        self._add_action(m, "Настроить W/L", self._adjust_wl, "Ctrl+W")
        sub = m.addMenu("CT-пресеты")
        for name, wl in CT_PRESETS:
            a = QtWidgets.QAction(name, self)
            a.triggered.connect(
                lambda checked=False, wl=wl: self._apply_preset(wl))
            sub.addAction(a)
        m.addSeparator()
        self._add_action(m, "Инвертировать", self._invert, "Ctrl+I")
        self._add_action(m, "Сбросить вид", self._reset_view, "Ctrl+R")
        m.addSeparator()
        self._add_action(m, "Приблизить", self._zoom_in, "Ctrl+=")
        self._add_action(m, "Отдалить", self._zoom_out, "Ctrl+-")
        self._add_action(m, "По размеру окна", self._zoom_fit, "Ctrl+0")
        self._add_action(m, "Масштаб 1:1", self._zoom_1to1,
                         "Ctrl+Shift+0")

        m = mb.addMenu("Измерения")
        self._add_action(m, "Линейка",
                         lambda: self._act_ruler_tb.toggle())
        self._add_action(m, "Калибровка",
                         lambda: self._act_calib_tb.toggle())
        m.addSeparator()
        self._add_action(m, "Очистить измерения",
                         self._clear_measurements)

        m = mb.addMenu("Аннотации")
        self._act_text = QtWidgets.QAction("Режим текста", self)
        self._act_text.setCheckable(True)
        self._act_text.setShortcut("Ctrl+T")
        self._act_text.toggled.connect(self._toggle_text_mode)
        m.addAction(self._act_text)
        m.addSeparator()
        self._add_action(m, "Очистить тексты", self._clear_texts_all)

        m = mb.addMenu("Раскладка")
        self._add_action(m, "1 снимок",
                         lambda: self.panel._select(1), "Ctrl+1")
        self._add_action(m, "2 снимка",
                         lambda: self.panel._select(2), "Ctrl+2")
        self._add_action(m, "4 снимка",
                         lambda: self.panel._select(4), "Ctrl+4")

        m = mb.addMenu("Вид")
        act = QtWidgets.QAction("Показать теги DICOM", self)
        act.setCheckable(True)
        act.setChecked(False)
        act.toggled.connect(self._tags_dock.setVisible)
        m.addAction(act)
        act2 = QtWidgets.QAction("Показывать аннотации на изображении",
                                 self)
        act2.setCheckable(True)
        act2.setChecked(True)
        act2.toggled.connect(self._toggle_annotations)
        m.addAction(act2)
        m.addSeparator()
        sub = m.addMenu("Размер шрифта аннотаций")
        self._font_scale_actions = []
        for mult, label in FONT_SCALES:
            a = QtWidgets.QAction(label, self)
            a.setCheckable(True)
            a.triggered.connect(
                lambda checked=False, m=mult: self._set_font_scale(m))
            sub.addAction(a)
            self._font_scale_actions.append((mult, a))
        self._font_scale_actions[2][1].setChecked(True)

        m = mb.addMenu("Справка")
        self._add_action(m, "О программе", self._about)

    def _add_action(self, menu, text, slot, shortcut=None):
        a = QtWidgets.QAction(text, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)
        return a