# -*- coding: utf-8 -*-
import socket
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui

from .constants import (
    HAS_PYNETDICOM, AE, evt,
    BasicGrayscalePrintManagementMeta,
    BasicFilmSession, BasicFilmBox, Printer, PrinterInstance,
    DsDataset, generate_uid, FILM_SIZE_TO_DICOM_ID,
)


def test_connection(ip, port, aet):
    """Проверка TCP + C-ECHO + N-GET Printer."""
    if not HAS_PYNETDICOM:
        return (False, "pynetdicom не установлен.")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip, int(port)))
        s.close()
    except Exception as ex:
        return (False, "TCP %s:%s — нет соединения:\n%s" % (ip, port, ex))

    ae = AE(ae_title=b"PYDICOM_SCU")
    ae.add_requested_context(BasicGrayscalePrintManagementMeta)
    from pynetdicom.sop_class import Verification
    ae.add_requested_context(Verification)
    assoc = None
    try:
        assoc = ae.associate(ip, int(port),
                             ae_title=aet.encode("ascii", "ignore"))
        if not assoc or not assoc.is_established:
            return (False, "DICOM-ассоциация НЕ установлена.\n"
                           "Проверьте AE Title '%s'." % aet)
        lines = ["✅ DICOM-ассоциация установлена", ""]
        try:
            st = assoc.send_c_echo()
            if st and st.Status == 0x0000:
                lines.append("✅ C-ECHO — принтер отвечает")
            else:
                lines.append("⚠ C-ECHO: %s" % getattr(st, "Status", "?"))
        except Exception as ex:
            lines.append("⚠ C-ECHO: %s" % ex)
        try:
            st, attr = assoc.send_n_get(
                [0x21100010, 0x21100020],
                Printer, PrinterInstance,
                meta_uid=BasicGrayscalePrintManagementMeta)
            if st and st.Status == 0x0000:
                s = str(getattr(attr, "PrinterStatus", "UNKNOWN"))
                info = str(getattr(attr, "PrinterStatusInfo", "") or "")
                if s == "NORMAL":
                    lines.append("✅ Статус принтера: NORMAL")
                else:
                    lines.append("⚠ Статус: %s (%s)" % (s, info))
            else:
                lines.append("⚠ N-GET: %s" % getattr(st, "Status", "?"))
        except Exception as ex:
            lines.append("⚠ N-GET: %s" % ex)
        return (True, "\n".join(lines))
    finally:
        try:
            if assoc and assoc.is_established: assoc.release()
        except Exception: pass


