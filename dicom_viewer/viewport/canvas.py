# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets


class _Canvas(QtWidgets.QLabel):
    def __init__(self, viewport):
        super().__init__()
        self._vp = viewport
        self.setMouseTracking(True)

    def mousePressEvent(self, e):
        self._vp._on_canvas_press(e)
        e.accept()

    def mouseMoveEvent(self, e):
        self._vp._on_canvas_move(e)
        e.accept()

    def mouseReleaseEvent(self, e):
        self._vp._on_canvas_release(e)
        e.accept()

    def mouseDoubleClickEvent(self, e):
        self._vp._on_canvas_double(e)
        e.accept()

    def wheelEvent(self, e):
        self._vp._on_canvas_wheel(e)
        e.accept()

    def keyPressEvent(self, e):
        self._vp.keyPressEvent(e)
        e.accept()