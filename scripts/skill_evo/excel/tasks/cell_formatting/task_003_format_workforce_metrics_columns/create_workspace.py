import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


DATA_ROW_COUNT = 200
RISK_VALUES = ["Low", "Medium", "High", "Critical"]


def build_workbook(output_file):
    wb = Workbook()
    ws = wb.active
    ws.title = "Roster"
    headers = ["Employee ID", "Monthly Salary", "Utilization Rate", "Bonus Target", "Risk Level"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for i in range(1, DATA_ROW_COUNT + 1):
        ws.append([
            f"EMP-{i:04d}",
            6800 + i * 32,
            round(0.58 + (i % 10) * 0.035, 4),
            900 + i * 11,
            RISK_VALUES[(i - 1) % len(RISK_VALUES)],
        ])
    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, "workforce_metrics.xlsx")
    build_workbook(output_file)
    with open(os.path.join(args.output_path, "task_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "task_id": "cell_formatting/task_003_format_workforce_metrics_columns",
                "target_file": "workforce_metrics.xlsx",
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
