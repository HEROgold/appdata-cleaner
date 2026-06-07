from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSlider,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from filters import SortFilterProxyModel


class BottomLayout(QHBoxLayout):
    def __init__(
        self,
        *items: QWidget,
    ) -> None:
        super().__init__()
        for item in items:
            self.addWidget(item)


class TopLayout(QHBoxLayout):
    def __init__(
        self,
        *items: QWidget,
    ) -> None:
        super().__init__()
        for item in items:
            self.addWidget(item)


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


class DeleteButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #DC3545; color: white; }")
        self.setEnabled(False)  # Initially disabled until something is selected


class DeselectAllButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #DC3545; color: white; }")


class SelectAllButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #28A745; color: white; }")


class ScanButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("QPushButton { background-color: #007ACC; color: white; }")
