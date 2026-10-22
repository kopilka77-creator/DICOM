# -*- coding: utf-8 -*-
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets


class PreviewCell(QtWidgets.QLabel):
    """Ячейка предпросмотра: свой B/C, зум, панорама.
    Управление мышью:
      колесо — зум
      ЛКМ + drag — панорама
      ПКМ / Ctrl+ЛКМ + drag — яркость/контраст
    """
    clicked = QtCore.pyqtSignal(object)

    def __init__(self, source_vp, parent=None):
        super().__init__(parent)
        self.source = source_vp
        self.setMinimumSize(80, 80)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet("background:#1a1a1a; color:#666;")
        self.setMouseTracking(True)

        st = getattr(source_vp, "_preview_state", None)
        if st is None:
            st = {"brightness": 0.0, "contrast": 1.0,
                  "zoom": 0.0, "pan_x": 0, "pan_y": 0}
            if source_vp is not None:
                source_vp._preview_state = st
        self._state = st

        self._pix = None
        self._drag = None
        self._drag_start = None
        self._drag_orig = None

    # ── источник ──
    def set_source_pixmap(self, pix):
        self._pix = pix
        self._render()

    # ── рендер ──
    def _render(self):
        if self._pix is None or self._pix.isNull():
            self.clear()
            return
        src = self._pix
        # B/C локальный
        b = self._state["brightness"]
        c = self._state["contrast"]
        if b != 0.0 or c != 1.0:
            img = src.toImage().convertToFormat(
                QtGui.QImage.Format_RGB888)
            w, h = img.width(), img.height()
            ptr = img.bits()
            ptr.setsize(img.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape(
                (h, w * 3)).astype(np.float32)
            arr = (arr - 128.0) * c + 128.0 + b
            arr = np.clip(arr, 0, 255).astype(np.uint8)
            img2 = QtGui.QImage(arr.tobytes(), w, h, w * 3,
                                QtGui.QImage.Format_RGB888).copy()
            src = QtGui.QPixmap.fromImage(img2)

        vw, vh = self.width(), self.height()
        if vw <= 0 or vh <= 0:
            return

        z = self._state["zoom"]
        if z <= 0:
            scaled = src.scaled(vw, vh, QtCore.Qt.KeepAspectRatio,
                                QtCore.Qt.SmoothTransformation)
        else:
            tw = max(1, int(src.width() * z))
            th = max(1, int(src.height() * z))
            scaled = src.scaled(tw, th, QtCore.Qt.KeepAspectRatio,
                                QtCore.Qt.SmoothTransformation)

        if scaled.width() > vw or scaled.height() > vh:
            canvas = QtGui.QPixmap(vw, vh)
            canvas.fill(QtGui.QColor(20, 20, 20))
            p = QtGui.QPainter(canvas)
            try:
                x = (vw - scaled.width()) // 2 + self._state["pan_x"]
                y = (vh - scaled.height()) // 2 + self._state["pan_y"]
                if scaled.width() > vw:
                    x = max(vw - scaled.width(), min(0, x))
                else:
                    x = (vw - scaled.width()) // 2
                if scaled.height() > vh:
                    y = max(vh - scaled.height(), min(0, y))
                else:
                    y = (vh - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
            finally:
                p.end()
            self.setPixmap(canvas)
        else:
            self._state["pan_x"] = 0
            self._state["pan_y"] = 0
            self.setPixmap(scaled)

    # ── события ──
    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy == 0:
            return
        base = self._state["zoom"] if self._state["zoom"] > 0 else 1.0
        if dy > 0:
            self._state["zoom"] = min(5.0, base * 1.2)
        else:
            self._state["zoom"] = max(0.1, base * 0.8)
        self._render()
        e.accept()

    def mousePressEvent(self, e):
        self.clicked.emit(self)
        self.setFocus()
        if e.button() == QtCore.Qt.LeftButton:
            if e.modifiers() & QtCore.Qt.ControlModifier:
                self._drag = "bc"
            else:
                self._drag = "pan"
        elif e.button() == QtCore.Qt.RightButton:
            self._drag = "bc"
        else:
            return
        self._drag_start = e.pos()
        self._drag_orig = (self._state["pan_x"], self._state["pan_y"],
                           self._state["brightness"],
                           self._state["contrast"])
        if self._drag == "pan":
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        else:
            self.setCursor(QtCore.Qt.SizeVerCursor)

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        d = e.pos() - self._drag_start
        if self._drag == "pan":
            self._state["pan_x"] = self._drag_orig[0] + d.x()
            self._state["pan_y"] = self._drag_orig[1] + d.y()
        else:
            b0, c0 = self._drag_orig[2], self._drag_orig[3]
            b = b0 + d.y() * 0.5
            c = c0 * (1.0 + d.x() / 200.0)
            self._state["brightness"] = max(-100.0, min(100.0, b))
            self._state["contrast"] = max(0.1, min(3.0, c))
        self._render()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(QtCore.Qt.ArrowCursor)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._render()

    # ── публичное API ──
    def reset_view(self):
        self._state["zoom"] = 0.0
        self._state["pan_x"] = 0
        self._state["pan_y"] = 0
        self._state["brightness"] = 0.0
        self._state["contrast"] = 1.0
        self._render()

    def reset_bc(self):
        self._state["brightness"] = 0.0
        self._state["contrast"] = 1.0
        self._render()