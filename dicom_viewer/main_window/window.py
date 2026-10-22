# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from ..constants import FILM_SIZES, ORIENTATIONS, FILM_TYPES
from ..settings_panel import PrintSettingsPanel
from ..viewport_layout import ViewportLayoutManager
from ..pacs import PacsTab
from ..dicom_io import _tags_for_dataset
from .ui import _UIMixin
from .actions import _ActionsMixin
from .preview import _PreviewMixin
from .printing import _PrintingMixin
from .preview_canvas import PreviewCanvas


class MainWindow(_UIMixin, _ActionsMixin, _PreviewMixin, _PrintingMixin,
                 QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICOM Viewer")
        self.resize(1400, 900)

        self._split_orientation = QtCore.Qt.Horizontal

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        viewer_page = QtWidgets.QWidget()
        viewer_layout = QtWidgets.QHBoxLayout(viewer_page)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)
        self.panel = PrintSettingsPanel()
        self.viewports = ViewportLayoutManager()
        viewer_layout.addWidget(self.panel, 0)
        viewer_layout.addWidget(self.viewports, 1)
        self.tabs.addTab(viewer_page, "Просмотр")

        self._build_preview_tab()
        self._build_pacs_tab()
        self._connect_panel_signals()
        self._connect_viewport_signals()
        self._build_tags_dock()

        self._build_toolbar()
        self._build_menu()
        self._build_status_bar()

        try:
            saved_mode = 1
            for m, b in self.panel._layout_btns:
                if b.isChecked():
                    saved_mode = m
                    break
            self.viewports.set_layout_mode(saved_mode)
        except Exception:
            pass

        self.statusBar().showMessage("Готов")

    def _build_preview_tab(self):
        self._preview_page = QtWidgets.QWidget()
        pv = QtWidgets.QVBoxLayout(self._preview_page)
        pv.setContentsMargins(6, 6, 6, 6)
        pv.setSpacing(6)

        tb1 = QtWidgets.QHBoxLayout()
        tb1.setSpacing(6)

        tb1.addWidget(QtWidgets.QLabel("Плёнка:"))
        self._pv_film = QtWidgets.QComboBox()
        self._pv_film.addItems(FILM_SIZES)
        tb1.addWidget(self._pv_film)

        tb1.addWidget(QtWidgets.QLabel("Ориент.:"))
        self._pv_orient = QtWidgets.QComboBox()
        self._pv_orient.addItems(ORIENTATIONS)
        tb1.addWidget(self._pv_orient)

        tb1.addWidget(QtWidgets.QLabel("Тип:"))
        self._pv_type = QtWidgets.QComboBox()
        self._pv_type.addItems(FILM_TYPES)
        tb1.addWidget(self._pv_type)

        self._pv_tags = QtWidgets.QCheckBox("Теги")
        self._pv_tags.setChecked(True)
        self._pv_overlays = QtWidgets.QCheckBox("Описание")
        self._pv_overlays.setChecked(True)
        self._pv_footer = QtWidgets.QCheckBox("Подвал")
        self._pv_footer.setChecked(True)
        self._pv_noborder = QtWidgets.QCheckBox("Без рамки")
        self._pv_whitebg = QtWidgets.QCheckBox("Белый фон")
        for w in (self._pv_tags, self._pv_overlays, self._pv_footer,
                  self._pv_noborder, self._pv_whitebg):
            tb1.addWidget(w)
        tb1.addStretch(1)
        pv.addLayout(tb1)

        tb2 = QtWidgets.QHBoxLayout()
        tb2.setSpacing(6)

        self._pv_split_orient_btn = QtWidgets.QPushButton("↔")
        self._pv_split_orient_btn.setFixedWidth(40)
        self._pv_split_orient_btn.setToolTip(
            "Разделитель: горизонтальный (2 снимка слева/справа)")
        tb2.addWidget(self._pv_split_orient_btn)

        self._pv_zoom_1to1_btn = QtWidgets.QPushButton("1:1")
        self._pv_zoom_1to1_btn.setFixedWidth(50)
        tb2.addWidget(self._pv_zoom_1to1_btn)

        self._pv_bc_reset = QtWidgets.QPushButton("Сброс B/C")
        tb2.addWidget(self._pv_bc_reset)

        tb2.addStretch(1)

        self._pv_refresh_btn = QtWidgets.QPushButton("Обновить")
        self._pv_print_btn = QtWidgets.QPushButton("Печать")
        self._pv_dicom_btn = QtWidgets.QPushButton("Печать DICOM")
        self._pv_pdf_btn = QtWidgets.QPushButton("PDF")
        for w in (self._pv_refresh_btn, self._pv_print_btn,
                  self._pv_dicom_btn, self._pv_pdf_btn):
            tb2.addWidget(w)
        pv.addLayout(tb2)

        self._preview_scroll = QtWidgets.QScrollArea()
        self._preview_scroll.setWidgetResizable(True)
        self._preview_scroll.setAlignment(QtCore.Qt.AlignCenter)
        self._preview_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._preview_canvas = PreviewCanvas()
        self._preview_canvas.cell_clicked.connect(self._on_pv_cell_clicked)
        self._preview_scroll.setWidget(self._preview_canvas)
        pv.addWidget(self._preview_scroll, 1)
        self.tabs.addTab(self._preview_page, "Предпросмотр печати")

        self._pv_active_cell_ref = None

        self._sync_preview_widgets()
        self._apply_preview_bg()

        self._pv_film.currentTextChanged.connect(
            lambda t: self.panel.film_size.setCurrentText(t))
        self._pv_orient.currentTextChanged.connect(
            lambda t: self.panel.orientation.setCurrentText(t))
        self._pv_type.currentTextChanged.connect(
            lambda t: self.panel.film_type.setCurrentText(t))
        self.panel.film_size.currentTextChanged.connect(
            lambda t: self._set_pv(self._pv_film, t))
        self.panel.orientation.currentTextChanged.connect(
            lambda t: self._set_pv(self._pv_orient, t))
        self.panel.film_type.currentTextChanged.connect(
            lambda t: self._set_pv(self._pv_type, t))

        self._pv_tags.toggled.connect(self.panel.print_tags.setChecked)
        self.panel.print_tags.toggled.connect(
            lambda v: self._set_chk(self._pv_tags, v))
        self.panel.print_tags.toggled.connect(
            lambda v: self._schedule_preview_refresh(100))

        self._pv_overlays.toggled.connect(
            self.panel.print_overlays.setChecked)
        self.panel.print_overlays.toggled.connect(
            lambda v: self._set_chk(self._pv_overlays, v))
        self.panel.print_overlays.toggled.connect(
            lambda v: self._schedule_preview_refresh(100))

        self._pv_footer.toggled.connect(self.panel.print_footer.setChecked)
        self.panel.print_footer.toggled.connect(
            lambda v: self._set_chk(self._pv_footer, v))
        self.panel.print_footer.toggled.connect(
            lambda v: self._schedule_preview_refresh(100))

        self._pv_noborder.toggled.connect(self.panel.no_border.setChecked)
        self.panel.no_border.toggled.connect(
            lambda v: self._set_chk(self._pv_noborder, v))
        self.panel.no_border.toggled.connect(
            lambda v: self._schedule_preview_refresh(100))

        self._pv_whitebg.toggled.connect(self.panel.white_bg.setChecked)
        self.panel.white_bg.toggled.connect(
            lambda v: self._set_chk(self._pv_whitebg, v))
        self.panel.white_bg.toggled.connect(self._on_white_bg_changed)

        self._pv_split_orient_btn.clicked.connect(
            self._pv_toggle_split_orientation)
        self._pv_zoom_1to1_btn.clicked.connect(self._pv_zoom_1to1)
        self._pv_bc_reset.clicked.connect(self._pv_reset_bc)
        self._pv_refresh_btn.clicked.connect(self._refresh_preview)
        self._pv_print_btn.clicked.connect(self._print_regular)
        self._pv_dicom_btn.clicked.connect(self._print_dicom)
        self._pv_pdf_btn.clicked.connect(self._save_as_pdf)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ─── остальные методы без изменений ───
    def _build_pacs_tab(self):
        self.pacs_tab = PacsTab()
        self.pacs_tab.load_requested.connect(self._load_pacs_files)
        self.tabs.addTab(self.pacs_tab, "PACS (загрузка)")

    def _connect_panel_signals(self):
        self.panel.layout_changed.connect(self._on_layout_changed)
        self.panel.settings_changed.connect(self._on_settings_changed)
        self.panel.open_btn.clicked.connect(self._open_file)
        self.panel.open_folder_btn.clicked.connect(self._open_folder)
        self.panel.print_btn.clicked.connect(self._print_dicom)
        self.panel.test_btn.clicked.connect(self._test_dicom_connection)
        self.panel.save_calib_btn.clicked.connect(
            self._save_calibration_to_tags)

    def _connect_viewport_signals(self):
        for vp in self.viewports.all_viewports:
            vp.clicked.connect(self._on_vp_clicked_refresh_tags)
            vp.frame_changed.connect(self._on_frame_changed_refresh_tags)
            vp.text_mode_changed.connect(self._on_text_mode_changed)
            vp.measure_status.connect(
                lambda s: self.statusBar().showMessage(s, 8000))
            vp.measure_mode_changed.connect(self._on_measure_mode_changed)
            vp.annot_changed.connect(self._on_annot_changed)

    def _build_tags_dock(self):
        self._tags_dock = QtWidgets.QDockWidget("Теги DICOM", self)
        self._tags_tree = QtWidgets.QTreeWidget()
        self._tags_tree.setColumnCount(4)
        self._tags_tree.setHeaderLabels(
            ["Tag", "Название", "VR", "Значение"])
        self._tags_tree.setAlternatingRowColors(True)
        self._tags_tree.setRootIsDecorated(False)
        self._tags_tree.setMinimumWidth(350)
        header = self._tags_tree.header()
        header.setStretchLastSection(True)
        try:
            header.setSectionResizeMode(
                0, QtWidgets.QHeaderView.Interactive)
            header.setSectionResizeMode(
                1, QtWidgets.QHeaderView.Interactive)
            header.setSectionResizeMode(
                2, QtWidgets.QHeaderView.Interactive)
            header.setSectionResizeMode(
                3, QtWidgets.QHeaderView.Stretch)
        except AttributeError:
            pass
        self._tags_dock.setWidget(self._tags_tree)
        self._tags_dock.setMinimumWidth(300)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._tags_dock)
        self.resizeDocks([self._tags_dock], [420], QtCore.Qt.Horizontal)
        self._tags_dock.setVisible(False)

    def _set_pv(self, widget, val):
        widget.blockSignals(True)
        widget.setCurrentText(val)
        widget.blockSignals(False)

    def _set_chk(self, widget, val):
        widget.blockSignals(True)
        widget.setChecked(bool(val))
        widget.blockSignals(False)

    def _sync_preview_widgets(self):
        try:
            for cb, panel_cb in (
                    (self._pv_film, self.panel.film_size),
                    (self._pv_orient, self.panel.orientation),
                    (self._pv_type, self.panel.film_type)):
                cb.blockSignals(True)
                cb.setCurrentText(panel_cb.currentText())
                cb.blockSignals(False)
            for cb, panel_cb in (
                    (self._pv_tags, self.panel.print_tags),
                    (self._pv_overlays, self.panel.print_overlays),
                    (self._pv_footer, self.panel.print_footer),
                    (self._pv_noborder, self.panel.no_border),
                    (self._pv_whitebg, self.panel.white_bg)):
                cb.blockSignals(True)
                cb.setChecked(panel_cb.isChecked())
                cb.blockSignals(False)
        except Exception:
            pass

    def _on_annot_changed(self):
        self._schedule_preview_refresh(200)

    def _on_tab_changed(self, idx):
        if idx == 1:
            self._refresh_preview()

    def _on_settings_changed(self):
        self._schedule_preview_refresh(200)

    def _on_layout_changed(self, mode):
        self.viewports.set_layout_mode(mode)
        self._refresh_tags()
        self._update_status_info()
        self._schedule_preview_refresh(200)

    def _on_vp_clicked_refresh_tags(self, vp):
        self.viewports._set_active_vp(vp)
        if self._act_text.isChecked() != vp.is_text_mode():
            self._act_text.blockSignals(True)
            self._act_text.setChecked(vp.is_text_mode())
            self._act_text.blockSignals(False)
        if hasattr(self, "_act_text_tb"):
            self._act_text_tb.blockSignals(True)
            self._act_text_tb.setChecked(vp.is_text_mode())
            self._act_text_tb.blockSignals(False)
        mm = vp.get_measure_mode()
        self._act_ruler_tb.blockSignals(True)
        self._act_ruler_tb.setChecked(mm == "ruler")
        self._act_ruler_tb.blockSignals(False)
        self._act_calib_tb.blockSignals(True)
        self._act_calib_tb.setChecked(mm == "calibrate")
        self._act_calib_tb.blockSignals(False)
        if self._tags_dock.isVisible():
            self._refresh_tags(vp)
        self._update_status_info(vp)

    def _on_frame_changed_refresh_tags(self, vp):
        if self.viewports.active_viewport is None:
            self.viewports._set_active_vp(vp)
        if (vp is self.viewports.active_viewport
                and self._tags_dock.isVisible()):
            self._refresh_tags(vp)
        if vp is self.viewports.active_viewport:
            self._update_status_info(vp)
        self._schedule_preview_refresh(200)

    def _on_text_mode_changed(self, vp, on):
        if vp is self._active_vp():
            self._act_text.blockSignals(True)
            self._act_text.setChecked(on)
            self._act_text.blockSignals(False)
            if hasattr(self, "_act_text_tb"):
                self._act_text_tb.blockSignals(True)
                self._act_text_tb.setChecked(on)
                self._act_text_tb.blockSignals(False)

    def _on_measure_mode_changed(self, vp, mode):
        if vp is self._active_vp():
            self._act_ruler_tb.blockSignals(True)
            self._act_ruler_tb.setChecked(mode == "ruler")
            self._act_ruler_tb.blockSignals(False)
            self._act_calib_tb.blockSignals(True)
            self._act_calib_tb.setChecked(mode == "calibrate")
            self._act_calib_tb.blockSignals(False)

    def _refresh_tags(self, vp=None):
        if not self._tags_dock.isVisible():
            return
        vp = vp or self.viewports.active_viewport
        if vp is None or not vp._series:
            for v in self.viewports.all_viewports:
                if v.isVisible() and v._series:
                    vp = v
                    break
        if vp is None or not vp._series:
            self._tags_tree.clear()
            return
        ds, _ = vp._series[vp._index]
        self._tags_tree.clear()
        for tag_str, name, vr, val in _tags_for_dataset(ds):
            QtWidgets.QTreeWidgetItem(
                self._tags_tree, [tag_str, name, vr, val])
        for i in (0, 1, 2):
            self._tags_tree.resizeColumnToContents(i)
        self.statusBar().showMessage(
            "Теги: %d элементов" % self._tags_tree.topLevelItemCount())

    def _active_vp(self):
        vp = self.viewports.active_viewport
        if vp is not None and vp.isVisible():
            return vp
        for v in self.viewports.all_viewports:
            if v.isVisible():
                return v
        return None

    def _any_series(self):
        for vp in self.viewports.all_viewports:
            if vp._series:
                return True
        return False

    def _load_pacs_files(self, files):
        if not files:
            return
        loaded = 0
        vps = self.viewports.all_viewports
        for i, path in enumerate(files):
            if i >= len(vps):
                break
            try:
                vps[i].load_path(path)
                loaded += 1
            except Exception as ex:
                self.statusBar().showMessage(
                    "Ошибка загрузки %s: %s" % (path, ex))
        self.statusBar().showMessage(
            "Загружено с PACS: %d файлов" % loaded)
        self._schedule_preview_refresh(200)

    def closeEvent(self, event):
        try:
            self.panel.save_settings()
        except Exception:
            pass
        super().closeEvent(event)