"""Manage windows aministrator privileges and error handling."""

import ctypes

from PySide6.QtWidgets import QApplication, QMessageBox


import sys


def show_admin_error() -> None:
    """Show admin error with fallback methods"""
    # Try to create QApplication first if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create message box
    msg = QMessageBox()
    msg.setWindowTitle("Administrator Required")
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText(
        "This application requires Administrator privileges to clean AppData folders."
    )
    msg.setInformativeText("Please run as Administrator and try again.")
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


def ask_elevation() -> None:
    # TODO: This works, however
    # this breaks debuggers and closes the original process.
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False
