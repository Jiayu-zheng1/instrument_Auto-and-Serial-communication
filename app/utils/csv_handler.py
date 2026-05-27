"""CSV report file handler — ported from CSV/Create.py."""
import os
import csv
import time


class CsvReport:
    """Handles test result CSV generation."""

    def __init__(self, test_items: list[str], upper_limit: dict, lower_limit: dict):
        self.item = test_items
        self.columns = [
            'Site', 'Product', 'SerialNumber', 'Station ID',
            'Test Pass/Fail Status', 'StartTime', 'EndTime', 'Version'
        ] + self.item
        self.header_lines = [
            'Display Name ----->',
            'PDCA Priority ----->',
            'Upper Limit ----->',
            'Lower Limit ----->',
            'Measurement Unit ----->',
        ]
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        self.path = os.path.expanduser('~/Documents/SpartaLog/Test_CSV')

    def write_csv(self):
        os.makedirs(self.path, exist_ok=True)
        filename = time.strftime("%Y%m%d.csv")
        filepath = os.path.join(self.path, filename)
        with open(filepath, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.columns)
            writer.writeheader()
            writer.writerow({'Site': self.header_lines[0]})
            row_pdca = {'Site': self.header_lines[1]}
            row_upper = {'Site': self.header_lines[2]}
            row_lower = {'Site': self.header_lines[3]}
            row_meas = {'Site': self.header_lines[4]}
            for item in self.item:
                row_pdca[item] = "-2"
                row_meas[item] = 'N/A'
                row_upper[item] = self.upper_limit.get(item, "")
                row_lower[item] = self.lower_limit.get(item, "")
            writer.writerow(row_pdca)
            writer.writerow(row_upper)
            writer.writerow(row_lower)
            writer.writerow(row_meas)

    def set_csv_file(self, serial: str, value_dict: dict):
        filename = time.strftime("%Y%m%d.csv")
        filepath = os.path.join(self.path, filename)
        if not os.path.exists(filepath):
            self.write_csv()

        newdata = {
            'Site': 'FLDG',
            'Product': '',
            'SerialNumber': serial,
            'Station ID': '',
            'Test Pass/Fail Status': '',
            'StartTime': time.strftime("%Y-%m-%d %H:%M:%S"),
            'EndTime': time.strftime("%Y-%m-%d %H:%M:%S"),
            'Version': '1.0.0',
        }
        for key, value in value_dict.items():
            if key in self.item:
                newdata[key] = value

        with open(filepath, 'a+', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.columns)
            writer.writerow(newdata)
