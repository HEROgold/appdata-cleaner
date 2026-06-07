# -------------------------------------------------------------------------
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt


from typing import override


class SortFilterProxyModel(QSortFilterProxyModel):
    @override
    def lessThan(
        self,
        source_left: QModelIndex | QPersistentModelIndex,
        source_right: QModelIndex | QPersistentModelIndex,
        /,
    ) -> bool:
        # Special handling for the Size column (column 2)
        if source_left.column() == 2:
            left_data = self.sourceModel().data(source_left, Qt.ItemDataRole.UserRole)
            right_data = self.sourceModel().data(source_right, Qt.ItemDataRole.UserRole)
            if left_data is not None and right_data is not None:
                return left_data < right_data
        # Default string comparison for other columns
        return super().lessThan(source_left, source_right)
