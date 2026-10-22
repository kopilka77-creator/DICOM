# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from ..image_utils import _scalar
from ..dialogs import WindowLevelDialog
from ..print_scu import test_connection


class _ActionsMixin:
    def _set_font_scale(self, mult):
        for m, a in self._font_scale_actions:
            a.setChecked(m == mult)
        for vp in self.viewports.all_viewports:
            vp.set_font_scale(mult)
        self._schedule_preview_refresh(200)
        self.statusBar().showMessage(
            "Размер шрифта аннотаций: %d%%" % int(mult * 100))

    def _auto_wl(self):
        vp = self._active_vp()
        if vp:
            vp.auto_window_level()
            self._update_status_info(vp)
            self._schedule_preview_refresh(200)

    def _adjust_wl(self):
        vp = self._active_vp()
        if vp is None or not vp._series:
            return
        ds, _ = vp._series[vp._index]
        wc = _scalar(getattr(ds, "WindowCenter", None)) or 40.0
        ww = _scalar(getattr(ds, "WindowWidth", None)) or 400.0
        if vp._wl_override is not None:
            wc, ww = vp._wl_override
        WindowLevelDialog(wc, ww, vp, self).exec_()
        self._update_status_info(vp)
        self._schedule_preview_refresh(200)

    def _apply_preset(self, wl):
        vp = self._active_vp()
        if vp:
            vp.apply_preset(wl)
            self._update_status_info(vp)
            self._schedule_preview_refresh(200)

    def _invert(self):
        vp = self._active_vp()
        if vp:
            vp.toggle_invert()
            self._schedule_preview_refresh(200)

    def _reset_view(self):
        vp = self._active_vp()
        if vp:
            vp.reset_view()
            self._update_status_info(vp)
            self._schedule_preview_refresh(200)

    def _zoom_in(self):
        vp = self._active_vp()
        if vp:
            vp.zoom_in()
            self._update_status_info(vp)

    def _zoom_out(self):
        vp = self._active_vp()
        if vp:
            vp.zoom_out()
            self._update_status_info(vp)

    def _zoom_fit(self):
        vp = self._active_vp()
        if vp:
            vp.zoom_fit()
            self._update_status_info(vp)

    def _zoom_1to1(self):
        vp = self._active_vp()
        if vp:
            vp.zoom_1to1()
            self._update_status_info(vp)

    def _toggle_annotations(self, show):
        for vp in self.viewports.all_viewports:
            vp.set_show_annotations(show)
        self._schedule_preview_refresh(200)

    def _toggle_ruler_mode(self, on):
        if on:
            self._act_calib_tb.blockSignals(True)
            self._act_calib_tb.setChecked(False)
            self._act_calib_tb.blockSignals(False)
            for vp in self.viewports.all_viewports:
                vp.set_measure_mode(None)
            vp = self._active_vp()
            if vp is None:
                self._act_ruler_tb.blockSignals(True)
                self._act_ruler_tb.setChecked(False)
                self._act_ruler_tb.blockSignals(False)
                return
            vp.set_measure_mode("ruler")
        else:
            for vp in self.viewports.all_viewports:
                if vp.get_measure_mode() == "ruler":
                    vp.set_measure_mode(None)

    def _toggle_calib_mode(self, on):
        if on:
            self._act_ruler_tb.blockSignals(True)
            self._act_ruler_tb.setChecked(False)
            self._act_ruler_tb.blockSignals(False)
            for vp in self.viewports.all_viewports:
                vp.set_measure_mode(None)
            vp = self._active_vp()
            if vp is None:
                self._act_calib_tb.blockSignals(True)
                self._act_calib_tb.setChecked(False)
                self._act_calib_tb.blockSignals(False)
                return
            vp.set_measure_mode("calibrate")
        else:
            for vp in self.viewports.all_viewports:
                if vp.get_measure_mode() == "calibrate":
                    vp.set_measure_mode(None)

    def _clear_measurements(self):
        vp = self._active_vp()
        if vp:
            vp.clear_measurements()
            self._update_status_info(vp)
            self._schedule_preview_refresh(100)

    def _toggle_text_mode(self, checked):
        vp = self._active_vp()
        if vp is None:
            for a in (getattr(self, "_act_text", None),
                      getattr(self, "_act_text_tb", None)):
                if a is not None:
                    a.blockSignals(True)
                    a.setChecked(False)
                    a.blockSignals(False)
            return
        if vp.is_text_mode() == bool(checked):
            return
        vp.set_text_mode(bool(checked))
        if checked:
            self._act_ruler_tb.blockSignals(True)
            self._act_ruler_tb.setChecked(False)
            self._act_ruler_tb.blockSignals(False)
            self._act_calib_tb.blockSignals(True)
            self._act_calib_tb.setChecked(False)
            self._act_calib_tb.blockSignals(False)

    def _clear_texts_current(self):
        vp = self._active_vp()
        if vp:
            vp.clear_texts_current()
            self._schedule_preview_refresh(100)

    def _clear_texts_all(self):
        vp = self._active_vp()
        if vp:
            vp.clear_texts_all()
            self._schedule_preview_refresh(100)

    def _open_file(self):
        try:
            dlg = QtWidgets.QFileDialog(self, "Открыть DICOM или ZIP")
            dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
            dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
            dlg.setNameFilter(
                "DICOM / ZIP (*.dcm *.dicom *.zip);;All files (*.*)")
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            files = dlg.selectedFiles()
            if files:
                self.viewports.open_in_active(files[0])
                self._update_status_info()
                self._schedule_preview_refresh(200)
        except Exception as ex:
            try:
                QtWidgets.QMessageBox.warning(self, "Файл", str(ex))
            except Exception:
                pass

    def _open_folder(self):
        try:
            dlg = QtWidgets.QFileDialog(self, "Открыть папку с серией")
            dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
            dlg.setFileMode(QtWidgets.QFileDialog.Directory)
            dlg.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
            if dlg.exec_() != QtWidgets.QDialog.Accepted:
                return
            files = dlg.selectedFiles()
            if files:
                self.viewports.open_in_active(files[0])
                self._update_status_info()
                self._schedule_preview_refresh(200)
        except Exception as ex:
            try:
                QtWidgets.QMessageBox.warning(self, "Папка", str(ex))
            except Exception:
                pass

    def _test_dicom_connection(self):
        params = self.panel.collect()
        ok, msg = test_connection(params["ip"], params["port"],
                                  params["aet"])
        if ok:
            QtWidgets.QMessageBox.information(self, "Тест DICOM", msg)
        else:
            QtWidgets.QMessageBox.critical(self, "Тест DICOM", msg)

    def _save_calibration_to_tags(self):
        vp = self._active_vp()
        if vp is None:
            return
        if not hasattr(vp, "save_calibration_to_tags"):
            QtWidgets.QMessageBox.warning(
                self, "Калибровка",
                "Метод save_calibration_to_tags не реализован.")
            return
        ok, msg = vp.save_calibration_to_tags()
        if ok:
            QtWidgets.QMessageBox.information(self, "Калибровка", msg)
        else:
            QtWidgets.QMessageBox.warning(self, "Калибровка", msg)

    def _about(self):
        QtWidgets.QMessageBox.about(
            self, "О программе",
            "DICOM Viewer\n\n"
            "Просмотр DICOM, сетка 1/2/4 (изменяемые размеры),\n"
            "ZIP-архивы, сжатые форматы, теги DICOM,\n"
            "W/L, яркость/контраст, зум, панорама, инверсия,\n"
            "текстовые надписи, калибровка по шару и линейка (мм),\n"
            "печать Windows / PDF / DICOM Print SCU,\n"
            "загрузка с PACS (C-FIND + C-GET).")