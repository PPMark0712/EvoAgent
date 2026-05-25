import argparse
import os

from openpyxl import load_workbook



def build_workbook(output_file):
    from create_workspace import build_workbook as create_input_workbook

    create_input_workbook(output_file)



def main(args):
    from create_workspace import add_summary_row

    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, "budget_update.xlsx")
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    ws = wb["Inputs"]
    add_summary_row(ws)
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create gold workbook for direct cell update task")
    parser.add_argument("output_path", help="Directory to place gold workbook in")
    main(parser.parse_args())
