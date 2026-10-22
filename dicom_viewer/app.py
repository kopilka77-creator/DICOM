# -*- coding: utf-8 -*-
import sys
import faulthandler
import traceback
from PyQt5 import QtWidgets

from .theme import apply_modern_style
from .main_window import MainWindow


def run_app():
    try:
        fh = open("crash.log", "w")
        faulthandler.enable(fh)
    except Exception:
        pass

    def _excepthook(et, ev, tb):
        try:
            with open("error.log", "a", encoding="utf-8") as f:
                f.write("\n=== uncaught ===\n")
                traceback.print_exception(et, ev, tb, file=f)
        except Exception:
            pass

    sys.excepthook = _excepthook
    app = QtWidgets.QApplication(sys.argv)
    apply_modern_style(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())