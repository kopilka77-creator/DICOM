# -*- coding: utf-8 -*-
from PyQt5 import QtGui

QSS = """
QMainWindow, QWidget { background-color: #1e1e1e; color: #e0e0e0; }
QWidget { font-family: "Segoe UI", "SF Pro Text", "Ubuntu", "Sans-Serif"; font-size: 10pt; }
QMenuBar { background-color: #252526; color: #e0e0e0; padding: 4px; border-bottom: 1px solid #3c3c3c; }
QMenuBar::item { padding: 6px 12px; background: transparent; border-radius: 4px; }
QMenuBar::item:selected { background-color: #3c3c3c; }
QMenuBar::item:pressed { background-color: #4a9eff; color: #ffffff; }
QMenu { background-color: #2d2d30; color: #e0e0e0; border: 1px solid #3c3c3c; border-radius: 6px; padding: 6px; }
QMenu::item { padding: 8px 24px; border-radius: 4px; min-width: 160px; }
QMenu::item:selected { background-color: #4a9eff; color: #ffffff; }
QMenu::separator { height: 1px; background-color: #3c3c3c; margin: 4px 8px; }
QToolBar { background-color: #252526; border: none; border-bottom: 1px solid #3c3c3c; padding: 6px 8px; spacing: 4px; }
QToolBar QToolButton { background-color: transparent; color: #e0e0e0; border: 1px solid transparent; border-radius: 6px; padding: 6px 10px; min-width: 28px; min-height: 28px; }
QToolBar QToolButton:hover { background-color: #3c3c3c; border-color: #3c3c3c; }
QToolBar QToolButton:pressed, QToolBar QToolButton:checked { background-color: #4a9eff; color: #ffffff; border-color: #4a9eff; }
QPushButton { background-color: #3c3c3c; color: #e0e0e0; border: 1px solid #4a4a4a; border-radius: 6px; padding: 7px 14px; min-height: 26px; }
QPushButton:hover { background-color: #4a4a4a; border-color: #5a5a5a; }
QPushButton:pressed, QPushButton:checked { background-color: #4a9eff; color: #ffffff; border-color: #4a9eff; }
QPushButton:disabled { background-color: #2d2d30; color: #666666; border-color: #3c3c3c; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #2d2d30; color: #e0e0e0; border: 1px solid #3c3c3c; border-radius: 6px; padding: 5px 9px; min-height: 24px; selection-background-color: #4a9eff; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #4a9eff; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background-color: #2d2d30; color: #e0e0e0; border: 1px solid #3c3c3c; border-radius: 6px; selection-background-color: #4a9eff; padding: 4px; }
QGroupBox { background-color: #252526; border: 1px solid #3c3c3c; border-radius: 8px; margin-top: 18px; padding: 16px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 12px; color: #4a9eff; background-color: #1e1e1e; }
QCheckBox { color: #e0e0e0; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #3c3c3c; background-color: #2d2d30; }
QCheckBox::indicator:hover { border-color: #4a9eff; }
QCheckBox::indicator:checked { background-color: #4a9eff; border-color: #4a9eff; }
QSlider::groove:horizontal { background-color: #3c3c3c; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal { background-color: #4a9eff; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }
QSlider::handle:horizontal:hover { background-color: #5aacff; }
QDockWidget { color: #e0e0e0; }
QDockWidget::title { background-color: #252526; padding: 8px 12px; border-bottom: 1px solid #3c3c3c; font-weight: 600; color: #4a9eff; }
QTreeWidget, QListWidget, QTableWidget, QPlainTextEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #3c3c3c; border-radius: 6px; alternate-background-color: #252526; selection-background-color: #4a9eff; selection-color: #ffffff; gridline-color: #3c3c3c; }
QTreeWidget::item, QTableWidget::item { padding: 4px; border: none; }
QHeaderView::section { background-color: #2d2d30; color: #e0e0e0; border: none; border-right: 1px solid #3c3c3c; border-bottom: 1px solid #3c3c3c; padding: 6px; font-weight: 600; }
QScrollBar:vertical { background-color: #1e1e1e; width: 12px; border-radius: 6px; border: none; }
QScrollBar::handle:vertical { background-color: #3c3c3c; border-radius: 6px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #4a4a4a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background-color: #1e1e1e; height: 12px; border-radius: 6px; border: none; }
QScrollBar::handle:horizontal { background-color: #3c3c3c; border-radius: 6px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #4a4a4a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QStatusBar { background-color: #252526; color: #a0a0a0; border-top: 1px solid #3c3c3c; padding: 2px; font-size: 9pt; }
QStatusBar::item { border: none; }
QDialog { background-color: #1e1e1e; }
QMessageBox { background-color: #1e1e1e; }
QToolTip { background-color: #2d2d30; color: #e0e0e0; border: 1px solid #3c3c3c; border-radius: 4px; padding: 6px; font-size: 9pt; }
QScrollArea { background-color: #1e1e1e; border: none; }
QScrollArea > QWidget > QWidget { background-color: #1e1e1e; }
QInputDialog { background-color: #1e1e1e; }
QInputDialog QLabel { color: #e0e0e0; }
QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 6px; top: -1px; }
QTabWidget::tab-bar { alignment: left; }
QTabBar { background-color: #252526; }
QTabBar::tab { background-color: #2d2d30; color: #a0a0a0; border: 1px solid #3c3c3c; border-bottom: none; padding: 8px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:hover { background-color: #3c3c3c; color: #e0e0e0; }
QTabBar::tab:selected { background-color: #1e1e1e; color: #4a9eff; border-color: #4a9eff #4a9eff #1e1e1e; border-bottom: 1px solid #1e1e1e; font-weight: 600; }
"""


def apply_modern_style(app):
    app.setStyle("Fusion")
    try:
        font = QtGui.QFont("Segoe UI", 10)
    except Exception:
        font = QtGui.QFont()
    app.setFont(font)
    app.setStyleSheet(QSS)