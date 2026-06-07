from __future__ import annotations
import sys
from admin import is_admin, ask_elevation
from filters import SortFilterProxyModel


from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTableView,
    QVBoxLayout,
    QWidget,
    QApplication,
)
from humanize import naturalsize


import os
from pathlib import Path
from typing import Any

from utils import parse_size
from workers import DeleteWorker, ScanWorker


def start_scan(main: MainWindow) -> None:
    if main.scan_worker and main.scan_worker.isRunning():
        return
    main.source_model.removeRows(0, main.source_model.rowCount())
    main.progress_bar.setVisible(False)  # Hide progress bar
    main.status_label.setText("Scanning…")
    main.size_info_label.setText("")  # Clear size info
    main.delete_btn.setEnabled(False)  # Disable during scan
    main.scan_btn.setEnabled(False)  # Disable scan button during scan
    main.select_all_btn.setEnabled(False)  # Disable selection buttons during scan
    main.deselect_all_btn.setEnabled(False)

    appdata = os.environ.get("APPDATA")
    local = os.environ.get("LOCALAPPDATA")

    bases = [
        Path(appdata) if appdata else None,
        Path(local) if local else None,
        Path(local.replace("Local", "LocalLow")) if local else None,
    ]
    bases = [b for b in bases if b and os.path.exists(b)]
    max_depth = main.depth_slider.value()
    main.scan_worker = ScanWorker(bases, max_depth)

    def add_label(n: int) -> None:
        main.status_label.setText(f"Found {n} folders")

    def add_scanning(n: str) -> None:
        main.status_label.setText(f"Scanning: {n}")

    main.scan_worker.progress.connect(add_label)
    main.scan_worker.current_path.connect(add_scanning)
    main.scan_worker.folder_found.connect(main.add_table_row)
    main.scan_worker.finished.connect(main.scan_finished)
    main.scan_worker.start()


def set_state_all(main: MainWindow, state: Qt.CheckState) -> None:
    for row in range(main.source_model.rowCount()):
        main.source_model.item(row, 0).setCheckState(state)


def select_all(main: MainWindow) -> None:
    set_state_all(main, Qt.CheckState.Checked)


def deselect_all(main: MainWindow) -> None:
    set_state_all(main, Qt.CheckState.Unchecked)


def confirm(main: MainWindow, title: str, message: str) -> bool:
    """Show a confirmation dialog and return True if user confirms."""
    return (
        QMessageBox.question(
            main,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        == QMessageBox.StandardButton.Yes
    )


def confirm_deletion(main: MainWindow, count: int) -> bool:
    """Show a confirmation dialog before deletion."""
    return confirm(
        main,
        "Confirm Deletion",
        f"Are you sure you want to delete {count} selected folder(s)? This action cannot be undone.",
    )


def start_delete(main: MainWindow) -> None:
    paths_to_delete: list[Path] = [
        Path(main.source_model.item(row, 1).text())
        for row in range(main.source_model.rowCount())
        if main.source_model.item(row, 0).checkState() == Qt.CheckState.Checked
    ]

    if not confirm_deletion(main, len(paths_to_delete)):
        return

    main.delete_btn.setEnabled(False)
    main.progress_bar.setVisible(True)
    main.progress_bar.setRange(0, len(paths_to_delete))
    main.status_label.setText("Deleting…")

    main.delete_worker = DeleteWorker(paths_to_delete)
    main.delete_worker.progress.connect(main.progress_bar.setValue)
    main.delete_worker.finished.connect(main.deletion_finished)
    main.delete_worker.start()


def update_totals(main: MainWindow, *_: Any) -> None:
    total_found = 0
    total_selected = 0
    selected_count = 0

    for row in range(main.source_model.rowCount()):
        size_item = main.source_model.item(row, 2)
        # Get the raw size in bytes from UserRole data
        size_bytes = size_item.data(Qt.ItemDataRole.UserRole)
        if size_bytes is None:
            # Fallback to parsing the displayed text if no UserRole data
            size_bytes = parse_size(size_item.text())

        total_found += size_bytes
        if main.source_model.item(row, 0).checkState() == Qt.CheckState.Checked:
            total_selected += size_bytes
            selected_count += 1

    found_h = naturalsize(total_found, binary=True)
    selected_h = naturalsize(total_selected, binary=True)

    # Update status
    row_count = main.source_model.rowCount()
    if row_count > 0:
        main.status_label.setText(f"Found {row_count} folders")
        main.size_info_label.setText(f"[{selected_h} / {found_h}]")
    else:
        main.status_label.setText("Ready")
        main.size_info_label.setText("")

    # Enable delete button if something is selected
    main.delete_btn.setEnabled(total_selected > 0 and selected_count > 0)


class ScanButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #007ACC; color: white; }")


class SelectAllButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #28A745; color: white; }")


class DeselectAllButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #DC3545; color: white; }")


class DeleteButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #DC3545; color: white; }")
        self.setEnabled(False)  # Initially disabled until something is selected


class DepthSlider(QSlider):
    def __init__(self, depth_label: QLabel, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimum(0)
        self.setMaximum(10)
        self.setValue(3)
        self.setFixedWidth(100)
        self.depth_label = depth_label
        self.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self, value: int) -> None:
        if value == 0:
            self.depth_label.setText("Depth: ∞")
        else:
            self.depth_label.setText(f"Depth: {value}")


class TableView(QTableView):
    def __init__(
        self, proxy_model: SortFilterProxyModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)

        self.setModel(proxy_model)
        self.setSortingEnabled(True)
        self.setColumnWidth(0, 40)
        self.setColumnWidth(2, 100)  # Size column
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )  # Path column
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        # Sort by size (column 2) in descending order by default
        self.sortByColumn(2, Qt.SortOrder.DescendingOrder)


