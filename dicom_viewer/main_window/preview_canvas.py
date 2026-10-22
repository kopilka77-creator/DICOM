# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .preview_cell import PreviewCell


_SPLITTER_STYLE = (
    "QSplitter::handle { background:#888; }"
    "QSplitter::handle:hover { background:#4a9eff; }"
    "QSplitter::handle:pressed { background:#4a9eff; }")


class PreviewCanvas(QtWidgets.QWidget):
    cell_clicked = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cells = []
        self._mode = 1
        self._sheet_size = (1540, 1870)
        self._split_orientation = QtCore.Qt.Horizontal
        self.setMinimumSize(200, 200)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)

        self._header_lbl = QtWidgets.QLabel()
        self._header_lbl.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self._header_lbl.setStyleSheet(
            "background:#ffffff; color:#000; padding:4px;")
        self._header_lbl.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._header_lbl.setVisible(False)
        self._layout.addWidget(self._header_lbl)

        self._cell_host = QtWidgets.QWidget()
        self._cell_layout = QtWidgets.QVBoxLayout(self._cell_host)
        self._cell_layout.setContentsMargins(0, 0, 0, 0)
        self._cell_layout.setSpacing(0)
        self._layout.addWidget(self._cell_host, 1)

        self._footer_lbl = QtWidgets.QLabel()
        self._footer_lbl.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self._footer_lbl.setStyleSheet(
            "background:#ffffff; color:#000; padding:4px;")
        self._footer_lbl.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self._footer_lbl.setVisible(False)
        self._layout.addWidget(self._footer_lbl)

    def set_sheet_size(self, w, h):
        self._sheet_size = (int(w), int(h))

    def get_sheet_size(self):
        return self._sheet_size

    def set_split_orientation(self, orientation):
        self._split_orientation = orientation

    def _clear_cells(self):
        while self._cell_layout.count():
            item = self._cell_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.cells = []

    def _make_cell(self, vp):
        cell = PreviewCell(vp)
        cell.clicked.connect(self.cell_clicked.emit)
        return cell

    def rebuild(self, source_vps, mode, header_pix, footer_pix,
                show_tags, show_footer, no_border, white_bg):
        self._mode = mode
        self._clear_cells()

        if show_tags and header_pix is not None:
            self._header_lbl.setPixmap(header_pix)
            self._header_lbl.setFixedHeight(header_pix.height() + 8)
            self._header_lbl.setVisible(True)
        else:
            self._header_lbl.setVisible(False)

        if show_footer and footer_pix is not None:
            self._footer_lbl.setPixmap(footer_pix)
            self._footer_lbl.setFixedHeight(footer_pix.height() + 8)
            self._footer_lbl.setVisible(True)
        else:
            self._footer_lbl.setVisible(False)

        vps = list(source_vps[:mode])
        while len(vps) < mode:
            vps.append(None)

        border_style = "" if no_border else "border:1px solid #888;"
        bg = "#ffffff" if white_bg else "#1a1a1a"
        cell_qss = "background:%s; %s" % (bg, border_style)

        if mode == 1:
            cell = self._make_cell(vps[0])
            cell.setStyleSheet(cell_qss)
            self.cells.append(cell)
            self._cell_layout.addWidget(cell)
        elif mode == 2:
            sp = QtWidgets.QSplitter(self._split_orientation)
            sp.setChildrenCollapsible(False)
            sp.setHandleWidth(6)
            sp.setStyleSheet(_SPLITTER_STYLE)
            for vp in vps:
                cell = self._make_cell(vp)
                cell.setStyleSheet(cell_qss)
                self.cells.append(cell)
                sp.addWidget(cell)
            self._cell_layout.addWidget(sp)
        else:
            top = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            bot = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
            outer = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            for s in (top, bot, outer):
                s.setChildrenCollapsible(False)
                s.setHandleWidth(6)
                s.setStyleSheet(_SPLITTER_STYLE)
            for vp in vps[:2]:
                cell = self._make_cell(vp)
                cell.setStyleSheet(cell_qss)
                self.cells.append(cell)
                top.addWidget(cell)
            for vp in vps[2:]:
                cell = self._make_cell(vp)
                cell.setStyleSheet(cell_qss)
                self.cells.append(cell)
                bot.addWidget(cell)
            outer.addWidget(top)
            outer.addWidget(bot)
            self._cell_layout.addWidget(outer)

    def set_source_pixmaps(self, pixmaps):
        for i, cell in enumerate(self.cells):
            if i < len(pixmaps):
                cell.set_source_pixmap(pixmaps[i])

    def reset_view(self, cell):
        if cell in self.cells:
            cell.reset_view()

    def reset_bc(self, cell):
        if cell in self.cells:
            cell.reset_bc()