import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
BLOCK_SIZE = 55
BLOCK_LABELS = ['North', 'South', 'East', 'West']
REORDER_STEP = 37
ZERO_NET_ROWS = {1, 48, 109, 173}


def canonical_rows():
    grouped_rows = []
    for idx in range(ROW_COUNT):
        region = BLOCK_LABELS[idx // BLOCK_SIZE]
        account_id = f'ACC-{idx + 1:03d}'
        bookings = 3200 + idx * 37
        discount_rate = round(0.02 + (idx % 5) * 0.01, 4)
        cogs_rate = round(0.28 + (idx % 4) * 0.03, 4)
        opex = 410 + (idx % 7) * 35
        if idx + 1 in ZERO_NET_ROWS:
            bookings = 0
            discount_rate = 0
        grouped_rows.append((account_id, region, bookings, discount_rate, cogs_rate, opex))
    return [grouped_rows[(idx * REORDER_STEP) % ROW_COUNT] for idx in range(ROW_COUNT)]


def build_workbook(output_file):
    wb = Workbook()
    inputs = wb.active
    inputs.title = 'Drivers'
    inputs.append(['Account ID', 'Region', 'Bookings', 'Discount Rate', 'COGS Rate', 'Opex'])
    for cell in inputs[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        inputs.append(list(row))

    detail = wb.create_sheet('PnL')
    detail.append(['Account ID', 'Region', 'Gross Revenue', 'Discount Loss', 'Net Revenue', 'COGS', 'Gross Profit', 'Opex', 'Operating Income', 'Operating Margin'])
    for cell in detail[1]:
        cell.font = Font(bold=True)
    for row_num in range(2, ROW_COUNT + 2):
        detail[f'A{row_num}'] = f'=Drivers!A{row_num}'
        detail[f'B{row_num}'] = f'=Drivers!B{row_num}'
        gross_source_row = row_num if row_num not in (2, ROW_COUNT + 1) else min(ROW_COUNT + 1, row_num + 1)
        detail[f'C{row_num}'] = f'=Drivers!C{gross_source_row}'
        detail[f'D{row_num}'] = f'=C{row_num}*Drivers!E{row_num}'
        detail[f'E{row_num}'] = f'=C{row_num}+D{row_num}'
        detail[f'F{row_num}'] = f'=Drivers!F{row_num}'
        detail[f'G{row_num}'] = f'=E{row_num}+F{row_num}'
        detail[f'H{row_num}'] = f'=Drivers!D{row_num}'
        detail[f'I{row_num}'] = f'=G{row_num}-H{row_num}'
        detail[f'J{row_num}'] = f'=I{row_num}/E{row_num}'

    summary = wb.create_sheet('Summary')
    summary.append(['Region', 'Total Net Revenue', 'Total Operating Income', 'Operating Margin'])
    for cell in summary[1]:
        cell.font = Font(bold=True)
    for idx, label in enumerate(BLOCK_LABELS, start=2):
        summary[f'A{idx}'] = label
        start = 2 + (idx - 2) * BLOCK_SIZE
        end = start + BLOCK_SIZE - 1
        summary[f'B{idx}'] = f'=SUM(PnL!C{start}:C{end})'
        summary[f'C{idx}'] = f'=SUM(PnL!G{start}:G{end})'
        summary[f'D{idx}'] = f'=C{idx}/B{idx}'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'regional_pnl_audit.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump({'task_id': 'workbook_audit/task_001_audit_regional_pnl_workbook', 'target_file': 'regional_pnl_audit.xlsx'}, f, ensure_ascii=False, indent=2)
    print(os.path.abspath(args.output_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create workspace for workbook audit task')
    parser.add_argument('output_path', help='Directory to create workspace in')
    main(parser.parse_args())
