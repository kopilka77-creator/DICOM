# -*- coding: utf-8 -*-
import os
import tempfile
from PyQt5 import QtCore, QtWidgets

from .constants import (
    HAS_PYNETDICOM, AE, DsDataset,
)


class PacsWorker(QtCore.QThread):
    log = QtCore.pyqtSignal(str)
    find_done = QtCore.pyqtSignal(list)
    get_done = QtCore.pyqtSignal(list)
    failed = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int, int)

    def __init__(self, pacs_ip, pacs_port, pacs_aet, local_aet,
                 query_ds, action="find", retrieve_ds=None,
                 save_dir=None, parent=None):
        super().__init__(parent)
        self.pacs_ip = pacs_ip; self.pacs_port = int(pacs_port)
        self.pacs_aet = pacs_aet; self.local_aet = local_aet
        self.query_ds = query_ds; self.action = action
        self.retrieve_ds = retrieve_ds; self.save_dir = save_dir
        self._cancelled = False

    def cancel(self): self._cancelled = True

    def run(self):
        if not HAS_PYNETDICOM:
            self.failed.emit("pynetdicom не установлен.")
            return
        from pynetdicom.sop_class import (
            StudyRootQueryRetrieveInformationModelFind,
            StudyRootQueryRetrieveInformationModelGet,
        )
        from pynetdicom.pdu_primitives import SCP_SCU_RoleSelectionNegotiation
        from pynetdicom import StoragePresentationContexts
        try:
            if self.action == "find":
                self._do_find(StudyRootQueryRetrieveInformationModelFind)
            else:
                self._do_get(StudyRootQueryRetrieveInformationModelGet,
                             SCP_SCU_RoleSelectionNegotiation,
                             StoragePresentationContexts)
        except Exception as ex:
            self.failed.emit("Ошибка: %s" % ex)

    def _do_find(self, find_sop_class):
        ae = AE(ae_title=self.local_aet.encode("ascii", "ignore")[:16])
        ae.add_requested_context(find_sop_class)
        self.log.emit("Подключение к PACS %s:%d..."
                      % (self.pacs_ip, self.pacs_port))
        assoc = ae.associate(self.pacs_ip, self.pacs_port,
                             ae_title=self.pacs_aet.encode("ascii", "ignore")[:16])
        if not assoc or not assoc.is_established:
            self.failed.emit("Не удалось установить ассоциацию с PACS.\n"
                             "Проверьте IP, PORT, AET.")
            return
        self.log.emit("✅ Ассоциация установлена. Отправка C-FIND...")
        results = []
        try:
            responses = assoc.send_c_find(self.query_ds, find_sop_class)
            for status, identifier in responses:
                if self._cancelled:
                    assoc.abort(); return
                if status is None:
                    self.failed.emit("Таймаут C-FIND."); return
                if status.Status in (0xFF00, 0xFF01):
                    if identifier:
                        results.append(identifier)
                        self.log.emit("  %s / %s"
                                      % (getattr(identifier, "PatientName", "?"),
                                         getattr(identifier, "StudyDate", "?")))
                elif status.Status == 0x0000:
                    self.log.emit("✅ C-FIND завершён. Найдено: %d" % len(results))
                else:
                    self.log.emit("⚠ C-FIND статус: 0x%04X" % status.Status)
        finally:
            try: assoc.release()
            except Exception: pass
        self.find_done.emit(results)

    def _do_get(self, get_sop_class, role_cls, storage_ctxs):
        out_dir = self.save_dir or tempfile.mkdtemp(prefix="pacs_")
        os.makedirs(out_dir, exist_ok=True)
        ae = AE(ae_title=self.local_aet.encode("ascii", "ignore")[:16])
        ae.add_requested_context(get_sop_class)
        for cx in storage_ctxs:
            ae.add_requested_context(cx.abstract_syntax, cx.transfer_syntax)
        ext_neg = []
        for cx in storage_ctxs:
            role = role_cls()
            role.sop_class_uid = cx.abstract_syntax
            role.scu_role = False
            role.scp_role = True
            ext_neg.append(role)
        saved = []
        counter = {"n": 0}

        def on_c_store(ds, context, info):
            if self._cancelled: return 0xA702
            try:
                meta = DsDataset()
                meta.MediaStorageSOPClassUID = ds.SOPClassUID
                meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
                meta.TransferSyntaxUID = context.transfer_syntax
                from pynetdicom import (
                    PYNETDICOM_IMPLEMENTATION_UID,
                    PYNETDICOM_IMPLEMENTATION_VERSION,
                )
                meta.ImplementationClassUID = PYNETDICOM_IMPLEMENTATION_UID
                meta.ImplementationVersionName = PYNETDICOM_IMPLEMENTATION_VERSION
                ds.file_meta = meta
                ds.is_little_endian = context.transfer_syntax.is_little_endian
                ds.is_implicit_VR = context.transfer_syntax.is_implicit_VR
                fpath = os.path.join(out_dir, "%s.dcm" % ds.SOPInstanceUID)
                ds.save_as(fpath, write_like_original=False)
                saved.append(fpath)
                counter["n"] += 1
                self.progress.emit(counter["n"], 0)
                return 0x0000
            except Exception as ex:
                self.log.emit("  ❌ C-STORE: %s" % ex)
                return 0xC000

        ae.on_c_store = on_c_store
        self.log.emit("Подключение к PACS для C-GET...")
        assoc = ae.associate(self.pacs_ip, self.pacs_port,
                             ae_title=self.pacs_aet.encode("ascii", "ignore")[:16],
                             ext_neg=ext_neg)
        if not assoc or not assoc.is_established:
            self.failed.emit("C-GET: не удалось установить ассоциацию.")
            return
        self.log.emit("✅ C-GET: ассоциация установлена.")
        try:
            responses = assoc.send_c_get(self.retrieve_ds, get_sop_class)
            for status, _id in responses:
                if self._cancelled:
                    assoc.abort(); break
                if status is None:
                    self.failed.emit("Таймаут C-GET."); break
                if hasattr(status, "NumberOfRemainingSuboperations"):
                    rem = status.NumberOfRemainingSuboperations or 0
                    done = status.NumberOfCompletedSuboperations or 0
                    failed_sub = status.NumberOfFailedSuboperations or 0
                    total = done + rem + failed_sub
                    if total:
                        self.progress.emit(done, total)
                if status.Status == 0x0000:
                    self.log.emit("✅ C-GET завершён: %d файлов" % len(saved))
                elif status.Status in (0xFF00, 0xFF01):
                    pass
                elif status.Status == 0xB000:
                    self.log.emit("⚠ C-GET: часть файлов с ошибками")
                else:
                    self.log.emit("⚠ C-GET статус: 0x%04X" % status.Status)
        finally:
            try: assoc.release()
            except Exception: pass
        self.get_done.emit(saved)


