# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from .canvas import _Canvas
from .render import _RenderMixin
from .text import _TextMixin
from .measure import _MeasureMixin
from .events import _EventsMixin


class ViewportWidget(_RenderMixin, _MeasureMixin, _TextMixin,
                     _EventsMixin, QtWidgets.QWidget):
    clicked = QtCore.pyqtSignal(object)
    frame_changed = QtCore.pyqtSignal(object)
    text_mode_changed = QtCore.pyqtSignal(object, bool)
    measure_status = QtCore.pyqtSignal(str)
    measure_mode_changed = QtCore.pyqtSignal(object, str)
    annot_changed = QtCore.pyqtSignal()

    _WL_SENSITIVITY_PX = 400.0
    _MAX_SCALED_PIXELS = 64000000
    _FONT_REFERENCE = 512.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(180, 220)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._active = False

        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(QtCore.Qt.AlignCenter)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet(
            "QScrollArea { background:#141414; border:none; border-radius:8px; }"
            "QScrollArea > QWidget > QWidget { background:#141414; }")

        self.image_label = _Canvas(self)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setStyleSheet("color:#888; background:#141414;")
        self.image_label.setText("Перетащите DICOM, ZIP\nили папку сюда")
        self.scroll.setWidget(self.image_label)
        self.scroll.viewport().installEventFilter(self)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setVisible(False)
        self.slider.valueChanged.connect(self._on_slider)

        self.frame_info = QtWidgets.QLabel("", self)
        self.frame_info.setAlignment(QtCore.Qt.AlignCenter)
        self.frame_info.setVisible(False)
        self.frame_info.setStyleSheet("color:#a0a0a0; font-size:9pt;")

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)
        v.addWidget(self.scroll, 1)
        v.addWidget(self.slider, 0)
        v.addWidget(self.frame_info, 0)

        self._series = []
        self._index = 0
        self._src_pixmap = None
        self._annot_cache = None
        self._img_bytes = None
        self._zoom = 0.0
        self._invert = False
        self._wl_override = None
        self._show_annot = True
        self._font_scale = 1.0

        self._raw_arr = None
        self._raw_ds = None
        self._cache_base = None
        self._cache_base_key = None
        self._cache_final_key = None
        self._auto_wl_key = None
        self._auto_wl_cache = None
        self._brightness = 0.0
        self._contrast = 1.0
        self._print_cache = None
        self._print_cache_key = None

        self._drag_mode = None
        self._drag_start_global = None
        self._drag_wl = (0.0, 1.0)
        self._drag_scroll = (0, 0)

        self._text_drag_idx = None
        self._text_drag_start_xn = 0.0
        self._text_drag_start_yn = 0.0
        self._text_drag_label_w = 1
        self._text_drag_label_h = 1
        self._text_annots = {}
        self._text_mode = False

        self._calibration_mm_per_px = None
        self._measure_mode = None
        self._measure_start = None
        self._measurements = {}
        self._drag_measure = None
        self._drag_part = None
        self._drag_orig = None

    # ─── общие хелперы ───
    def _canvas_to_native(self, pos):
        if not self._series or self._src_pixmap is None:
            return None
        pm = self.image_label.pixmap()
        if pm is None or pm.isNull():
            return None
        W, H = self._src_pixmap.width(), self._src_pixmap.height()
        if W <= 0 or H <= 0:
            return None
        return (pos.x() * (float(W) / pm.width()),
                pos.y() * (float(H) / pm.height()))

    def _find_viewport_parent(self, w):
        while w is not None:
            if isinstance(w, ViewportWidget):
                return w
            w = w.parentWidget()
        return None