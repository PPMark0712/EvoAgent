import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
CHANNELS = ['Paid Search', 'Partner', 'Outbound', 'Lifecycle']


def canonical_rows():
    rows = []
    for idx in range(ROW_COUNT):
        leads = 90 + (idx % 30) * 4
        conversions = 12 + (idx % 14)
        avg_deal = 900 + (idx % 11) * 80
        cac = 18 + (idx % 7) * 2
        service_cost = 45 + (idx % 9) * 3
        discount_rate = 0.03 + (idx % 4) * 0.01
        refund_rate = 0.01 + (idx % 3) * 0.005
        contract_months = 6 + (idx % 7)
        rows.append((
            f'ACC-{idx + 1:03d}',
            CHANNELS[idx % len(CHANNELS)],
            leads,
            conversions,
            avg_deal,
            cac,
            service_cost,
            discount_rate,
            refund_rate,
            contract_months,
        ))
    return rows


def build_workbook(output_file):
    wb = Workbook()
    raw = wb.active
    raw.title = 'Raw'
    headers = [
        'Account ID',
        'Channel',
        'Leads',
        'Conversions',
        'Avg Deal Size',
        'CAC per Lead',
        'Service Cost per Conversion',
        'Discount Rate',
        'Refund Rate',
        'Contract Months',
    ]
    raw.append(headers)
    for cell in raw[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        raw.append(list(row))

    model = wb.create_sheet('Model')
    model_headers = [
        'Account ID',
        'Channel',
        'Revenue',
        'Acquisition Spend',
        'Service Cost',
        'Discount Loss',
        'Refund Loss',
        'Net Revenue',
        'Contribution',
        'ROI',
    ]
    model.append(model_headers)
    for cell in model[1]:
        cell.font = Font(bold=True)
    for row_num in range(2, ROW_COUNT + 2):
        model[f'A{row_num}'] = f'=Raw!A{row_num}'
        model[f'B{row_num}'] = f'=Raw!B{row_num}'
        model[f'C{row_num}'] = f'=Raw!C{row_num}*Raw!E{row_num}'
        model[f'D{row_num}'] = f'=Raw!D{row_num}*Raw!F{row_num}*0'
        model[f'E{row_num}'] = f'=Raw!G{row_num}'
        model[f'F{row_num}'] = f'=C{row_num}*Raw!I{row_num}'
        model[f'G{row_num}'] = f'=C{row_num}*0'
        model[f'H{row_num}'] = f'=C{row_num}-D{row_num}'
        model[f'I{row_num}'] = f'=H{row_num}+E{row_num}'
        model[f'J{row_num}'] = f'=I{row_num}/0'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'unit_economics.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {
                'task_id': 'formula_repair/task_002_fix_unit_economics_formulas',
                'target_file': 'unit_economics.xlsx',
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
