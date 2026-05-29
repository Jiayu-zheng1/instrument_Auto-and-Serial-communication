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

    COLUMNS = ["Test Item", "Lower Limit", "Value", "Upper Limit", "Unit", "Result"]
    COL_WIDTHS = [250, 100, 90, 100, 70, 80]

    # 列索引常量
    COL_ITEM = 0
    COL_LOWER = 1
    COL_VALUE = 2
    COL_UPPER = 3
    COL_UNIT = 4
    COL_RESULT = 5

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

        # 选中行浅蓝背景
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.CONTROL_BG};
                border: 1px solid {Colors.SEPARATOR};
                border-radius: 6px;
                gridline-color: {Colors.SEPARATOR};
                font-size: 13px;
                selection-background-color: #B3D9FF;
                selection-color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 5px 12px;
                border-bottom: 1px solid {Colors.SEPARATOR};
            }}
            QHeaderView::section {{
                background-color: {Colors.CONTROL_BG};
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                padding: 6px 12px;
                border: none;
                border-bottom: 2px solid {Colors.SEPARATOR};
            }}
        """)

    def load_config(self, csv_rows: list[dict]):
        """Populate table from parsed CSV rows where Running='Y'."""
        self.setRowCount(0)
        for row in csv_rows:
            if row.get("Running", "") != "Y":
                continue
            r = self.rowCount()
            self.insertRow(r)
            self.setRowHeight(r, TABLE_ROW_HEIGHT)
            self.setItem(r, self.COL_ITEM, self._cell(row.get("TestItem", "")))
            self.setItem(r, self.COL_LOWER, self._cell(row.get("LowerLimit", "")))
            self.setItem(r, self.COL_VALUE, self._cell(row.get("value", "")))
            self.setItem(r, self.COL_UPPER, self._cell(row.get("UpperLimit", "")))
            self.setItem(r, self.COL_UNIT, self._cell(row.get("Unit", "")))
            self.setItem(r, self.COL_RESULT, self._cell(row.get("Result", "")))

    def clear_results(self):
        for r in range(self.rowCount()):
            self.setItem(r, self.COL_VALUE, self._cell(""))
            self.setItem(r, self.COL_RESULT, self._cell(""))

    def set_value(self, test_item: str, value: str):
        self._update_column(test_item, self.COL_VALUE, value)

    def set_result(self, test_item: str, result: str):
        self._update_column(test_item, self.COL_RESULT, result)

    def set_result_color(self, test_item: str, result: str):
        for r in range(self.rowCount()):
            if (
                self.item(r, self.COL_ITEM)
                and self.item(r, self.COL_ITEM).text() == test_item
            ):
                item = self.item(r, self.COL_RESULT)
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
            if (
                self.item(r, self.COL_ITEM)
                and self.item(r, self.COL_ITEM).text() == test_item
            ):
                self.setItem(r, col, self._cell(value))
                # 自动滚动到当前行
                item = self.item(r, self.COL_ITEM)
                if item:
                    self.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                break

    def _cell(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return item
