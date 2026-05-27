"""HIG-styled test results table."""

from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
)
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtCore import Qt
from app.views.theme import Colors, FONT_FAMILY, TABLE_ROW_HEIGHT


class TestTable(QTableWidget):
    """Clean, borderless table for test item results."""

    COLUMNS = ["Test Item", "Lower Limit", "Value", "Upper Limit", "Result"]
    COL_WIDTHS = [340, 110, 110, 110, 100]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup()

    def _setup(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)

        for i, w in enumerate(self.COL_WIDTHS):
            self.setColumnWidth(i, w)

        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.NoFocus)

        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

        font = QFont(FONT_FAMILY.split(",")[0].strip('"'), 13)
        self.setFont(font)

    def load_config(self, csv_rows: list[dict]):
        """Populate table from parsed CSV rows where Running='Y'."""
        self.setRowCount(0)
        for row in csv_rows:
            if row.get("Running", "") != "Y":
                continue
            r = self.rowCount()
            self.insertRow(r)
            self.setRowHeight(r, TABLE_ROW_HEIGHT)
            self.setItem(r, 0, self._cell(row.get("TestItem", "")))
            self.setItem(r, 1, self._cell(row.get("LowerLimit", "")))
            self.setItem(r, 2, self._cell(row.get("value", "")))
            self.setItem(r, 3, self._cell(row.get("UpperLimit", "")))
            self.setItem(r, 4, self._cell(row.get("Result", "")))

    def clear_results(self):
        for r in range(self.rowCount()):
            self.setItem(r, 2, self._cell(""))
            self.setItem(r, 4, self._cell(""))

    def set_value(self, test_item: str, value: str):
        self._update_column(test_item, 2, value)

    def set_result(self, test_item: str, result: str):
        self._update_column(test_item, 4, result)

    def set_result_color(self, test_item: str, result: str):
        for r in range(self.rowCount()):
            if self.item(r, 0) and self.item(r, 0).text() == test_item:
                item = self.item(r, 4)
                if item:
                    if result == "Pass":
                        item.setBackground(QBrush(QColor(Colors.SUCCESS_BG)))
                        item.setForeground(QBrush(QColor(Colors.SUCCESS)))
                    else:
                        item.setBackground(QBrush(QColor(Colors.DANGER_BG)))
                        item.setForeground(QBrush(QColor(Colors.DANGER)))
                break

    def _update_column(self, test_item: str, col: int, value: str):
        for r in range(self.rowCount()):
            if self.item(r, 0) and self.item(r, 0).text() == test_item:
                self.setItem(r, col, self._cell(value))
                break

    def _cell(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return item
