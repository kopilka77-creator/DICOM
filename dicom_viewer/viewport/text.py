# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from ..dialogs import TextAnnotationDialog


class _TextMixin:
    def _hit_test_text(self, pos):
        if not self._series or self._src_pixmap is None:
            return None
        pm = self.image_label.pixmap()
        if pm is None or pm.isNull():
            return None
        lbl_w, lbl_h = pm.width(), pm.height()
        if lbl_w <= 0 or lbl_h <= 0:
            return None
        texts = self._text_annots.get(self._index, [])
        if not texts:
            return None
        W, H = self._src_pixmap.width(), self._src_pixmap.height()
        if W <= 0 or H <= 0:
            return None
        scale = max(W, H) / self._FONT_REFERENCE * self._font_scale
        nx = pos.x() * (float(W) / lbl_w)
        ny = pos.y() * (float(H) / lbl_h)
        for i in range(len(texts) - 1, -1, -1):
            item = texts[i]
            if len(item) == 4:
                xn, yn, text, mult = item
            elif len(item) == 3:
                xn, yn, text = item
                mult = 1.0
            else:
                continue
            pt = max(8, int(round(14 * scale * float(mult))))
            fm = QtGui.QFontMetrics(
                QtGui.QFont("Arial", pt, QtGui.QFont.Bold))
            x_native = xn * W
            y_native = yn * H
            w = fm.boundingRect(text).width()
            h = fm.height()
            bbox = QtCore.QRectF(x_native, y_native - fm.ascent(), w, h)
            if bbox.contains(nx, ny):
                return (self._index, i)
        return None

    def _handle_text_click(self, e):
        pixmap = self.image_label.pixmap()
        if (pixmap is None or pixmap.width() <= 0
                or pixmap.height() <= 0):
            return
        pos = e.pos()
        xn = pos.x() / float(pixmap.width())
        yn = pos.y() / float(pixmap.height())
        if not (0.0 <= xn <= 1.0 and 0.0 <= yn <= 1.0):
            return
        dlg = TextAnnotationDialog(self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        text, mult = dlg.result_text()
        if not text:
            return
        self._text_annots.setdefault(self._index, []).append(
            (xn, yn, text, mult))
        self._invalidate_annot_cache()
        self._apply_scaled()
        self.set_text_mode(False)

    def _start_text_drag(self, hit, e):
        frame_idx, list_idx = hit
        texts = self._text_annots.get(frame_idx, [])
        if list_idx < 0 or list_idx >= len(texts):
            return
        item = texts[list_idx]
        if len(item) == 4:
            xn, yn, _t, _m = item
        else:
            xn, yn, _t = item
        pm = self.image_label.pixmap()
        self._text_drag_idx = (frame_idx, list_idx)
        self._text_drag_start_xn = xn
        self._text_drag_start_yn = yn
        self._drag_start_global = e.globalPos()
        self._text_drag_label_w = max(1, pm.width() if pm else 1)
        self._text_drag_label_h = max(1, pm.height() if pm else 1)
        self._drag_mode = "text"
        self.image_label.setCursor(QtCore.Qt.ClosedHandCursor)

    def _drag_text_move(self, e):
        if self._text_drag_idx is None:
            return
        frame_idx, list_idx = self._text_drag_idx
        texts = self._text_annots.get(frame_idx, [])
        if list_idx < 0 or list_idx >= len(texts):
            return
        d = e.globalPos() - self._drag_start_global
        lw = max(1, self._text_drag_label_w)
        lh = max(1, self._text_drag_label_h)
        new_xn = max(0.0, min(1.0,
            self._text_drag_start_xn + d.x() / float(lw)))
        new_yn = max(0.0, min(1.0,
            self._text_drag_start_yn + d.y() / float(lh)))
        item = texts[list_idx]
        if len(item) == 4:
            _, _, text, mult = item
        else:
            _, _, text = item
            mult = 1.0
        texts[list_idx] = (new_xn, new_yn, text, mult)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _edit_text(self, frame_idx, list_idx):
        texts = self._text_annots.get(frame_idx, [])
        if list_idx < 0 or list_idx >= len(texts):
            return
        item = texts[list_idx]
        if len(item) == 4:
            xn, yn, text, mult = item
        elif len(item) == 3:
            xn, yn, text = item
            mult = 1.0
        else:
            return
        dlg = TextAnnotationDialog(self, initial_text=text,
                                   initial_mult=mult,
                                   allow_delete=True)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        if dlg.result_action() == TextAnnotationDialog.ACTION_DELETE:
            texts.pop(list_idx)
            if not texts:
                self._text_annots.pop(frame_idx, None)
        else:
            new_text, new_mult = dlg.result_text()
            if new_text:
                texts[list_idx] = (xn, yn, new_text, new_mult)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _delete_text(self, frame_idx, list_idx):
        texts = self._text_annots.get(frame_idx, [])
        if list_idx < 0 or list_idx >= len(texts):
            return
        texts.pop(list_idx)
        if not texts:
            self._text_annots.pop(frame_idx, None)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _show_text_context_menu(self, hit, global_pos):
        frame_idx, list_idx = hit
        menu = QtWidgets.QMenu(self)
        act_edit = menu.addAction("Редактировать...")
        act_del = menu.addAction("Удалить")
        try:
            chosen = menu.exec_(global_pos)
        except Exception:
            chosen = None
        if chosen is act_edit:
            self._edit_text(frame_idx, list_idx)
        elif chosen is act_del:
            self._delete_text(frame_idx, list_idx)

    def set_text_mode(self, on):
        self._text_mode = bool(on)
        if self._text_mode:
            self.image_label.setCursor(QtCore.Qt.IBeamCursor)
        else:
            self.image_label.setCursor(QtCore.Qt.ArrowCursor)
        self.text_mode_changed.emit(self, self._text_mode)

    def is_text_mode(self):
        return self._text_mode

    def clear_texts_current(self):
        self._text_annots.pop(self._index, None)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def clear_texts_all(self):
        self._text_annots.clear()
        self._invalidate_annot_cache()
        self._apply_scaled()