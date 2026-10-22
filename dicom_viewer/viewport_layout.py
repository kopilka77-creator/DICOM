# -*- coding: utf-8 -*-
import os
from PyQt5 import QtCore, QtWidgets

from .viewport import ViewportWidget


class ViewportLayoutManager(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stack = QtWidgets.QStackedWidget(self)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.stack)

        self.all_viewports = [ViewportWidget(self) for _ in range(4)]
        for vp in self.all_viewports:
            vp.clicked.connect(self._on_vp_clicked)
        self.active_viewport = None

        self.page1 = QtWidgets.QWidget()
        self._grid1 = QtWidgets.QGridLayout(self.page1)
        self._grid1.setContentsMargins(6, 6, 6, 6)
        self._grid1.setSpacing(0)

        self.page2 = QtWidgets.QWidget()
        lay2 = QtWidgets.QVBoxLayout(self.page2)
        lay2.setContentsMargins(6, 6, 6, 6)
        self._split2 = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._split2.setChildrenCollapsible(False)
        self._split2.setHandleWidth(6)
        self._split2.setStyleSheet(
            "QSplitter::handle { background:#3c3c3c; }"
            "QSplitter::handle:hover { background:#4a9eff; }")
        lay2.addWidget(self._split2)

        self.page4 = QtWidgets.QWidget()
        lay4 = QtWidgets.QVBoxLayout(self.page4)
        lay4.setContentsMargins(6, 6, 6, 6)
        self._split4_outer = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self._split4_outer.setChildrenCollapsible(False)
        self._split4_outer.setHandleWidth(6)
        self._split4_top = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._split4_top.setChildrenCollapsible(False)
        self._split4_top.setHandleWidth(6)
        self._split4_bot = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self._split4_bot.setChildrenCollapsible(False)
        self._split4_bot.setHandleWidth(6)
        self._split4_outer.addWidget(self._split4_top)
        self._split4_outer.addWidget(self._split4_bot)
        for sp in (self._split4_outer, self._split4_top, self._split4_bot):
            sp.setStyleSheet(
                "QSplitter::handle { background:#3c3c3c; }"
                "QSplitter::handle:hover { background:#4a9eff; }")
        lay4.addWidget(self._split4_outer)

        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.stack.addWidget(self.page4)
        self._arrange(1)

    def _arrange(self, mode):
        for vp in self.all_viewports:
            vp.setParent(None)
            vp.hide()
        if mode == 1:
            self._grid1.addWidget(self.all_viewports[0], 0, 0)
            self.all_viewports[0].show()
            self.stack.setCurrentWidget(self.page1)
            self._set_active_vp(self.all_viewports[0])
        elif mode == 2:
            self._split2.addWidget(self.all_viewports[0])
            self._split2.addWidget(self.all_viewports[1])
            self.all_viewports[0].show(); self.all_viewports[1].show()
            try: self._split2.setSizes([1, 1])
            except Exception: pass
            self.stack.setCurrentWidget(self.page2)
            if (self.active_viewport is None
                    or not self.active_viewport.isVisible()):
                self._set_active_vp(self.all_viewports[0])
        else:
            self._split4_top.addWidget(self.all_viewports[0])
            self._split4_top.addWidget(self.all_viewports[1])
            self._split4_bot.addWidget(self.all_viewports[2])
            self._split4_bot.addWidget(self.all_viewports[3])
            for vp in self.all_viewports:
                vp.show()
            try:
                self._split4_outer.setSizes([1, 1])
                self._split4_top.setSizes([1, 1])
                self._split4_bot.setSizes([1, 1])
            except Exception: pass
            self.stack.setCurrentWidget(self.page4)
            if (self.active_viewport is None
                    or not self.active_viewport.isVisible()):
                self._set_active_vp(self.all_viewports[0])

    def _set_active_vp(self, vp):
        if self.active_viewport is vp: return
        if self.active_viewport is not None:
            try: self.active_viewport.set_active(False)
            except Exception: pass
        self.active_viewport = vp
        if vp is not None: vp.set_active(True)

    def _on_vp_clicked(self, vp):
        self._set_active_vp(vp)

    def set_layout_mode(self, mode):
        self._arrange(mode)

    def open_in_active(self, path):
        vp = self.active_viewport
        if vp is None or not vp.isVisible():
            for v in self.all_viewports:
                if v.isVisible(): vp = v; break
        if vp is None: vp = self.all_viewports[0]
        self._set_active_vp(vp)
        if os.path.isdir(path): vp.load_folder(path)
        else: vp.load_path(path)