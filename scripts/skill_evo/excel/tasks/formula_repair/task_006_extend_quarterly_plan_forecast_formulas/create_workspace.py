import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
REGIONS = ['North', 'South', 'East', 'West']


def canonical_rows():
    rows = []
    for idx in range(ROW_COUNT):
        q1_units = 90 + (idx % 18) * 4
        q1_price = 58 + (idx % 6) * 3
        q2_units = q1_units + 8 + (idx % 5)
        q2_price = q1_price + 2 + (idx % 4)
        q3_unit_growth = 0.06 + (idx % 4) * 0.02
        q4_unit_growth = 0.05 + (idx % 5) * 0.015
        q3_price_lift = 0.02 + (idx % 3) * 0.01
        q4_price_lift = 0.015 + (idx % 4) * 0.008
        rows.append((
            f'PLAN-{idx + 1:03d}',
            REGIONS[idx % len(REGIONS)],
            q1_units,
            q1_price,
            q2_units,
            q2_price,
            q3_unit_growth,
            q4_unit_growth,
            q3_price_lift,
            q4_price_lift,
        ))
    return rows


def build_workbook(output_file):
    wb = Workbook()
    drivers = wb.active
    drivers.title = 'Drivers'
    headers = [
        'Account ID',
        'Region',
        'Q1 Units',
        'Q1 Price',
        'Q2 Units',
        'Q2 Price',
        'Q3 Unit Growth',
        'Q4 Unit Growth',
        'Q3 Price Lift',
        'Q4 Price Lift',
    ]
    drivers.append(headers)
    for cell in drivers[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        drivers.append(list(row))

    plan = wb.create_sheet('Plan')
    plan_headers = [
        'Account ID',
        'Region',
        'Q1 Revenue',
        'Q2 Revenue',
        'Q3 Units',
        'Q3 Price',
        'Q3 Revenue',
        'Q4 Units',
        'Q4 Price',
        'Q4 Revenue',
        'H2 Revenue',
        'H2 Growth %',
    ]
    plan.append(plan_headers)
    for cell in plan[1]:
        cell.font = Font(bold=True)
    for row_num in range(2, ROW_COUNT + 2):
        plan[f'A{row_num}'] = f'=Drivers!A{row_num}'
        plan[f'B{row_num}'] = f'=Drivers!B{row_num}'
        plan[f'C{row_num}'] = f'=Drivers!C{row_num}*Drivers!D{row_num}'
        plan[f'D{row_num}'] = f'=Drivers!E{row_num}*Drivers!F{row_num}'
        plan[f'E{row_num}'] = f'=Drivers!C{row_num}*(1+Drivers!G{row_num})'
        plan[f'F{row_num}'] = f'=Drivers!D{row_num}*(1+Drivers!I{row_num})'
        plan[f'G{row_num}'] = f'=E{row_num}+F{row_num}'
        plan[f'H{row_num}'] = f'=Drivers!E{row_num}'
        plan[f'I{row_num}'] = f'=Drivers!F{row_num}'
        plan[f'J{row_num}'] = f'=H{row_num}*I{row_num}'
        plan[f'K{row_num}'] = f'=G{row_num}'
        plan[f'L{row_num}'] = f'=K{row_num}/0'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'quarterly_plan.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {
                'task_id': 'formula_repair/task_006_extend_quarterly_plan_forecast_formulas',
                'target_file': 'quarterly_plan.xlsx',
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(os.path.abspath(args.output_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create workspace for formula repair task')
    parser.add_argument('output_path', help='Directory to create workspace in')
    main(parser.parse_args())
