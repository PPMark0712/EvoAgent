import argparse
import os

from openpyxl import load_workbook

from create_workspace import BLOCK_LABELS, BLOCK_SIZE, ROW_COUNT, build_workbook


LOOKUP_RANGE_END = ROW_COUNT + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'capacity_dashboard_audit.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    detail = wb['Utilization']
    for row_num in range(2, ROW_COUNT + 2):
        detail[f'A{row_num}'] = f'=Staffing!A{row_num}'
        detail[f'B{row_num}'] = f'=Staffing!B{row_num}'
        detail[f'C{row_num}'] = f'=Staffing!C{row_num}*Staffing!D{row_num}'
        detail[f'D{row_num}'] = f'=C{row_num}*Staffing!E{row_num}'
        detail[f'E{row_num}'] = f'=Staffing!C{row_num}*Staffing!F{row_num}'
        detail[f'F{row_num}'] = f'=D{row_num}-E{row_num}'
        detail[f'G{row_num}'] = f'=IF(Staffing!C{row_num}=0,0,C{row_num}/Staffing!C{row_num})'
    summary = wb['Dashboard']
    for idx, _label in enumerate(BLOCK_LABELS, start=2):
        summary[f'B{idx}'] = f'=SUMIF(Utilization!$B$2:$B${LOOKUP_RANGE_END},$A{idx},Utilization!$D$2:$D${LOOKUP_RANGE_END})'
        summary[f'C{idx}'] = f'=SUMIF(Utilization!$B$2:$B${LOOKUP_RANGE_END},$A{idx},Utilization!$F$2:$F${LOOKUP_RANGE_END})'
        summary[f'D{idx}'] = f'=SUMIF(Utilization!$B$2:$B${LOOKUP_RANGE_END},$A{idx},Utilization!$G$2:$G${LOOKUP_RANGE_END})/{BLOCK_SIZE}'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for workbook audit task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
