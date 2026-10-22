# -*- coding: utf-8 -*-
try:
    from pynetdicom import AE, evt
    from pynetdicom.sop_class import (
        BasicGrayscalePrintManagementMeta,
        BasicFilmSession, BasicFilmBox, Printer, PrinterInstance,
    )
    from pydicom.dataset import Dataset as DsDataset
    from pydicom.uid import generate_uid
    HAS_PYNETDICOM = True
except Exception:
    HAS_PYNETDICOM = False
    AE = evt = None
    BasicGrayscalePrintManagementMeta = None
    BasicFilmSession = BasicFilmBox = Printer = PrinterInstance = None
    DsDataset = None
    generate_uid = None

FILM_SIZES = ["8x10", "10x12", "11x14", "14x14", "14x17", "A4", "A3"]
ORIENTATIONS = ["PORTRAIT", "LANDSCAPE"]
FILM_TYPES = ["CLEAR FILM", "BLUE FILM", "PAPER",
              "MAMMO CLEAR FILM", "MAMMO BLUE FILM"]
FILM_SIZE_TO_INCHES = {
    "8x10": (8.0, 10.0), "10x12": (10.0, 12.0),
    "11x14": (11.0, 14.0), "14x14": (14.0, 14.0),
    "14x17": (14.0, 17.0), "A4": (8.27, 11.69), "A3": (11.69, 16.54),
}
FILM_SIZE_TO_DICOM_ID = {
    "8x10": "8_10", "10x12": "10_12", "11x14": "11_14",
    "14x14": "14_14", "14x17": "14_17", "A4": "A4", "A3": "A3",
}
CT_PRESETS = [
    ("Auto (из тегов / авто)", None),
    ("CT Lung", (-600, 1500)), ("CT Mediastinum", (50, 350)),
    ("CT Bone", (400, 1800)), ("CT Brain", (40, 80)),
    ("CT Soft Tissue", (40, 400)), ("CT Abdomen", (60, 400)),
    ("CT Liver", (30, 120)), ("CT Angio", (300, 600)),
]
FONT_SCALES = [
    (0.5, "50%"), (0.75, "75%"), (1.0, "100% (норма)"),
    (1.25, "125%"), (1.5, "150%"), (2.0, "200%"), (3.0, "300%"),
]
TEXT_SIZE_CHOICES = [
    ("Маленький (x0.75)", 0.75), ("Обычный (x1.0)", 1.0),
    ("Крупный (x1.5)", 1.5), ("Очень крупный (x2.0)", 2.0),
    ("Огромный (x3.0)", 3.0),
]
DICOM_MIME = "application/x-dicom-viewport"
DECOMPRESS_HINT = (
    "Не удалось распаковать сжатые пиксельные данные.\n\n"
    "Установите плагин декодирования:\n\n"
    "    pip install pylibjpeg pylibjpeg-libjpeg pylibjpeg-openjpeg\n\n"
    "или:\n\n"
    "    pip install python-gdcm\n\n"
    "После установки перезапустите программу."
)