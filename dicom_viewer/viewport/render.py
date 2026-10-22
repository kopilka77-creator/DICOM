# -*- coding: utf-8 -*-
import numpy as np
from PyQt5 import QtCore, QtGui

from ..image_utils import _to_display_uint8, _scalar


class _RenderMixin:
    def _set_frame(self, arr, ds):
        self._raw_arr = arr
        self._raw_ds = ds
        self._cache_base = None
        self._cache_base_key = None
        self._cache_final_key = None
        self._auto_wl_key = None
        self._src_pixmap = None
        self._annot_cache = None
        self._print_cache = None

    def _display(self, arr, ds):
        self._set_frame(arr, ds)
        self._recompute()

    def _recompute(self):
        if self._raw_arr is None:
            return
        base_key = (self._index, id(self._raw_arr),
                    self._wl_override, self._invert)
        if self._cache_base_key != base_key or self._cache_base is None:
            self._cache_base = self._compute_base()
            self._cache_base_key = base_key
        final_key = (base_key, self._brightness, self._contrast)
        if self._cache_final_key != final_key or self._src_pixmap is None:
            u8 = self._compute_bc(self._cache_base)
            self._make_pixmap(u8)
            self._cache_final_key = final_key
            self._annot_cache = None
            self._print_cache = None
        self._apply_scaled()

    def _effective_wl(self):
        if not self._series:
            return (40.0, 400.0)
        ds, arr = self._series[self._index]
        if self._wl_override is not None:
            return self._wl_override
        key = (self._index, id(arr))
        if self._auto_wl_key == key and self._auto_wl_cache is not None:
            return self._auto_wl_cache
        wc = _scalar(getattr(ds, "WindowCenter", None))
        ww = _scalar(getattr(ds, "WindowWidth", None))
        if wc is not None and ww is not None and ww > 0:
            result = (wc, ww)
        else:
            a = arr.astype(np.float32)
            try:
                slope = float(getattr(ds, "RescaleSlope", 1) or 1)
                inter = float(getattr(ds, "RescaleIntercept", 0) or 0)
                if slope != 1.0 or inter != 0.0:
                    a = a * slope + inter
            except Exception:
                pass
            lo, hi = float(a.min()), float(a.max())
            result = ((lo + hi) / 2.0, max(1.0, hi - lo))
        self._auto_wl_key = key
        self._auto_wl_cache = result
        return result

    def _compute_base(self):
        arr = self._raw_arr
        ds = self._raw_ds
        if arr.ndim == 3 and arr.shape[2] in (3, 4):
            u8 = arr.astype(np.uint8) if arr.dtype != np.uint8 else arr
            if u8.shape[2] == 4:
                u8 = u8[:, :, :3]
            if self._invert:
                u8 = 255 - u8
            return u8
        wc, ww = self._effective_wl()
        return _to_display_uint8(arr, ds, wc=wc, ww=ww,
                                 invert=self._invert)

    def _compute_bc(self, base):
        if self._brightness == 0.0 and self._contrast == 1.0:
            return np.stack([base] * 3, -1) if base.ndim == 2 else base
        a = base.astype(np.float32)
        a = (a - 128.0) * self._contrast + 128.0 + self._brightness
        a = np.clip(a, 0, 255).astype(np.uint8)
        return np.stack([a] * 3, -1) if a.ndim == 2 else a

    def _make_pixmap(self, u8):
        u8 = np.ascontiguousarray(u8)
        h, w = u8.shape[:2]
        self._img_bytes = u8.tobytes()
        img = QtGui.QImage(self._img_bytes, w, h, w * 3,
                           QtGui.QImage.Format_RGB888).copy()
        self._src_pixmap = QtGui.QPixmap.fromImage(img)

    def set_window_level(self, wc, ww):
        self._wl_override = (float(wc), float(ww))
        self._recompute()

    def auto_window_level(self):
        self._wl_override = None
        self._recompute()

    def set_brightness(self, v):
        self._brightness = float(v)
        self._recompute()

    def set_contrast(self, v):
        self._contrast = float(v)
        self._recompute()

    def set_bc(self, brightness, contrast):
        self._brightness = float(brightness)
        self._contrast = float(contrast)
        self._recompute()

    def get_brightness(self):
        return self._brightness

    def get_contrast(self):
        return self._contrast

    def reset_bc(self):
        self._brightness = 0.0
        self._contrast = 1.0
        self._recompute()

    def toggle_invert(self):
        self._invert = not self._invert
        self._recompute()

    def apply_preset(self, wl):
        if wl is None:
            self.auto_window_level()
        else:
            self.set_window_level(wl[0], wl[1])

    def reset_view(self):
        self._zoom = 0.0
        self._invert = False
        self._wl_override = None
        self._brightness = 0.0
        self._contrast = 1.0
        self._recompute()

    def _max_zoom_for(self, pm):
        if pm is None or pm.isNull():
            return 1.0
        px = max(1, pm.width() * pm.height())
        if px >= self._MAX_SCALED_PIXELS:
            return 1.0
        return (self._MAX_SCALED_PIXELS / float(px)) ** 0.5

    def zoom_in(self):
        base = self._zoom if self._zoom > 0 else 1.0
        limit = self._max_zoom_for(self._src_pixmap)
        self._zoom = min(limit, base * 1.25)
        self._apply_scaled()

    def zoom_out(self):
        base = self._zoom if self._zoom > 0 else 1.0
        self._zoom = max(0.1, base * 0.8)
        self._apply_scaled()

    def zoom_fit(self):
        self._zoom = 0.0
        self._apply_scaled()

    def zoom_1to1(self):
        self._zoom = 1.0
        self._apply_scaled()

    def set_show_annotations(self, show):
        self._show_annot = bool(show)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def set_font_scale(self, mult):
        self._font_scale = float(mult)
        self._invalidate_annot_cache()
        self._apply_scaled()

    def _invalidate_annot_cache(self):
        self._annot_cache = None
        self._print_cache = None
        try:
            self.annot_changed.emit()
        except Exception:
            pass

    def _annotated_source(self):
        if self._annot_cache is not None:
            return self._annot_cache
        if self._src_pixmap is None:
            return None
        try:
            if self._series:
                self._annot_cache = self._render_annotations(
                    self._src_pixmap, show_info=self._show_annot)
            else:
                self._annot_cache = self._src_pixmap
        except Exception:
            self._annot_cache = self._src_pixmap
        return self._annot_cache

    def _apply_scaled(self):
        if self._src_pixmap is None:
            return
        try:
            src = self._annotated_source()
            if src is None or src.isNull():
                return
            vw = self.scroll.viewport().width()
            vh = self.scroll.viewport().height()
            if vw < 10 or vh < 10:
                return
            if self._zoom <= 0:
                tw, th = vw, vh
            else:
                tw = max(1, int(src.width() * self._zoom))
                th = max(1, int(src.height() * self._zoom))
            if tw * th > self._MAX_SCALED_PIXELS:
                factor = (self._MAX_SCALED_PIXELS / float(tw * th)) ** 0.5
                tw = max(1, int(tw * factor))
                th = max(1, int(th * factor))
            if self._zoom <= 0 or tw * th < 4000000:
                transform = QtCore.Qt.SmoothTransformation
            else:
                transform = QtCore.Qt.FastTransformation
            pix = src.scaled(tw, th, QtCore.Qt.KeepAspectRatio, transform)
            if pix is None or pix.isNull():
                return
            self.image_label.setPixmap(pix)
            try:
                self.image_label.resize(pix.size())
            except Exception:
                pass
        except Exception:
            pass

    def _render_annotations(self, pix, show_info=True):
        try:
            if not self._series:
                return pix
            ds, _ = self._series[self._index]
            result = pix.copy()
            W, H = result.width(), result.height()
            scale = max(W, H) / self._FONT_REFERENCE * self._font_scale
            small_pt = max(6, int(round(9 * scale)))
            p = QtGui.QPainter(result)
            try:
                p.setRenderHint(QtGui.QPainter.Antialiasing, True)
                p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
                if show_info:
                    p.setFont(QtGui.QFont("Arial", small_pt))
                    fm = p.fontMetrics()
                    lh = fm.height() + max(1, int(small_pt * 0.2))
                    margin = max(4, int(small_pt * 0.6))

                    def draw(x, y, lines, align="left"):
                        for i, line in enumerate(lines):
                            if not line:
                                continue
                            yy = y + i * lh
                            w = fm.boundingRect(line).width()
                            if align == "right":
                                xx = x - w
                            elif align == "center":
                                xx = x - w // 2
                            else:
                                xx = x
                            p.setPen(QtGui.QColor(0, 0, 0, 220))
                            p.drawText(xx + 1, yy + 1, line)
                            p.setPen(QtGui.QColor(255, 255, 255, 235))
                            p.drawText(xx, yy, line)

                    base_top = margin + fm.ascent()
                    base_bottom = H - margin - fm.descent()
                    tl = [str(getattr(ds, a, "") or "").strip()
                          for a in ("PatientName", "PatientID",
                                    "PatientBirthDate")]
                    tl = [x for x in tl if x]
                    if tl:
                        draw(margin, base_top, tl, "left")
                    tr = []
                    mod = str(getattr(ds, "Modality", "") or "").strip()
                    if mod:
                        tr.append(mod)
                    for attr, pref in (("SeriesNumber", "Series: "),
                                       ("InstanceNumber", "Inst: ")):
                        v = str(getattr(ds, attr, "") or "").strip()
                        if v:
                            tr.append(pref + v)
                    if tr:
                        draw(W - margin, base_top, tr, "right")
                    bl = []
                    wc, ww = self._effective_wl()
                    bl.append("W: %.2f  L: %.2f" % (ww, wc))
                    bl.append("Zoom: fit" if self._zoom <= 0
                              else "Zoom: %.2fx" % self._zoom)
                    if self._invert:
                        bl.append("INVERTED")
                    if self._brightness != 0.0 or self._contrast != 1.0:
                        bl.append("B: %+.0f  C: %.2f"
                                  % (self._brightness, self._contrast))
                    if self._calibration_mm_per_px:
                        bl.append("Cal: %.4f mm/px"
                                  % self._calibration_mm_per_px)
                    start_y = base_bottom - lh * (len(bl) - 1)
                    draw(margin, start_y, bl, "left")
                    if len(self._series) > 1:
                        draw(W - margin, base_bottom,
                             ["%d / %d" % (self._index + 1,
                                           len(self._series))], "right")
                    for item in self._text_annots.get(self._index, []):
                        if isinstance(item, tuple) and len(item) == 4:
                            xn, yn, text, mult = item
                        elif isinstance(item, tuple) and len(item) == 3:
                            xn, yn, text = item
                            mult = 1.0
                        else:
                            continue
                        x = int(xn * W)
                        y = int(yn * H)
                        pt = max(8, int(round(14 * scale * float(mult))))
                        p.setFont(
                            QtGui.QFont("Arial", pt, QtGui.QFont.Bold))
                        p.setPen(QtGui.QColor(0, 0, 0, 230))
                        p.drawText(x + 2, y + 2, text)
                        p.setPen(QtGui.QColor(255, 255, 0, 245))
                        p.drawText(x, y, text)
                self._draw_measurements(p, W, H)
            finally:
                p.end()
            return result
        except Exception:
            return pix

    def get_print_pixmap(self, include_info=True):
        if self._src_pixmap is None:
            return None
        key = (include_info, self._cache_final_key,
               self._font_scale, self._index)
        if self._print_cache is not None and self._print_cache_key == key:
            return self._print_cache
        try:
            pix = self._render_annotations(self._src_pixmap,
                                            show_info=include_info)
        except Exception:
            pix = self._src_pixmap.copy()
        self._print_cache = pix
        self._print_cache_key = key
        return pix