import argparse
import os

from openpyxl import Workbook
from openpyxl.styles import Font


def main(args):
    from create_workspace import canonical_rows, messy_rows

    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, "roster_clean.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Clean"
    ws.append(["Employee ID", "Department", "Location", "Status", "Manager"])
    raw_rows = messy_rows()
    for index, row in enumerate(canonical_rows()):
        ws.append([row["employee_id"], row["department"], row["location"], row["status"], raw_rows[index][4]])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create gold workbook for data cleaning task")
    parser.add_argument("output_path", help="Directory to place gold workbook in")
    main(parser.parse_args())
