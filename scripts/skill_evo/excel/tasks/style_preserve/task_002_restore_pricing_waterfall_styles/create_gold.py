import argparse
import os

from openpyxl import load_workbook
from create_workspace import build_workbook, write_formulas, apply_full_styles


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'pricing_waterfall_style.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    target_ws = wb['Waterfall']
    for row_num in range(2, 180 + 2):
        write_formulas(target_ws, row_num, broken=False)
    apply_full_styles(target_ws, 180)
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for style preserve task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