class DicomPrintWorker(QtCore.QThread):
    step = QtCore.pyqtSignal(int, str)
    finished_ok = QtCore.pyqtSignal(str)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, ip, port, aet, params, arr, width, height, parent=None):
        super().__init__(parent)
        self.ip = ip; self.port = int(port); self.aet = aet
        self.params = dict(params)
        self.arr = arr; self.width = width; self.height = height

    def run(self):
        assoc = None
        try:
            ae = AE(ae_title=b"PYDICOM_SCU")
            ae.add_requested_context(BasicGrayscalePrintManagementMeta)
            from pynetdicom.sop_class import Verification
            ae.add_requested_context(Verification)

            def _on_n_event(event):
                try:
                    info = getattr(event, "event_information", None)
                    if info is not None:
                        es = getattr(info, "ExecutionStatus", None)
                        if es is not None:
                            self.step.emit(7,
                                "N-EVENT-REPORT ExecutionStatus=%s" % es)
                except Exception: pass
                return 0x0000

            self.step.emit(1, "Установка ассоциации с %s:%d (AET %s)..."
                           % (self.ip, self.port, self.aet))
            assoc = ae.associate(self.ip, self.port,
                                 ae_title=self.aet.encode("ascii", "ignore"),
                                 evt_handlers=[(evt.EVT_N_EVENT_REPORT, _on_n_event)])
            if not assoc or not assoc.is_established:
                self.failed.emit(
                    "Не удалось установить DICOM-ассоциацию.\n"
                    "Проверьте IP, PORT, AET.")
                return
            self.step.emit(1, "✅ Ассоциация установлена")

            self.step.emit(2, "N-GET Printer Status...")
            try:
                st, attr = assoc.send_n_get(
                    [0x21100010, 0x21100020],
                    Printer, PrinterInstance,
                    meta_uid=BasicGrayscalePrintManagementMeta)
                if st and st.Status == 0x0000:
                    s = str(getattr(attr, "PrinterStatus", "UNKNOWN"))
                    info = str(getattr(attr, "PrinterStatusInfo", "") or "")
                    if s == "NORMAL":
                        self.step.emit(2, "✅ Статус: NORMAL")
                    elif s == "WARNING":
                        self.step.emit(2, "⚠ WARNING (%s)" % info)
                    else:
                        self.failed.emit("Принтер не готов: %s (%s)" % (s, info))
                        return
                else:
                    self.step.emit(2, "⚠ N-GET не поддерживается, продолжаем")
            except Exception as ex:
                self.step.emit(2, "⚠ N-GET: %s, продолжаем" % ex)

            self.step.emit(3, "N-CREATE Film Session...")
            session = DsDataset()
            session.NumberOfCopies = "1"
            session.PrintPriority = "HIGH"
            session.MediumType = self.params.get("film_type", "PAPER")
            session.FilmDestination = "MAGAZINE"
            session.FilmSessionLabel = "DICOM_VIEWER"
            session.MemoryAllocation = 1
            session.OwnerID = "DICOM_VIEWER"
            st, film_session = assoc.send_n_create(
                session, BasicFilmSession, generate_uid(),
                meta_uid=BasicGrayscalePrintManagementMeta)
            if not st or st.Status != 0x0000:
                self.failed.emit("N-CREATE Film Session: %s"
                                 % getattr(st, "Status", "?"))
                return
            self.step.emit(3, "✅ Film Session создана")

            self.step.emit(4, "N-CREATE Film Box...")
            box = DsDataset()
            box.ImageDisplayFormat = "STANDARD\\1,1"
            box.FilmOrientation = ("PORTRAIT"
                if self.params.get("orientation") == "PORTRAIT"
                else "LANDSCAPE")
            box.FilmSizeID = FILM_SIZE_TO_DICOM_ID.get(
                self.params.get("film_size", "A4"), "A4")
            box.MagnificationType = "REPLICATE"
            box.SmoothingType = "NORMAL"
            box.Trim = "NO"
            ref = DsDataset()
            ref.ReferencedSOPClassUID = film_session.SOPClassUID
            ref.ReferencedSOPInstanceUID = film_session.SOPInstanceUID
            box.ReferencedFilmSessionSequence = [ref]
            st, film_box = assoc.send_n_create(
                box, BasicFilmBox, generate_uid(),
                meta_uid=BasicGrayscalePrintManagementMeta)
            if not st or st.Status != 0x0000:
                self.failed.emit("N-CREATE Film Box: %s (FilmSizeID=%s)"
                                 % (getattr(st, "Status", "?"), box.FilmSizeID))
                return
            if (not hasattr(film_box, "ReferencedImageBoxSequence")
                    or len(film_box.ReferencedImageBoxSequence) == 0):
                self.failed.emit("Принтер не вернул ReferencedImageBoxSequence.")
                return
            self.step.emit(4, "✅ Film Box создан (%s)" % box.FilmSizeID)

            self.step.emit(5, "N-SET Image Box — %dx%d..."
                           % (self.width, self.height))
            ref_ib = film_box.ReferencedImageBoxSequence[0]
            ib = DsDataset()
            ib.ImagePosition = 1
            ib.BasicGrayscaleImageSequence = [DsDataset()]
            bg = ib.BasicGrayscaleImageSequence[0]
            bg.SamplesPerPixel = 1
            bg.PhotometricInterpretation = "MONOCHROME2"
            bg.Rows = self.height
            bg.Columns = self.width
            bg.BitsAllocated = 8
            bg.BitsStored = 8
            bg.HighBit = 7
            bg.PixelRepresentation = 0
            bg.PixelData = self.arr.tobytes()
            st, _ = assoc.send_n_set(
                ib, ref_ib.ReferencedSOPClassUID,
                ref_ib.ReferencedSOPInstanceUID,
                meta_uid=BasicGrayscalePrintManagementMeta)
            if not st or st.Status != 0x0000:
                self.failed.emit("N-SET Image Box: %s"
                                 % getattr(st, "Status", "?"))
                return
            self.step.emit(5, "✅ Изображение загружено (%d байт)"
                           % len(bg.PixelData))

            self.step.emit(6, "N-ACTION Print...")
            act = DsDataset()
            act.RequestedSOPClassUID = film_box.SOPClassUID
            act.RequestedSOPInstanceUID = film_box.SOPInstanceUID
            st, _ = assoc.send_n_action(
                act, 1, film_box.SOPClassUID, film_box.SOPInstanceUID,
                meta_uid=BasicGrayscalePrintManagementMeta)
            if not st or st.Status != 0x0000:
                self.failed.emit("N-ACTION Print: %s"
                                 % getattr(st, "Status", "?"))
                return
            self.step.emit(6, "✅ Команда печати принята")

            self.step.emit(7, "Release...")
            try: assoc.release()
            except Exception: pass
            assoc = None
            self.finished_ok.emit(
                "Задание отправлено.\n\n"
                "IP: %s:%d\nAET: %s\nFilm: %s / %s / %s\nImage: %dx%d"
                % (self.ip, self.port, self.aet,
                   self.params.get("film_size", "—"),
                   self.params.get("orientation", "—"),
                   self.params.get("film_type", "—"),
                   self.width, self.height))
        except Exception as ex:
            self.failed.emit("Неожиданная ошибка:\n%s" % ex)
        finally:
            try:
                if assoc is not None and assoc.is_established:
                    assoc.release()
            except Exception: pass


class DicomPrintProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Печать на DICOM-принтер")
        self.setModal(True)
        self.resize(620, 480)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16); v.setSpacing(10)
        title = QtWidgets.QLabel("Отправка задания на DICOM-принтер")
        title.setStyleSheet("font-size:12pt; font-weight:600; color:#4a9eff;")
        v.addWidget(title)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 7); self.progress.setValue(0)
        self.progress.setFormat("%v / %m шагов")
        v.addWidget(self.progress)
        self.list = QtWidgets.QListWidget()
        self.list.setStyleSheet(
            "QListWidget { background:#1a1a1a; color:#e0e0e0; "
            "border:1px solid #3c3c3c; border-radius:6px; "
            "font-family:Consolas; font-size:9pt; }"
            "QListWidget::item { padding:4px 6px; }")
        v.addWidget(self.list, 1)
        h = QtWidgets.QHBoxLayout(); h.addStretch(1)
        self.btn_close = QtWidgets.QPushButton("Закрыть")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setMinimumWidth(120)
        h.addWidget(self.btn_close)
        v.addLayout(h)
        self._ok = False

    def _add(self, text, color="#e0e0e0"):
        item = QtWidgets.QListWidgetItem(text)
        item.setForeground(QtGui.QColor(color))
        self.list.addItem(item)
        self.list.scrollToBottom()

    def on_step(self, idx, msg):
        color = "#4aff9e" if msg.startswith("✅") else \
                "#ffb84a" if msg.startswith("⚠") else \
                "#ff6b6b" if msg.startswith("❌") else "#e0e0e0"
        self._add("[%d/7] %s" % (idx, msg), color)
        self.progress.setValue(idx)

    def on_ok(self, msg):
        self._ok = True
        self._add("")
        self._add("✅ ГОТОВО", "#4aff9e")
        for line in msg.splitlines():
            if line.strip(): self._add("   " + line, "#a0ffa0")
        self.progress.setValue(7)
        self.btn_close.setEnabled(True); self.btn_close.setFocus()

    def on_fail(self, msg):
        self._ok = False
        self._add("")
        self._add("❌ ОШИБКА", "#ff6b6b")
        for line in msg.splitlines():
            if line.strip(): self._add("   " + line, "#ffb0b0")
        self.btn_close.setEnabled(True); self.btn_close.setFocus()

    def closeEvent(self, e):
        if not self.btn_close.isEnabled(): e.ignore()
        else: e.accept()