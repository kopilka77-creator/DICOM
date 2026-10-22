# -*- coding: utf-8 -*-
import io
import os
import zipfile

import pydicom


def _read_bytes(data):
    ds = pydicom.dcmread(io.BytesIO(data))
    return ds, ds.pixel_array


def _is_decompress_error(ex):
    s = str(ex).lower()
    return ("decompress" in s or "plugin" in s or
            "transfer syntax" in s or "pixel data" in s)


def read_dicom_path(path):
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            last_err = None
            for name in zf.namelist():
                if name.endswith("/"): continue
                try:
                    ds, arr = _read_bytes(zf.read(name))
                    if arr is not None: return ds, arr
                except Exception as ex:
                    last_err = ex
                    continue
            if last_err is not None and _is_decompress_error(last_err):
                raise last_err
        raise ValueError("DICOM внутри ZIP не найден")
    with open(path, "rb") as f:
        return _read_bytes(f.read())


def _sort_key(item):
    fp, ds = item
    pos = getattr(ds, "ImagePositionPatient", None)
    if pos is not None and len(pos) >= 3:
        try: return (0, float(pos[2]))
        except Exception: pass
    ins = getattr(ds, "InstanceNumber", None)
    if ins is not None:
        try: return (1, float(ins))
        except Exception: pass
    return (2, fp)


def read_dicom_folder(path):
    files = []
    for root, _, names in os.walk(path):
        for name in names:
            if name.startswith("."): continue
            fp = os.path.join(root, name)
            try:
                ds = pydicom.dcmread(fp, stop_before_pixels=True, force=True)
                if not hasattr(ds, "SOPClassUID"): continue
                files.append((fp, ds))
            except Exception: continue
    if not files:
        raise ValueError("В папке нет DICOM-файлов")
    groups = {}
    for fp, ds in files:
        key = (str(getattr(ds, "StudyInstanceUID", "")),
               str(getattr(ds, "SeriesInstanceUID", "")))
        groups.setdefault(key, []).append((fp, ds))
    series_files = max(groups.values(), key=len)
    series_files.sort(key=_sort_key)
    series = []
    last_err = None
    for fp, _ in series_files:
        try:
            ds = pydicom.dcmread(fp, force=True)
            arr = ds.pixel_array
        except Exception as ex:
            last_err = ex
            continue
        try: nf = int(str(getattr(ds, "NumberOfFrames", 1)) or 1)
        except Exception: nf = 1
        if nf > 1 and arr.ndim >= 3:
            for i in range(arr.shape[0]):
                series.append((ds, arr[i]))
        else:
            series.append((ds, arr))
    if not series:
        if last_err is not None and _is_decompress_error(last_err):
            raise last_err
        raise ValueError("Не удалось прочитать пиксельные данные")
    return series


def _tags_for_dataset(ds):
    rows = []
    for elem in ds:
        tag_str = "(%04X,%04X)" % (elem.tag.group, elem.tag.element)
        try: name = str(elem.description() or "")
        except Exception: name = ""
        if not name: name = str(getattr(elem, "keyword", ""))
        vr = str(elem.VR or "")
        try:
            if vr in ("OB", "OW", "OF", "UN") or isinstance(
                    elem.value, (bytes, bytearray)):
                n = len(elem.value) if hasattr(elem.value, "__len__") else 0
                val = "<binary, %d bytes>" % n
            elif vr == "SQ":
                val = "<sequence, %d item(s)>" % len(elem.value)
            else:
                val = str(elem.value)
        except Exception:
            val = "<...>"
        if len(val) > 200: val = val[:200] + "..."
        rows.append((tag_str, name, vr, val))
    return rows