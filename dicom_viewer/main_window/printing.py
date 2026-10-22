# -*- coding: utf-8 -*-
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from PyQt5 import QtPrintSupport
    _QPrinter = QtPrintSupport.QPrinter
    _QPrinterInfo = QtPrintSupport.QPrinterInfo
    _QPrintDialog = QtPrintSupport.QPrintDialog
except ImportError:
    _QPrinter = _QPrinterInfo = _QPrintDialog = None
try:
    from PyQt5.QtGui import QPageSize as _QPageSize
except Exception:
    _QPageSize = None

from ..constants import HAS_PYNETDICOM, FILM_SIZE_TO_INCHES
from ..print_scu import (DicomPrintWorker, DicomPrintProgressDialog)


class _PrintingMixin:
    def _apply_paper_settings(self, printer, params):
        film = params.get("film_size", "14x17")
        orientation = params.get("orientation", "PORTRAIT")
        short_in, long_in = FILM_SIZE_TO_INCHES.get(film, (14.0, 17.0))
        if orientation == "PORTRAIT":
            page_w, page_h = short_in, long_in
        else:
            page_w, page_h = long_in, short_in
        applied = False
        if _QPageSize is not None:
            try:
                ps = _QPageSize(QtCore.QSizeF(page_w, page_h),
                                _QPageSize.Inch,
                                "Film %s" % film,
                                _QPageSize.ExactMatch)
                printer.setPageSize(ps)
                applied = True
            except Exception:
                applied = False
        if not applied:
            try:
                printer.setPaperSize(QtCore.QSizeF(page_w, page_h),
                                     _QPrinter.Inch)
            except Exception:
                pass
        try:
            if page_w > page_h:
                printer.setOrientation(_QPrinter.Landscape)
            else:
                printer.setOrientation(_QPrinter.Portrait)
        except Exception:
            pass

    def _format_dicom_date(self, s):
        s = str(s or "").strip()
        if len(s) == 8 and s.isdigit():
            return "%s-%s-%s" % (s[:4], s[4:6], s[6:8])
        return s

    def _draw_sheet_header(self, painter, rect):
        ds = None
        for vp in self.viewports.all_viewports:
            if vp._series:
                ds = vp._series[vp._index][0]
                break
        if ds is None:
            return
        try:
            patient = str(getattr(ds, "PatientName", "") or "").strip() or "—"
            pid = str(getattr(ds, "PatientID", "") or "").strip() or "—"
            birth = self._format_dicom_date(
                getattr(ds, "PatientBirthDate", "")) or "—"
            modality = str(getattr(ds, "Modality", "") or "").strip() or "—"
            study_date = self._format_dicom_date(
                getattr(ds, "StudyDate", "")) or "—"
            accession = str(
                getattr(ds, "AccessionNumber", "") or "").strip() or "—"
            study_desc = str(
                getattr(ds, "StudyDescription", "") or "").strip()
        except Exception:
            return
        pt = max(7, int(rect.height() * 0.28))
        painter.setFont(QtGui.QFont("Arial", pt))
        fm = painter.fontMetrics()
        painter.setPen(QtGui.QColor(0, 0, 0))
        lh = fm.height()
        y0 = rect.y() + fm.ascent() + 2
        left = ["Patient: %s" % patient,
                "ID: %s    DOB: %s" % (pid, birth)]
        if study_desc:
            left.append("Study: %s" % study_desc)
        right = ["Modality: %s" % modality,
                 "Study Date: %s" % study_date,
                 "Accession: %s" % accession]
        for i, line in enumerate(left):
            painter.drawText(rect.x() + 4, y0 + i * lh, line)
        for i, line in enumerate(right):
            w = fm.boundingRect(line).width()
            painter.drawText(rect.right() - w - 4, y0 + i * lh, line)

    def _draw_sheet_footer(self, painter, rect, params):
        import datetime as _dt
        pt = max(7, int(rect.height() * 0.3))
        painter.setFont(QtGui.QFont("Arial", pt))
        fm = painter.fontMetrics()
        painter.setPen(QtGui.QColor(0, 0, 0))
        lh = fm.height()
        y0 = rect.y() + fm.ascent() + 2
        ip = params.get("ip") or "—"
        aet = params.get("aet") or "—"
        port = params.get("port", 0)
        film = params.get("film_size") or "—"
        orient = params.get("orientation") or "—"
        ftype = params.get("film_type") or "—"
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        left = ["DICOM Printer:  %s   AET: %s   Port: %s"
                % (ip, aet, port),
                "Film:  %s   Orientation: %s   Type: %s"
                % (film, orient, ftype)]
        right = ["Printed: %s" % ts]
        for i, line in enumerate(left):
            painter.drawText(rect.x() + 4, y0 + i * lh, line)
        for i, line in enumerate(right):
            w = fm.boundingRect(line).width()
            painter.drawText(rect.right() - w - 4, y0 + i * lh, line)

    def _draw_sheet(self, painter, rect, params):
        if rect is None or rect.width() <= 0 or rect.height() <= 0:
            return
        painter.save()
        try:
            painter.fillRect(rect, QtGui.QColor(255, 255, 255))
        except Exception:
            pass
        painter.restore()
        show_tags = params.get("print_tags", True)
        show_footer = params.get("print_footer", True)
        margin = int(min(rect.width(), rect.height()) * 0.015)
        inner = rect.adjusted(margin, margin, -margin, -margin)
        if inner.width() <= 0 or inner.height() <= 0:
            return
        header_h = int(inner.height() * 0.10) if show_tags else 0
        footer_h = int(inner.height() * 0.075) if show_footer else 0
        header_rect = QtCore.QRect(inner.x(), inner.y(),
                                   inner.width(), header_h)
        footer_rect = QtCore.QRect(inner.x(),
                                   inner.y() + inner.height() - footer_h,
                                   inner.width(), footer_h)
        grid_rect = QtCore.QRect(inner.x(), inner.y() + header_h,
                                 inner.width(),
                                 inner.height() - header_h - footer_h)
        if show_tags:
            try:
                self._draw_sheet_header(painter, header_rect)
            except Exception:
                pass
        self._draw_sheet_grid(painter, grid_rect, params)
        if show_footer:
            try:
                self._draw_sheet_footer(painter, footer_rect, params)
            except Exception:
                pass

    def _draw_sheet_grid(self, painter, rect, params):
        if rect is None or rect.width() <= 0 or rect.height() <= 0:
            return
        mode = 1
        for m, b in self.panel._layout_btns:
            if b.isChecked():
                mode = m
                break
        vps = self.viewports.all_viewports
        if mode == 1:
            cells = [(0, 0, 1, 1, vps[0])]
        elif mode == 2:
            cells = [(0, 0, 1, 2, vps[0]), (0, 1, 1, 2, vps[1])]
        else:
            cells = [(0, 0, 2, 2, vps[0]), (0, 1, 2, 2, vps[1]),
                     (1, 0, 2, 2, vps[2]), (1, 1, 2, 2, vps[3])]
        margin = int(min(rect.width(), rect.height()) * 0.02)
        inner = rect.adjusted(margin, margin, -margin, -margin)
        if inner.width() <= 0 or inner.height() <= 0:
            return
        cw, ch = inner.width(), inner.height()
        show_overlays = params.get("print_overlays", True)
        no_border = params.get("no_border", False)
        for (r, c, rows, cols, vp) in cells:
            cell_x = inner.x() + (c * cw) // cols
            cell_y = inner.y() + (r * ch) // rows
            cell_w = cw // cols
            cell_h = ch // rows
            cell_rect = QtCore.QRect(cell_x, cell_y, cell_w, cell_h)
            if not no_border:
                try:
                    painter.setPen(
                        QtGui.QPen(QtGui.QColor(180, 180, 180), 1))
                    painter.drawRect(cell_rect.adjusted(1, 1, -2, -2))
                except Exception:
                    pass
            if vp is None or not vp._series:
                continue
            try:
                pix = vp.get_print_pixmap(include_info=show_overlays)
            except Exception:
                continue
            if pix is None or pix.isNull():
                continue
            draw_pix = pix
            cell_landscape = cell_w > cell_h
            img_landscape = pix.width() > pix.height()
            if cell_landscape != img_landscape:
                try:
                    draw_pix = pix.transformed(
                        QtGui.QTransform().rotate(90))
                except Exception:
                    draw_pix = pix
            pad = max(2, margin // 2)
            target_box = cell_rect.adjusted(pad, pad, -pad, -pad)
            if target_box.width() <= 0 or target_box.height() <= 0:
                continue
            size = draw_pix.size()
            size.scale(target_box.size(), QtCore.Qt.KeepAspectRatio)
            if size.width() <= 0 or size.height() <= 0:
                continue
            dst = QtCore.QRect(
                target_box.x() + (target_box.width() - size.width()) // 2,
                target_box.y() + (target_box.height() - size.height()) // 2,
                size.width(), size.height())
            try:
                painter.drawPixmap(dst, draw_pix)
            except Exception:
                pass

    def _print_regular(self):
        if _QPrinter is None:
            QtWidgets.QMessageBox.warning(
                self, "Печать", "QtPrintSupport недоступен.")
            return
        if not self._any_series():
            QtWidgets.QMessageBox.warning(
                self, "Печать", "Нет изображений.")
            return
        if _QPrinterInfo is not None:
            try:
                if not _QPrinterInfo.availablePrinters():
                    QtWidgets.QMessageBox.warning(
                        self, "Печать", "В системе нет принтеров.")
                    return
            except Exception:
                pass
        try:
            printer = _QPrinter(_QPrinter.PrinterResolution)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Печать", str(ex))
            return
        try:
            if not printer.isValid():
                QtWidgets.QMessageBox.warning(
                    self, "Печать", "Принтер не найден.")
                return
        except Exception:
            pass
        params = self.panel.collect()
        try:
            printer.setDocName("DICOM sheet")
        except Exception:
            pass
        self._apply_paper_settings(printer, params)
        if _QPrintDialog is None:
            return
        try:
            dlg = _QPrintDialog(printer, self)
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Печать", str(ex))
            return
        painter = QtGui.QPainter()
        started = False
        try:
            started = bool(painter.begin(printer))
            if not started:
                QtWidgets.QMessageBox.warning(
                    self, "Печать", "Не удалось начать печать.")
                return
            self._draw_sheet(painter, painter.viewport(), params)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Печать", str(ex))
            return
        finally:
            if started:
                try:
                    painter.end()
                except Exception:
                    pass
        self.statusBar().showMessage("Отправлено на Windows-принтер")

    def _save_as_pdf(self):
        if _QPrinter is None:
            QtWidgets.QMessageBox.warning(
                self, "PDF", "QtPrintSupport недоступен.")
            return
        if not self._any_series():
            QtWidgets.QMessageBox.warning(
                self, "PDF", "Нет изображений.")
            return
        try:
            dlg = QtWidgets.QFileDialog(self, "Сохранить в PDF")
            dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
            dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
            dlg.setDefaultSuffix("pdf")
            dlg.setNameFilter("PDF (*.pdf)")
            dlg.selectFile("dicom_sheet.pdf")
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            files = dlg.selectedFiles()
            if not files:
                return
            path = files[0]
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "PDF", str(ex))
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        params = self.panel.collect()
        try:
            printer = _QPrinter(_QPrinter.PrinterResolution)
            printer.setOutputFormat(_QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            self._apply_paper_settings(printer, params)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "PDF", str(ex))
            return
        painter = QtGui.QPainter()
        started = False
        try:
            started = bool(painter.begin(printer))
            if not started:
                QtWidgets.QMessageBox.warning(
                    self, "PDF", "Не удалось создать PDF.")
                return
            self._draw_sheet(painter, painter.viewport(), params)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "PDF", str(ex))
            return
        finally:
            if started:
                try:
                    painter.end()
                except Exception:
                    pass
        self.statusBar().showMessage("PDF: %s" % path)

    def _print_dicom(self):
        if not HAS_PYNETDICOM:
            QtWidgets.QMessageBox.warning(
                self, "DICOM-печать",
                "Библиотека pynetdicom не установлена.\n\n"
                "    pip install pynetdicom pydicom\n\n"
                "и перезапустите программу.")
            return
        vp = self._active_vp()
        if vp is None or not vp._series:
            QtWidgets.QMessageBox.warning(
                self, "DICOM-печать", "Нет активного снимка.")
            return
        params = self.panel.collect()
        try:
            pix = vp.get_print_pixmap(
                include_info=params.get("print_overlays", True))
            if pix is None or pix.isNull():
                QtWidgets.QMessageBox.warning(
                    self, "DICOM-печать", "Пустое изображение.")
                return
            img = pix.toImage().convertToFormat(
                QtGui.QImage.Format_Grayscale8)
            width, height = img.width(), img.height()
            ptr = img.bits()
            ptr.setsize(img.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape(
                (height, width)).copy()
        except Exception as ex:
            QtWidgets.QMessageBox.critical(
                self, "DICOM-печать", "Ошибка подготовки:\n%s" % ex)
            return
        dlg = DicomPrintProgressDialog(self)
        worker = DicomPrintWorker(
            params["ip"], params["port"], params["aet"],
            params, arr, width, height, parent=self)
        worker.step.connect(dlg.on_step)
        worker.finished_ok.connect(dlg.on_ok)
        worker.failed.connect(dlg.on_fail)
        worker.finished.connect(worker.deleteLater)
        dlg._add("Параметры печати:", "#a0a0a0")
        for label, val in (
                ("IP", "%s:%d" % (params["ip"], params["port"])),
                ("AET", params["aet"]),
                ("Плёнка", "%s / %s / %s" % (
                    params.get("film_size", "—"),
                    params.get("orientation", "—"),
                    params.get("film_type", "—"))),
                ("Размер", "%dx%d px" % (width, height))):
            dlg._add("   %s: %s" % (label, val), "#a0a0a0")
        dlg._add("")
        worker.start()
        dlg.exec_()
        if dlg._ok:
            self.statusBar().showMessage(
                "DICOM-печать: задание отправлено")