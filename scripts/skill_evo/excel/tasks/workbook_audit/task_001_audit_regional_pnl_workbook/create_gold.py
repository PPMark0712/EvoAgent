import argparse
import os

from openpyxl import load_workbook

from create_workspace import BLOCK_LABELS, ROW_COUNT, build_workbook


LOOKUP_RANGE_END = ROW_COUNT + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'regional_pnl_audit.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    detail = wb['PnL']
    for row_num in range(2, ROW_COUNT + 2):
        detail[f'A{row_num}'] = f'=Drivers!A{row_num}'
        detail[f'B{row_num}'] = f'=Drivers!B{row_num}'
        detail[f'C{row_num}'] = f'=Drivers!C{row_num}'
        detail[f'D{row_num}'] = f'=C{row_num}*Drivers!D{row_num}'
        detail[f'E{row_num}'] = f'=C{row_num}-D{row_num}'
        detail[f'F{row_num}'] = f'=E{row_num}*Drivers!E{row_num}'
        detail[f'G{row_num}'] = f'=E{row_num}-F{row_num}'
        detail[f'H{row_num}'] = f'=Drivers!F{row_num}'
        detail[f'I{row_num}'] = f'=G{row_num}-H{row_num}'
        detail[f'J{row_num}'] = f'=IF(E{row_num}=0,0,I{row_num}/E{row_num})'

    summary = wb['Summary']
    for idx, _label in enumerate(BLOCK_LABELS, start=2):
        summary[f'B{idx}'] = f'=SUMIF(PnL!$B$2:$B${LOOKUP_RANGE_END},$A{idx},PnL!$E$2:$E${LOOKUP_RANGE_END})'
        summary[f'C{idx}'] = f'=SUMIF(PnL!$B$2:$B${LOOKUP_RANGE_END},$A{idx},PnL!$I$2:$I${LOOKUP_RANGE_END})'
        summary[f'D{idx}'] = f'=IF(B{idx}=0,0,C{idx}/B{idx})'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for workbook audit task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
