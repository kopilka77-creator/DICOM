# -*- coding: utf-8 -*-
import numpy as np


def _scalar(v):
    try: return float(v)
    except (TypeError, ValueError): pass
    try: return float(v[0])
    except Exception: return None


def _to_display_uint8(arr, ds, wc=None, ww=None, invert=False):
    a = arr.astype(np.float32)
    try:
        slope = float(getattr(ds, "RescaleSlope", 1) or 1)
        inter = float(getattr(ds, "RescaleIntercept", 0) or 0)
        if slope != 1.0 or inter != 0.0:
            a = a * slope + inter
    except Exception: pass
    lo = hi = None
    if wc is not None and ww is not None:
        lo = float(wc) - float(ww) / 2.0
        hi = float(wc) + float(ww) / 2.0
    if lo is None:
        wc_ds = _scalar(getattr(ds, "WindowCenter", None))
        ww_ds = _scalar(getattr(ds, "WindowWidth", None))
        if wc_ds is not None and ww_ds is not None:
            lo = wc_ds - ww_ds / 2.0
            hi = wc_ds + ww_ds / 2.0
    if lo is None:
        lo, hi = float(a.min()), float(a.max())
    a = np.clip(a, lo, hi)
    a = (a - lo) / (hi - lo) * 255.0 if hi > lo else np.zeros_like(a)
    if invert:
        a = 255.0 - a
    return a.astype(np.uint8)


def _dicom_pixel_spacing(ds):
    for attr in ("PixelSpacing", "ImagerPixelSpacing",
                 "NominalScannedPixelSpacing"):
        v = getattr(ds, attr, None)
        if v and len(v) >= 2:
            try:
                r = float(v[0]); c = float(v[1])
                if r > 0 and c > 0: return (r + c) / 2.0
            except Exception: pass
    return None