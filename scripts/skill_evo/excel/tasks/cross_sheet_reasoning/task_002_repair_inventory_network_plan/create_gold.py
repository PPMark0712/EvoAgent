import argparse
import os

from openpyxl import load_workbook
from create_workspace import ROW_COUNT, build_workbook


LOOKUP_RANGE_END = ROW_COUNT + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'inventory_network_plan.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    target_ws = wb['Plan']
    for row_num in range(2, ROW_COUNT + 2):
        target_ws[f'A{row_num}'] = f'=Demand!A{row_num}'
        target_ws[f'B{row_num}'] = f'=Demand!B{row_num}'
        target_ws[f'C{row_num}'] = f'=Demand!C{row_num}+Demand!D{row_num}'
        target_ws[f'D{row_num}'] = f'=IF(SUMIF(Supply!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Supply!$B$2:$B${LOOKUP_RANGE_END})=0,0,C{row_num}/SUMIF(Supply!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Supply!$B$2:$B${LOOKUP_RANGE_END}))'
        target_ws[f'E{row_num}'] = f'=D{row_num}*SUMIF(Supply!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Supply!$C$2:$C${LOOKUP_RANGE_END})'
        target_ws[f'F{row_num}'] = f'=E{row_num}*SUMIF(Supply!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Supply!$D$2:$D${LOOKUP_RANGE_END})'
        target_ws[f'G{row_num}'] = f'=E{row_num}+F{row_num}'
        target_ws[f'H{row_num}'] = f'=IF(C{row_num}=0,0,G{row_num}/C{row_num})'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for cross sheet reasoning task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
