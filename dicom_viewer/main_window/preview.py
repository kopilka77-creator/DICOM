# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui

from ..constants import FILM_SIZE_TO_INCHES


class _PreviewMixin:

    def _schedule_preview_refresh(self, delay=200):
        if self.tabs.currentIndex() != 1:
            return
        if not hasattr(self, "_preview_timer"):
            self._preview_timer = QtCore.QTimer(self)
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._refresh_preview)
        self._preview_timer.start(delay)

    def _make_header_pixmap(self, width, height, params):
        if height <= 0 or width <= 0:
            return None
        pix = QtGui.QPixmap(width, height)
        pix.fill(QtGui.QColor(255, 255, 255))
        p = QtGui.QPainter(pix)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            self._draw_sheet_header(p, QtCore.QRect(0, 0, width, height))
        finally:
            p.end()
        return pix

    def _make_footer_pixmap(self, width, height, params):
        if height <= 0 or width <= 0:
            return None
        pix = QtGui.QPixmap(width, height)
        pix.fill(QtGui.QColor(255, 255, 255))
        p = QtGui.QPainter(pix)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
            self._draw_sheet_footer(
                p, QtCore.QRect(0, 0, width, height), params)
        finally:
            p.end()
        return pix

    def _source_pixmaps_for_cells(self, params):
        out = []
        show_overlays = params.get("print_overlays", True)
        for vp in self.viewports.all_viewports:
            if vp is None or not vp._series:
                out.append(None)
                continue
            try:
                pix = vp.get_print_pixmap(include_info=show_overlays)
            except Exception:
                pix = None
            out.append(pix)
        return out

    def _current_layout_mode(self):
        for m, b in self.panel._layout_btns:
            if b.isChecked():
                return m
        return 1

    def _refresh_preview(self):
        canvas = getattr(self, "_preview_canvas", None)
        if canvas is None:
            return

        params = self.panel.collect()

        canvas.set_split_orientation(self._split_orientation)

        if not self._any_series():
            canvas.rebuild(
                self.viewports.all_viewports,
                self._current_layout_mode(),
                None, None, False, False, False, False)
            return

        film = params.get("film_size", "14x17")
        orientation = params.get("orientation", "PORTRAIT")
        short_in, long_in = FILM_SIZE_TO_INCHES.get(film, (14.0, 17.0))
        if orientation == "PORTRAIT":
            w_in, h_in = short_in, long_in
        else:
            w_in, h_in = long_in, short_in

        dpi = 110
        physical_w = max(100, int(w_in * dpi))
        physical_h = max(100, int(h_in * dpi))

        try:
            vp = self._preview_scroll.viewport()
            vw = max(200, vp.width() - 20)
            vh = max(200, vp.height() - 20)
        except Exception:
            vw, vh = 900, 1200

        scale = min(vw / float(physical_w), vh / float(physical_h))
        display_w = max(100, int(physical_w * scale))
        display_h = max(100, int(physical_h * scale))

        canvas.set_sheet_size(physical_w, physical_h)
        canvas.setFixedSize(display_w, display_h)

        header_h = int(display_h * 0.08)
        footer_h = int(display_h * 0.06)
        header_pix = None
        if params.get("print_tags", True):
            header_pix = self._make_header_pixmap(
                display_w, header_h, params)
        footer_pix = None
        if params.get("print_footer", True):
            footer_pix = self._make_footer_pixmap(
                display_w, footer_h, params)

        canvas.rebuild(
            self.viewports.all_viewports,
            self._current_layout_mode(),
            header_pix, footer_pix,
            params.get("print_tags", True),
            params.get("print_footer", True),
            params.get("no_border", False),
            self.panel.white_bg.isChecked())

        pixmaps = self._source_pixmaps_for_cells(params)
        canvas.set_source_pixmaps(pixmaps)

    def _pv_active_cell(self):
        return getattr(self, "_pv_active_cell_ref", None)

    def _on_pv_cell_clicked(self, cell):
        self._pv_active_cell_ref = cell

    def _pv_zoom_1to1(self):
        c = self._pv_active_cell()
        if c is not None:
            c._state["zoom"] = 1.0
            c._render()

    def _pv_reset_bc(self):
        c = self._pv_active_cell()
        if c is not None:
            c.reset_bc()

    def _pv_toggle_split_orientation(self):
        if self._split_orientation == QtCore.Qt.Horizontal:
            self._split_orientation = QtCore.Qt.Vertical
            self._pv_split_orient_btn.setText("↕")
            self._pv_split_orient_btn.setToolTip(
                "Разделитель: вертикальный (2 снимка сверху/снизу)")
        else:
            self._split_orientation = QtCore.Qt.Horizontal
            self._pv_split_orient_btn.setText("↔")
            self._pv_split_orient_btn.setToolTip(
                "Разделитель: горизонтальный (2 снимка слева/справа)")
        self._refresh_preview()

    def _on_white_bg_changed(self, checked):
        self._apply_preview_bg()
        self._schedule_preview_refresh(50)

    def _apply_preview_bg(self, *_):
        try:
            white = self.panel.white_bg.isChecked()
        except Exception:
            white = False
        bg = "#ffffff" if white else "#000000"
        if hasattr(self, "_preview_scroll"):
            self._preview_scroll.setStyleSheet(
                "QScrollArea { background:%s; border:none; }"
                "QScrollArea > QWidget > QWidget { background:%s; }"
                % (bg, bg))
            vp = self._preview_scroll.viewport()
            vp.setAutoFillBackground(True)
            pal = vp.palette()
            pal.setColor(QtGui.QPalette.Window, QtGui.QColor(bg))
            vp.setPalette(pal)