import argparse
import json
import os
from datetime import date, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font


DATA_ROW_COUNT = 200
STATUS_VALUES = ["Submitted", "Approved", "Pending", "Flagged"]


def build_workbook(output_file):
    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses"
    headers = ["Expense ID", "Expense Date", "Amount", "Variance %", "Status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    base_date = date(2026, 1, 1)
    for i in range(1, DATA_ROW_COUNT + 1):
        ws.append([
            f"EXP-{i:04d}",
            base_date + timedelta(days=i - 1),
            round(85.5 + i * 6.75, 2),
            round(-0.08 + (i % 12) * 0.0175, 4),
            STATUS_VALUES[(i - 1) % len(STATUS_VALUES)],
        ])
    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, "expense_audit.xlsx")
    build_workbook(output_file)
    with open(os.path.join(args.output_path, "task_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "task_id": "cell_formatting/task_002_format_expense_audit_columns",
                "target_file": "expense_audit.xlsx",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(os.path.abspath(args.output_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create workspace for cell formatting task")
    parser.add_argument("output_path", help="Directory to create workspace in")
    main(parser.parse_args())
