# -*- coding: utf-8 -*-
import os
from PyQt5 import QtCore, QtGui, QtWidgets

from ..constants import DICOM_MIME, DECOMPRESS_HINT
from ..dicom_io import (read_dicom_path, read_dicom_folder,
                        _is_decompress_error)

_DRAG_SOURCE = None
_SWAP_SOURCE = None


class _EventsMixin:
    def eventFilter(self, obj, event):
        if obj is self.scroll.viewport():
            et = event.type()
            if et in (QtCore.QEvent.MouseButtonPress,
                      QtCore.QEvent.MouseButtonDblClick):
                self.clicked.emit(self)
                if et == QtCore.QEvent.MouseButtonPress:
                    self.setFocus()
                return True
        return super().eventFilter(obj, event)

    def set_active(self, active):
        active = bool(active)
        if active == self._active:
            return
        self._active = active
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        try:
            r = self.rect().adjusted(1, 1, -1, -1)
            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(r), 8, 8)
            p.fillPath(path, QtGui.QColor("#141414"))
            if self._active:
                p.setPen(QtGui.QPen(QtGui.QColor("#4a9eff"), 2))
            else:
                p.setPen(QtGui.QPen(QtGui.QColor("#2d2d30"), 1))
            p.drawPath(path)
        finally:
            p.end()

    def _on_canvas_press(self, e):
        try:
            self.clicked.emit(self)
            self.setFocus()
            if not self._series:
                return
            if self._measure_mode:
                if self._handle_measure_click(e.pos(), e.button()):
                    return
            if not self._measure_mode and not self._text_mode:
                native = self._canvas_to_native(e.pos())
                if native is not None:
                    hit = self._hit_test_measure(native)
                    if (hit is not None
                            and e.button() == QtCore.Qt.LeftButton):
                        self._start_measure_drag(hit, e)
                        return
                    if (hit is not None
                            and e.button() == QtCore.Qt.RightButton):
                        m, _p = hit
                        self._measure_context_menu(m, e.globalPos())
                        return
            if (e.button() == QtCore.Qt.LeftButton
                    and (e.modifiers() & QtCore.Qt.ControlModifier)):
                global _SWAP_SOURCE
                _SWAP_SOURCE = self
                self._drag_mode = "move"
                self._drag_start_global = e.globalPos()
                self.image_label.setCursor(QtCore.Qt.ClosedHandCursor)
                return
            if self._text_mode and e.button() == QtCore.Qt.LeftButton:
                self._handle_text_click(e)
                return
            if (e.button() == QtCore.Qt.RightButton
                    and not self._text_mode):
                hit = self._hit_test_text(e.pos())
                if hit is not None:
                    self._show_text_context_menu(hit, e.globalPos())
                    return
            self._drag_mode = None
            self._drag_start_global = e.globalPos()
            if e.button() == QtCore.Qt.LeftButton:
                hit = self._hit_test_text(e.pos())
                if hit is not None:
                    self._start_text_drag(hit, e)
                    return
                self._drag_mode = "wl"
                self._drag_wl = self._effective_wl()
                self.image_label.setCursor(QtCore.Qt.SizeAllCursor)
            elif e.button() in (QtCore.Qt.RightButton,
                                 QtCore.Qt.MiddleButton):
                self._drag_mode = "pan"
                self._drag_scroll = (
                    self.scroll.horizontalScrollBar().value(),
                    self.scroll.verticalScrollBar().value())
                self.image_label.setCursor(QtCore.Qt.ClosedHandCursor)
        except Exception:
            self._drag_mode = None

    def _on_canvas_move(self, e):
        if self._drag_mode is None:
            try:
                if self._measure_mode:
                    self.image_label.setCursor(QtCore.Qt.CrossCursor)
                    return
                if self._text_mode:
                    self.image_label.setCursor(QtCore.Qt.IBeamCursor)
                    return
                native = self._canvas_to_native(e.pos())
                if (native and
                        self._hit_test_measure(native) is not None):
                    self.image_label.setCursor(QtCore.Qt.OpenHandCursor)
                    return
                if (self._series
                        and self._hit_test_text(e.pos()) is not None):
                    self.image_label.setCursor(QtCore.Qt.OpenHandCursor)
                else:
                    self.image_label.setCursor(QtCore.Qt.ArrowCursor)
            except Exception:
                pass
            return
        if self._drag_mode == "measure":
            self._drag_measure_move(e)
            return
        if self._drag_mode == "text":
            self._drag_text_move(e)
            return
        if self._drag_mode == "move":
            try:
                w = QtWidgets.QApplication.widgetAt(e.globalPos())
                target = self._find_viewport_parent(w)
                if target is not None and target is not self:
                    if not target._active:
                        target._active = True
                        target.update()
                else:
                    if not self._active:
                        self._active = True
                        self.update()
            except Exception:
                pass
            return
        try:
            d = e.globalPos() - self._drag_start_global
            if self._drag_mode == "wl":
                wc0, ww0 = self._drag_wl
                k = self._WL_SENSITIVITY_PX
                new_ww = max(0.01, ww0 * (1.0 + d.x() / k))
                new_wc = wc0 + d.y() * (ww0 / k)
                self.set_window_level(new_wc, new_ww)
            elif self._drag_mode == "pan":
                hbar = self.scroll.horizontalScrollBar()
                vbar = self.scroll.verticalScrollBar()
                sx, sy = self._drag_scroll
                hbar.setValue(sx - d.x())
                vbar.setValue(sy - d.y())
        except Exception:
            self._drag_mode = None

    def _on_canvas_release(self, e):
        if self._drag_mode == "measure":
            self._drag_measure = None
            self._drag_part = None
            self._drag_orig = None
        if self._drag_mode == "move":
            global _SWAP_SOURCE
            try:
                w = QtWidgets.QApplication.widgetAt(e.globalPos())
                target = self._find_viewport_parent(w)
                if (target is not None and target is not self
                        and _SWAP_SOURCE is self):
                    target._transfer_from(self)
                    target.clicked.emit(target)
            except Exception:
                pass
            _SWAP_SOURCE = None
        self._drag_mode = None
        self._text_drag_idx = None
        try:
            if self._measure_mode:
                self.image_label.setCursor(QtCore.Qt.CrossCursor)
            elif self._text_mode:
                self.image_label.setCursor(QtCore.Qt.IBeamCursor)
            else:
                self.image_label.setCursor(QtCore.Qt.ArrowCursor)
        except Exception:
            self.image_label.setCursor(QtCore.Qt.ArrowCursor)

    def _on_canvas_double(self, e):
        if self._measure_mode:
            return
        if not self._series or self._text_mode:
            return
        native = self._canvas_to_native(e.pos())
        if native is not None:
            hit = self._hit_test_measure(native)
            if hit is not None:
                m, part = hit
                if part == "label" and m.is_calibration:
                    self._edit_calibration_value(m)
                    return
        hit = self._hit_test_text(e.pos())
        if hit is not None:
            self._edit_text(*hit)
            return
        self.reset_view()

    def _on_canvas_wheel(self, e):
        try:
            if not self._series:
                return
            dy = e.angleDelta().y()
            if dy == 0:
                return
            if e.modifiers() & QtCore.Qt.ShiftModifier:
                if len(self._series) > 1:
                    self._set_index(
                        self._index + (1 if dy < 0 else -1))
                return
            if dy > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        except Exception:
            pass

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            if self._measure_mode:
                self.set_measure_mode(None)
                return
            if self._text_mode:
                self.set_text_mode(False)
                return
            if self._drag_mode == "move":
                global _SWAP_SOURCE
                _SWAP_SOURCE = None
                self._drag_mode = None
                self.image_label.setCursor(QtCore.Qt.ArrowCursor)
                return
        if len(self._series) > 1:
            if e.key() in (QtCore.Qt.Key_Right, QtCore.Qt.Key_Down):
                self._set_index(self._index + 1)
                return
            if e.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Up):
                self._set_index(self._index - 1)
                return
        super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasFormat(DICOM_MIME) or md.hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        md = e.mimeData()
        if md.hasFormat(DICOM_MIME) or md.hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        self.clicked.emit(self)
        if md.hasFormat(DICOM_MIME):
            src = _DRAG_SOURCE
            if src is not None and src is not self:
                try:
                    self._transfer_from(src)
                except Exception as ex:
                    QtWidgets.QMessageBox.warning(
                        self, "Ошибка переноса", str(ex))
            e.acceptProposedAction()
            return
        urls = md.urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if os.path.isdir(path):
            self.load_folder(path)
        else:
            self.load_path(path)

    def _get_state(self):
        return {
            "series": list(self._series),
            "index": self._index,
            "wl": self._wl_override,
            "invert": self._invert,
            "texts": {k: list(v)
                      for k, v in self._text_annots.items()},
            "measures": {k: list(v)
                         for k, v in self._measurements.items()},
            "cal": self._calibration_mm_per_px,
            "brightness": self._brightness,
            "contrast": self._contrast,
        }

    def _set_state(self, st):
        series = st.get("series", []) or []
        self._series = list(series)
        if not self._series:
            self._index = 0
            self._wl_override = None
            self._invert = False
            self._text_annots = {}
            self._measurements = {}
            self._calibration_mm_per_px = None
            self._brightness = 0.0
            self._contrast = 1.0
            self._src_pixmap = None
            self._img_bytes = None
            self._annot_cache = None
            self.image_label.clear()
            self.image_label.setText(
                "Перетащите DICOM, ZIP\nили папку сюда")
            self.slider.setVisible(False)
            self.frame_info.setVisible(False)
            self.frame_changed.emit(self)
            return
        idx = st.get("index", 0)
        self._index = max(0, min(idx, len(self._series) - 1))
        self._wl_override = st.get("wl")
        self._invert = bool(st.get("invert", False))
        self._text_annots = {k: list(v)
                             for k, v in st.get("texts", {}).items()}
        self._measurements = {k: list(v)
                              for k, v in st.get("measures", {}).items()}
        self._calibration_mm_per_px = st.get("cal")
        self._brightness = float(st.get("brightness", 0.0))
        self._contrast = float(st.get("contrast", 1.0))
        self._invalidate_annot_cache()
        multi = len(self._series) > 1
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, len(self._series) - 1))
        self.slider.setValue(self._index)
        self.slider.blockSignals(False)
        self.slider.setVisible(multi)
        self.frame_info.setVisible(multi)
        self._render_current()
        self.frame_changed.emit(self)

    def _transfer_from(self, src):
        if src is self:
            return
        if not src._series and not self._series:
            return
        src_state = src._get_state()
        dst_state = self._get_state()
        self._set_state(src_state)
        src._set_state(dst_state)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_scaled()

    def _show_load_error(self, path, ex):
        if _is_decompress_error(ex):
            QtWidgets.QMessageBox.warning(
                self, "Сжатые пиксельные данные", DECOMPRESS_HINT)
        else:
            QtWidgets.QMessageBox.warning(
                self, "Ошибка",
                "Не удалось открыть:\n%s\n\n%s" % (path, ex))

    def load_path(self, path):
        try:
            ds, arr = read_dicom_path(path)
            try:
                nf = int(str(getattr(ds, "NumberOfFrames", 1)) or 1)
            except Exception:
                nf = 1
            if nf > 1 and arr.ndim >= 3:
                frames = [(ds, arr[i]) for i in range(arr.shape[0])]
            else:
                frames = [(ds, arr)]
            self._load_series(frames, os.path.basename(path))
        except Exception as ex:
            self._show_load_error(path, ex)

    def load_folder(self, path):
        try:
            frames = read_dicom_folder(path)
            self._load_series(frames,
                              os.path.basename(path.rstrip("/\\")))
        except Exception as ex:
            self._show_load_error(path, ex)

    def _load_series(self, frames, title):
        self._series = frames
        self._index = 0
        self._wl_override = None
        self._text_annots = {}
        self._measurements = {}
        self._brightness = 0.0
        self._contrast = 1.0
        self._calibration_mm_per_px = None
        if frames:
            try:
                from ..image_utils import _dicom_pixel_spacing
                self._calibration_mm_per_px = _dicom_pixel_spacing(
                    frames[0][0])
            except Exception:
                pass
        self._invalidate_annot_cache()
        multi = len(frames) > 1
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, len(frames) - 1))
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.slider.setVisible(multi)
        self.frame_info.setVisible(multi)
        self.setToolTip(title)
        self._render_current()
        self.frame_changed.emit(self)

    def _set_index(self, idx):
        if not self._series:
            return
        idx = max(0, min(idx, len(self._series) - 1))
        if idx == self._index:
            return
        self._index = idx
        self.slider.blockSignals(True)
        self.slider.setValue(idx)
        self.slider.blockSignals(False)
        self._render_current()
        self.frame_changed.emit(self)

    def _on_slider(self, v):
        if v != self._index:
            self._index = v
            self._render_current()
            self.frame_changed.emit(self)

    def _render_current(self):
        if not self._series:
            return
        ds, arr = self._series[self._index]
        self._display(arr, ds)
        if len(self._series) > 1:
            self.frame_info.setText(
                "%d / %d" % (self._index + 1, len(self._series)))