class PacsTab(QtWidgets.QWidget):
    load_requested = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12); v.setSpacing(8)

        g = QtWidgets.QGroupBox("PACS сервер")
        f = QtWidgets.QFormLayout(g)
        self.pacs_ip = QtWidgets.QLineEdit("127.0.0.1")
        self.pacs_port = QtWidgets.QSpinBox()
        self.pacs_port.setRange(1, 65535); self.pacs_port.setValue(11112)
        self.pacs_aet = QtWidgets.QLineEdit("PACS")
        self.local_aet = QtWidgets.QLineEdit("DICOMVIEWER")
        f.addRow("IP:", self.pacs_ip)
        f.addRow("PORT:", self.pacs_port)
        f.addRow("PACS AET:", self.pacs_aet)
        f.addRow("Мой AET:", self.local_aet)
        v.addWidget(g)

        g2 = QtWidgets.QGroupBox("Поиск (C-FIND)")
        f2 = QtWidgets.QFormLayout(g2)
        self.pat_id = QtWidgets.QLineEdit()
        self.pat_name = QtWidgets.QLineEdit()
        self.study_date = QtWidgets.QLineEdit()
        self.modality = QtWidgets.QLineEdit()
        for lbl, w, tip in (("Patient ID:", self.pat_id, "Пусто = любой"),
                            ("Patient Name:", self.pat_name, "IVAN*"),
                            ("Study Date:", self.study_date, "YYYYMMDD"),
                            ("Modality:", self.modality, "CT, MR, US")):
            w.setPlaceholderText(tip)
            f2.addRow(lbl, w)
        v.addWidget(g2)

        h = QtWidgets.QHBoxLayout()
        self.find_btn = QtWidgets.QPushButton("🔍 Поиск")
        self.get_btn = QtWidgets.QPushButton("⬇ Загрузить выбранное")
        self.get_btn.setEnabled(False)
        self.cancel_btn = QtWidgets.QPushButton("Отмена")
        self.cancel_btn.setEnabled(False)
        h.addWidget(self.find_btn); h.addWidget(self.get_btn)
        h.addWidget(self.cancel_btn); h.addStretch(1)
        v.addLayout(h)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        v.addWidget(self.progress)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet(
            "QPlainTextEdit { background:#1a1a1a; color:#c0ffc0; "
            "font-family:Consolas; font-size:9pt; border:1px solid #3c3c3c; }")
        v.addWidget(self.log, 1)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Patient", "ID", "Date", "Modality", "Description", "Study UID"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table, 1)

        self._worker = None
        self._studies = []
        self._pending = []
        self._got_files = []

        self.find_btn.clicked.connect(self._do_find)
        self.get_btn.clicked.connect(self._do_get)
        self.cancel_btn.clicked.connect(self._cancel)

    def _build_query(self):
        ds = DsDataset()
        ds.QueryRetrieveLevel = "STUDY"
        ds.PatientID = self.pat_id.text().strip() or ""
        ds.PatientName = self.pat_name.text().strip() or ""
        ds.StudyDate = self.study_date.text().strip() or ""
        ds.ModalitiesInStudy = self.modality.text().strip() or ""
        ds.StudyInstanceUID = ""
        ds.StudyDescription = ""
        return ds

    def _do_find(self):
        if self._worker is not None: return
        self.log.clear()
        self.table.setRowCount(0)
        self._studies = []
        self.get_btn.setEnabled(False)
        self.progress.setVisible(False)
        self._worker = PacsWorker(
            self.pacs_ip.text().strip(), self.pacs_port.value(),
            self.pacs_aet.text().strip(), self.local_aet.text().strip(),
            self._build_query(), action="find", parent=self)
        self._worker.log.connect(self.log.appendPlainText)
        self._worker.failed.connect(self._on_fail)
        self._worker.find_done.connect(self._on_find_done)
        self._worker.finished.connect(self._cleanup_worker)
        self.find_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self._worker.start()

    def _on_find_done(self, studies):
        self._studies = studies
        self.table.setRowCount(len(studies))
        for i, ds in enumerate(studies):
            for col, attr in enumerate(
                    ("PatientName", "PatientID", "StudyDate",
                     "ModalitiesInStudy", "StudyDescription",
                     "StudyInstanceUID")):
                self.table.setItem(i, col,
                    QtWidgets.QTableWidgetItem(str(getattr(ds, attr, ""))))
        self.table.resizeColumnsToContents()
        self.get_btn.setEnabled(len(studies) > 0)

    def _do_get(self):
        rows = sorted(set(i.row() for i in self.table.selectedIndexes()))
        if not rows:
            QtWidgets.QMessageBox.information(self, "PACS",
                "Выберите исследование в таблице.")
            return
        self._pending = [self._studies[r] for r in rows]
        self._got_files = []
        self._get_next()

    def _get_next(self):
        if not self._pending:
            self._on_all_get_done(); return
        study = self._pending.pop(0)
        uid = str(getattr(study, "StudyInstanceUID", ""))
        ds = DsDataset()
        ds.QueryRetrieveLevel = "STUDY"
        ds.StudyInstanceUID = uid
        save_dir = tempfile.mkdtemp(prefix="pacs_%s_" % uid[:8])
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._worker = PacsWorker(
            self.pacs_ip.text().strip(), self.pacs_port.value(),
            self.pacs_aet.text().strip(), self.local_aet.text().strip(),
            None, action="get", retrieve_ds=ds, save_dir=save_dir,
            parent=self)
        self._worker.log.connect(self.log.appendPlainText)
        self._worker.failed.connect(self._on_fail)
        self._worker.get_done.connect(self._on_one_get_done)
        self._worker.finished.connect(self._cleanup_worker_get)
        self.get_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self._worker.start()

    def _on_one_get_done(self, files):
        self._got_files.extend(files)
        self._get_next()

    def _cleanup_worker_get(self):
        self._worker = None
        self.progress.setVisible(False)
        self.cancel_btn.setEnabled(False)

    def _on_all_get_done(self):
        self.get_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setVisible(False)
        if self._got_files:
            self.log.appendPlainText("=" * 40)
            self.log.appendPlainText(
                "✅ Загружено файлов: %d" % len(self._got_files))
            self.load_requested.emit(self._got_files)
        else:
            self.log.appendPlainText(
                "⚠ Файлы не получены. Возможно, PACS не поддерживает C-GET.")

    def _cancel(self):
        if self._worker is not None:
            self._worker.cancel()
            self.log.appendPlainText("⏹ Отмена запроса...")

    def _on_fail(self, msg):
        self.log.appendPlainText("❌ " + msg)
        QtWidgets.QMessageBox.critical(self, "PACS", msg)

    def _cleanup_worker(self):
        self._worker = None
        self.find_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)