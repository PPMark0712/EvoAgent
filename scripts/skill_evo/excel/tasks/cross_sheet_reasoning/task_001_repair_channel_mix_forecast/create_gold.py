import argparse
import os

from openpyxl import load_workbook
from create_workspace import ROW_COUNT, build_mix_rows, build_workbook


LOOKUP_RANGE_END = len(build_mix_rows()) + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'channel_mix_forecast.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    target_ws = wb['Output']
    for row_num in range(2, ROW_COUNT + 2):
        target_ws[f'A{row_num}'] = f'=Drivers!A{row_num}'
        target_ws[f'B{row_num}'] = f'=Drivers!B{row_num}'
        target_ws[f'C{row_num}'] = f'=Drivers!C{row_num}*Drivers!D{row_num}'
        target_ws[f'D{row_num}'] = (
            f'=C{row_num}*SUMIFS(Mix!$D$2:$D${LOOKUP_RANGE_END},'
            f'Mix!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},'
            f'Mix!$B$2:$B${LOOKUP_RANGE_END},$B{row_num},'
            f'Mix!$C$2:$C${LOOKUP_RANGE_END},"Active")'
        )
        target_ws[f'E{row_num}'] = (
            f'=C{row_num}*SUMIFS(Mix!$E$2:$E${LOOKUP_RANGE_END},'
            f'Mix!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},'
            f'Mix!$B$2:$B${LOOKUP_RANGE_END},$B{row_num},'
            f'Mix!$C$2:$C${LOOKUP_RANGE_END},"Active")'
        )
        target_ws[f'F{row_num}'] = f'=(C{row_num}-E{row_num})*Drivers!E{row_num}'
        target_ws[f'G{row_num}'] = (
            f'=F{row_num}*SUMIFS(Mix!$F$2:$F${LOOKUP_RANGE_END},'
            f'Mix!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},'
            f'Mix!$B$2:$B${LOOKUP_RANGE_END},$B{row_num},'
            f'Mix!$C$2:$C${LOOKUP_RANGE_END},"Active")'
        )
        target_ws[f'H{row_num}'] = f'=F{row_num}+G{row_num}'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for cross sheet reasoning task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
