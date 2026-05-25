import argparse
import os

from openpyxl import load_workbook
from create_workspace import ROW_COUNT, build_workbook


LOOKUP_RANGE_END = ROW_COUNT + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'multi_sheet_margin_bridge.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    target_ws = wb['Bridge']
    for row_num in range(2, ROW_COUNT + 2):
        target_ws[f'A{row_num}'] = f'=Orders!A{row_num}'
        target_ws[f'B{row_num}'] = f'=Orders!B{row_num}'
        target_ws[f'C{row_num}'] = f'=Orders!C{row_num}*SUMIF(Pricing!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Pricing!$B$2:$B${LOOKUP_RANGE_END})'
        target_ws[f'D{row_num}'] = f'=C{row_num}*SUMIF(Pricing!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Pricing!$C$2:$C${LOOKUP_RANGE_END})'
        target_ws[f'E{row_num}'] = f'=C{row_num}-D{row_num}'
        target_ws[f'F{row_num}'] = f'=Orders!C{row_num}*SUMIF(Costs!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Costs!$B$2:$B${LOOKUP_RANGE_END})'
        target_ws[f'G{row_num}'] = f'=E{row_num}-F{row_num}-SUMIF(Costs!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Costs!$C$2:$C${LOOKUP_RANGE_END})'
        target_ws[f'H{row_num}'] = f'=IF(E{row_num}=0,0,G{row_num}/E{row_num})'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for cross sheet reasoning task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