class TopLayout(QHBoxLayout):
    def __init__(
        self,
        *items: QWidget,
    ) -> None:
        super().__init__()
        for item in items:
            self.addWidget(item)


class BottomLayout(QHBoxLayout):
    def __init__(
        self,
        *items: QWidget,
    ) -> None:
        super().__init__()
        for item in items:
            self.addWidget(item)


class MainLayout(QVBoxLayout):
    def __init__(
        self,
        top_layout: TopLayout,
        table: TableView,
        bottom_layout: BottomLayout,
    ) -> None:
        super().__init__()
        self.addLayout(top_layout)
        self.addWidget(table)
        self.addLayout(bottom_layout)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AppData Cleaner")
        self.resize(900, 600)

        # UI Elements
        self.scan_btn = ScanButton("Scan")
        self.select_all_btn = SelectAllButton("Select All")
        self.deselect_all_btn = DeselectAllButton("Deselect All")
        self.delete_btn = DeleteButton("Delete Selected")

        # Depth slider
        self.depth_label = QLabel("Depth: 3")
        self.depth_slider = DepthSlider(depth_label=self.depth_label)
        self.depth_slider.valueChanged.connect(self.update_depth_label)

        # Size info label
        self.size_info_label = QLabel("")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        self.source_model = QStandardItemModel(0, 3)
        self.source_model.setHorizontalHeaderLabels(["✔", "Path", "Size"])

        # Setup proxy model for sorting
        self.proxy_model = SortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)

        self.table = TableView(self.proxy_model)

        self.status_label = QLabel("Ready")

        # Layout
        top_layout = self.add_top_layout()
        bottom_layout = self.add_bottom_layout()
        main_layout = self.add_main_layout(top_layout, bottom_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Connections
        self.scan_btn.clicked.connect(self.start_scan)
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.delete_btn.clicked.connect(self.start_delete)
        self.source_model.itemChanged.connect(self.update_totals)

        self.scan_worker: ScanWorker | None = None
        self.delete_worker: DeleteWorker | None = None

    def add_main_layout(
        self, top_layout: TopLayout, bottom_layout: BottomLayout
    ) -> MainLayout:
        main_layout = MainLayout(
            top_layout=top_layout, table=self.table, bottom_layout=bottom_layout
        )

        return main_layout

    def add_top_layout(self) -> TopLayout:
        top_layout = TopLayout(
            self.scan_btn,
            self.select_all_btn,
            self.deselect_all_btn,
            self.depth_label,
            self.depth_slider,
        )
        top_layout.addStretch()  # Push buttons to the left
        top_layout.addWidget(self.progress_bar)
        return top_layout

    def add_bottom_layout(self) -> BottomLayout:
        bottom_layout = BottomLayout(self.status_label)
        bottom_layout.addStretch()  # Push status to the left
        bottom_layout.addWidget(self.size_info_label)
        bottom_layout.addWidget(self.delete_btn)
        return bottom_layout

        # No initial scan - user will click button when ready

    def update_depth_label(self, value: int) -> None:
        if value == 0:
            self.depth_label.setText("Depth: ∞")
        else:
            self.depth_label.setText(f"Depth: {value}")

    # ---------- Scanning --------------------------------------------------
    start_scan = start_scan

    def add_table_row(self, path: Path, size_human: str, size_bytes_str: str) -> None:
        """Add a new row to the table with the given path and size information."""
        checkbox_item = QStandardItem()
        checkbox_item.setCheckable(True)
        checkbox_item.setEditable(False)
        path_item = QStandardItem(str(path))
        size_item = QStandardItem(size_human)
        # Store the raw size in bytes as user data for calculations
        size_item.setData(int(size_bytes_str), Qt.ItemDataRole.UserRole)
        self.source_model.appendRow([checkbox_item, path_item, size_item])
        self.update_totals()

    def scan_finished(self, total_count: int) -> None:
        self.status_label.setText(f"Scan completed. Found {total_count} folders")
        self.scan_btn.setEnabled(True)  # Re-enable scan button
        self.select_all_btn.setEnabled(True)  # Re-enable selection buttons
        self.deselect_all_btn.setEnabled(True)
        # Sort by size in descending order after scan completion
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        self.update_totals()  # Final update to enable delete button if something selected

    select_all = select_all
    deselect_all = deselect_all
    update_totals = update_totals
    start_delete = start_delete

    def deletion_finished(self) -> None:
        QMessageBox.information(self, "Done", "Selected folders have been deleted.")
        # Auto re-scan
        self.start_scan()


if __name__ == "__main__":
    # Debug info for admin check
    admin_status = is_admin()

    # Debug mode - show admin status (remove this after testing)
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        app = QApplication(sys.argv)
        QMessageBox.information(
            None,
            "Debug Info",
            f"Platform: {sys.platform}\n"
            f"Admin Status: {admin_status}\n"
            f"Will show admin error: {sys.platform.startswith('win') and not admin_status}",
        )

    if sys.platform.startswith("win") and not admin_status:
        ask_elevation()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
