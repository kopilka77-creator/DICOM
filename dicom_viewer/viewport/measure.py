# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from ..measure import _Measure
from ..image_utils import _dicom_pixel_spacing


class _MeasureMixin:
    def set_calibration(self, mm_per_px):
        self._calibration_mm_per_px = mm_per_px
        self._invalidate_annot_cache()
        self._apply_scaled()

    def get_calibration(self):
        return self._calibration_mm_per_px

    def has_calibration(self):
        return self._calibration_mm_per_px is not None

    def set_measure_mode(self, mode):
        self._measure_mode = mode
        self._measure_start = None
        if mode:
            self.image_label.setCursor(QtCore.Qt.CrossCursor)
        elif self._text_mode:
            self.image_label.setCursor(QtCore.Qt.IBeamCursor)
        else:
            self.image_label.setCursor(QtCore.Qt.ArrowCursor)
        self.measure_status.emit(self._measure_hint())
        self.measure_mode_changed.emit(self, mode or "")
        self._invalidate_annot_cache()
        self._apply_scaled()

    def get_measure_mode(self):
        return self._measure_mode

    def clear_measurements(self):
        self._measurements.clear()
        self._calibration_mm_per_px = None
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _measure_hint(self):
        if self._measure_mode == "calibrate":
            return "Калибровка: клик 2 точки шара"
        if self._measure_mode == "ruler":
            return "Линейка: клик 2 точки"
        return ""

    def _measure_label_text(self, m):
        if m.is_calibration and m.known_mm is not None:
            return "%.2f мм (кал.)" % m.known_mm
        cal = self._calibration_mm_per_px
        if cal:
            return "%.2f мм (%.1f px)" % (m.dist_px * cal, m.dist_px)
        return "%.1f px" % m.dist_px

    def _hit_test_measure(self, native):
        items = self._measurements.get(self._index, [])
        if not items or self._src_pixmap is None:
            return None
        W, H = self._src_pixmap.width(), self._src_pixmap.height()
        tol = max(10, int(min(W, H) * 0.025))
        nx, ny = native
        for m in items:
            if abs(nx - m.p1[0]) <= tol and abs(ny - m.p1[1]) <= tol:
                return (m, "p1")
            if abs(nx - m.p2[0]) <= tol and abs(ny - m.p2[1]) <= tol:
                return (m, "p2")
        pt = max(10, int(round(14 * max(W, H) / self._FONT_REFERENCE)))
        fm = QtGui.QFontMetrics(
            QtGui.QFont("Arial", pt, QtGui.QFont.Bold))
        for m in items:
            text = self._measure_label_text(m)
            tw = fm.boundingRect(text).width()
            th = fm.height()
            mx, my = m.mid()
            bbox = QtCore.QRectF(mx - tw / 2.0 - 4,
                                 my - th / 2.0 - 4, tw + 8, th + 8)
            if bbox.contains(nx, ny):
                return (m, "label")
        return None

    def _recalc_calibration(self):
        self._calibration_mm_per_px = None
        for m in self._measurements.get(self._index, []):
            if m.is_calibration and m.known_mm and m.dist_px > 0:
                self._calibration_mm_per_px = m.known_mm / m.dist_px
                return
        if self._series:
            try:
                self._calibration_mm_per_px = _dicom_pixel_spacing(
                    self._series[self._index][0])
            except Exception:
                pass

    def _handle_measure_click(self, canvas_pos, button):
        if button != QtCore.Qt.LeftButton:
            return False
        native = self._canvas_to_native(canvas_pos)
        if native is None:
            return True
        if self._measure_start is None:
            self._measure_start = native
            self.measure_status.emit(self._measure_hint())
            self._invalidate_annot_cache()
            self._apply_scaled()
            return True
        p1 = self._measure_start
        p2 = native
        self._measure_start = None
        is_cal = (self._measure_mode == "calibrate")
        m = _Measure(p1, p2, known_mm=None, is_calibration=is_cal)
        self._measurements.setdefault(self._index, []).append(m)
        if is_cal:
            try:
                dlg = QtWidgets.QInputDialog(self)
                dlg.setWindowTitle("Калибровка по шару")
                dlg.setLabelText("Введите реальный диаметр объекта (мм):")
                dlg.setInputMode(QtWidgets.QInputDialog.DoubleInput)
                dlg.setDoubleRange(0.001, 1e6)
                dlg.setDoubleDecimals(3)
                dlg.setDoubleValue(20.0)
                if dlg.exec_() == QtWidgets.QDialog.Accepted:
                    m.known_mm = float(dlg.doubleValue())
                    self._recalc_calibration()
                    self.measure_status.emit(
                        "Калибровка: %.4f мм/px"
                        % (self._calibration_mm_per_px or 0))
                else:
                    self._measurements.get(self._index, []).remove(m)
            except Exception:
                pass
        else:
            self.measure_status.emit(
                "Измерение: %s" % self._measure_label_text(m))
        self.set_measure_mode(None)
        self._invalidate_annot_cache()
        self._apply_scaled()
        return True

    def _edit_calibration_value(self, m):
        if not m.is_calibration:
            return
        try:
            dlg = QtWidgets.QInputDialog(self)
            dlg.setWindowTitle("Изменить значение калибровки")
            dlg.setLabelText("Диаметр объекта (мм):")
            dlg.setInputMode(QtWidgets.QInputDialog.DoubleInput)
            dlg.setDoubleRange(0.001, 1e6)
            dlg.setDoubleDecimals(3)
            dlg.setDoubleValue(m.known_mm or 20.0)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                m.known_mm = float(dlg.doubleValue())
                self._recalc_calibration()
                self._invalidate_annot_cache()
                self._apply_scaled()
        except Exception:
            pass

    def _delete_measure(self, m):
        try:
            self._measurements.get(self._index, []).remove(m)
        except ValueError:
            pass
        self._recalc_calibration()
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _measure_context_menu(self, m, global_pos):
        menu = QtWidgets.QMenu(self)
        act_edit = (menu.addAction("Изменить значение (мм)...")
                    if m.is_calibration else None)
        act_del = menu.addAction("Удалить измерение")
        try:
            chosen = menu.exec_(global_pos)
        except Exception:
            chosen = None
        if act_edit is not None and chosen is act_edit:
            self._edit_calibration_value(m)
        elif chosen is act_del:
            self._delete_measure(m)

    def _start_measure_drag(self, hit, e):
        m, part = hit
        self._drag_mode = "measure"
        self._drag_measure = m
        self._drag_part = part
        self._drag_start_global = e.globalPos()
        if part == "p1":
            self._drag_orig = tuple(m.p1)
        elif part == "p2":
            self._drag_orig = tuple(m.p2)
        else:
            self._drag_orig = (m.label_dx, m.label_dy)

    def _drag_measure_move(self, e):
        if self._drag_measure is None or self._drag_part is None:
            return
        pm = self.image_label.pixmap()
        if pm is None or pm.isNull() or self._src_pixmap is None:
            return
        W, H = self._src_pixmap.width(), self._src_pixmap.height()
        d = e.globalPos() - self._drag_start_global
        dnx = d.x() * W / float(pm.width())
        dny = d.y() * H / float(pm.height())
        m = self._drag_measure
        if self._drag_part == "p1":
            m.p1 = [self._drag_orig[0] + dnx, self._drag_orig[1] + dny]
        elif self._drag_part == "p2":
            m.p2 = [self._drag_orig[0] + dnx, self._drag_orig[1] + dny]
        else:
            m.label_dx = self._drag_orig[0] + dnx
            m.label_dy = self._drag_orig[1] + dny
        if m.is_calibration:
            self._recalc_calibration()
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _draw_cross(self, painter, x, y, color, size):
        painter.setPen(QtGui.QPen(color, 2))
        painter.drawLine(QtCore.QPointF(x - size, y - size),
                         QtCore.QPointF(x + size, y + size))
        painter.drawLine(QtCore.QPointF(x - size, y + size),
                         QtCore.QPointF(x + size, y - size))

    def _draw_measurements(self, painter, W, H):
        items = self._measurements.get(self._index, [])
        pending = self._measure_start
        pt = max(10, int(round(14 * max(W, H) / self._FONT_REFERENCE)))
        painter.setFont(QtGui.QFont("Arial", pt, QtGui.QFont.Bold))
        fm = painter.fontMetrics()
        cs = max(4, pt // 3)
        for m in items:
            color = (QtGui.QColor(255, 200, 0) if m.is_calibration
                     else QtGui.QColor(0, 255, 0))
            painter.setPen(QtGui.QPen(color, 2))
            painter.drawLine(QtCore.QPointF(*m.p1),
                             QtCore.QPointF(*m.p2))
            self._draw_cross(painter, m.p1[0], m.p1[1], color, cs)
            self._draw_cross(painter, m.p2[0], m.p2[1], color, cs)
            text = self._measure_label_text(m)
            tw = fm.boundingRect(text).width()
            th = fm.height()
            mx, my = m.mid()
            tx = mx - tw / 2.0
            ty = my + fm.ascent() / 2.0 - 2
            painter.setBrush(QtGui.QColor(0, 0, 0, 210))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRect(QtCore.QRectF(
                tx - 4, ty - fm.ascent() - 2, tw + 8, th + 4))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(color)
            painter.drawText(QtCore.QPointF(tx, ty), text)
        if pending is not None:
            self._draw_cross(painter, pending[0], pending[1],
                             QtGui.QColor(255, 255, 0), cs + 2)