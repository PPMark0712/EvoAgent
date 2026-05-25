import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


DATA_ROW_COUNT = 200
SEGMENTS = ["SMB", "Mid-Market", "Enterprise", "Channel"]


def build_workbook(output_file):
    wb = Workbook()
    ws = wb.active
    ws.title = "Revenue"
    headers = ["Account ID", "ARR", "Growth Rate", "Renewal Rate", "Segment"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for i in range(1, DATA_ROW_COUNT + 1):
        ws.append([
            f"ACC-{i:04d}",
            12000 + i * 175,
            round(0.03 + (i % 9) * 0.0125, 4),
            round(0.71 + (i % 7) * 0.025, 4),
            SEGMENTS[(i - 1) % len(SEGMENTS)],
        ])
    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, "revenue_tracker.xlsx")
    build_workbook(output_file)
    with open(os.path.join(args.output_path, "task_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "task_id": "cell_formatting/task_001_format_revenue_tracker_columns",
                "target_file": "revenue_tracker.xlsx",
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
