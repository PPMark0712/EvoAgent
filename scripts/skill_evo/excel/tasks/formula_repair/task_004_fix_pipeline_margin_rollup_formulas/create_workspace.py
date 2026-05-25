import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
REGIONS = ['North', 'South', 'East', 'West']
OWNERS = ['Ava', 'Leo', 'Mia', 'Noah', 'Ivy']


def canonical_rows():
    rows = []
    for idx in range(ROW_COUNT):
        bookings = 1200 + idx * 17
        implementation_cost = 260 + (idx % 12) * 11
        commission_rate = 0.04 + (idx % 5) * 0.01
        support_cost = 90 + (idx % 10) * 7
        expansion_revenue = 140 + (idx % 8) * 13
        discount_rate = 0.02 + (idx % 4) * 0.01
        renewal_probability = 0.65 + (idx % 7) * 0.03
        rows.append((
            f'DEAL-{idx + 1:03d}',
            REGIONS[idx % len(REGIONS)],
            OWNERS[idx % len(OWNERS)],
            bookings,
            implementation_cost,
            commission_rate,
            support_cost,
            expansion_revenue,
            discount_rate,
            renewal_probability,
        ))
    return rows


def build_workbook(output_file):
    wb = Workbook()
    pipeline = wb.active
    pipeline.title = 'Pipeline'
    headers = [
        'Deal ID',
        'Region',
        'Owner',
        'Bookings',
        'Implementation Cost',
        'Sales Commission Rate',
        'Support Cost',
        'Expansion Revenue',
        'Discount Rate',
        'Renewal Probability',
    ]
    pipeline.append(headers)
    for cell in pipeline[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        pipeline.append(list(row))

    rollup = wb.create_sheet('Rollup')
    rollup_headers = [
        'Deal ID',
        'Region',
        'Gross Revenue',
        'Commission Cost',
        'Support Cost',
        'Discount Loss',
        'Weighted Revenue',
        'Net Margin',
        'Margin %',
        'Expected Expansion',
    ]
    rollup.append(rollup_headers)
    for cell in rollup[1]:
        cell.font = Font(bold=True)
    for row_num in range(2, ROW_COUNT + 2):
        rollup[f'A{row_num}'] = f'=Pipeline!A{row_num}'
        rollup[f'B{row_num}'] = f'=Pipeline!B{row_num}'
        rollup[f'C{row_num}'] = f'=Pipeline!D{row_num}+Pipeline!E{row_num}'
        rollup[f'D{row_num}'] = f'=Pipeline!D{row_num}*0'
        rollup[f'E{row_num}'] = f'=Pipeline!F{row_num}'
        rollup[f'F{row_num}'] = f'=C{row_num}*Pipeline!J{row_num}'
        rollup[f'G{row_num}'] = f'=C{row_num}*Pipeline!I{row_num}'
        rollup[f'H{row_num}'] = f'=G{row_num}-D{row_num}'
        rollup[f'I{row_num}'] = f'=H{row_num}/0'
        rollup[f'J{row_num}'] = f'=Pipeline!H{row_num}*0'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'pipeline_margin_rollup.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {
                'task_id': 'formula_repair/task_004_fix_pipeline_margin_rollup_formulas',
                'target_file': 'pipeline_margin_rollup.xlsx',
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
