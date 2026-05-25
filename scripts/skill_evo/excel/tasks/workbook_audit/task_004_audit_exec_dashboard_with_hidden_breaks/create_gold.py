import argparse
import os

from openpyxl import load_workbook
from create_workspace import BLOCK_SIZE, ROW_COUNT, SEGMENTS, build_workbook


LOOKUP_RANGE_END = ROW_COUNT + 1
TARGET_RANGE_END = len(SEGMENTS) + 1


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    target = os.path.join(args.output_path, 'exec_dashboard_audit.xlsx')
    if not os.path.isfile(target):
        build_workbook(target)
    wb = load_workbook(target)
    model = wb['OperatingModel']
    for row_num in range(2, ROW_COUNT + 2):
        model[f'A{row_num}'] = f'=Drivers!A{row_num}'
        model[f'B{row_num}'] = f'=Drivers!B{row_num}'
        model[f'C{row_num}'] = f'=Drivers!C{row_num}*(1+SUMIF(Adjustments!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Adjustments!$B$2:$B${LOOKUP_RANGE_END})-SUMIF(Adjustments!$A$2:$A${LOOKUP_RANGE_END},$A{row_num},Adjustments!$C$2:$C${LOOKUP_RANGE_END}))'
        model[f'D{row_num}'] = f'=C{row_num}*Drivers!D{row_num}'
        model[f'E{row_num}'] = f'=C{row_num}*Drivers!E{row_num}'
        model[f'F{row_num}'] = f'=D{row_num}-E{row_num}-Drivers!F{row_num}'
        model[f'G{row_num}'] = f'=IF(D{row_num}=0,0,F{row_num}/D{row_num})'

    dashboard = wb['Dashboard']
    alerts = wb['Alerts']
    for idx, _segment in enumerate(SEGMENTS, start=2):
        dashboard[f'B{idx}'] = f'=SUMIF(OperatingModel!$B$2:$B${LOOKUP_RANGE_END},$A{idx},OperatingModel!$C$2:$C${LOOKUP_RANGE_END})'
        dashboard[f'C{idx}'] = f'=SUMIF(OperatingModel!$B$2:$B${LOOKUP_RANGE_END},$A{idx},OperatingModel!$F$2:$F${LOOKUP_RANGE_END})'
        dashboard[f'D{idx}'] = f'=SUMIF(OperatingModel!$B$2:$B${LOOKUP_RANGE_END},$A{idx},OperatingModel!$G$2:$G${LOOKUP_RANGE_END})/{BLOCK_SIZE}'
        alerts[f'B{idx}'] = f'=IF(Dashboard!D{idx}<SUMIF(Targets!$A$2:$A${TARGET_RANGE_END},$A{idx},Targets!$C$2:$C${TARGET_RANGE_END}),"ALERT","OK")'
        alerts[f'C{idx}'] = f'=IF(Dashboard!B{idx}<SUMIF(Targets!$A$2:$A${TARGET_RANGE_END},$A{idx},Targets!$B$2:$B${TARGET_RANGE_END}),"ALERT","OK")'
    wb.save(target)
    wb.close()
    print(os.path.abspath(target))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create gold workbook for hard workbook audit task')
    parser.add_argument('output_path', help='Directory to place gold workbook in')
    main(parser.parse_args())
