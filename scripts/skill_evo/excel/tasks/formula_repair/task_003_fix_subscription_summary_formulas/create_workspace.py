import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
PLANS = ['Starter', 'Growth', 'Scale', 'Enterprise']
MONTHS = ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06']


def canonical_rows():
    rows = []
    for idx in range(ROW_COUNT):
        start_subs = 700 + (idx % 45) * 12
        new_subs = 45 + (idx % 18)
        reactivated = 5 + (idx % 7)
        churned = 20 + (idx % 11)
        arpu = 42 + (idx % 8) * 3
        support_cost = 6 + (idx % 5)
        fee_rate = 0.018 + (idx % 4) * 0.004
        setup_fee = 200 + (idx % 6) * 25
        rows.append((
            MONTHS[idx % len(MONTHS)],
            PLANS[idx % len(PLANS)],
            start_subs,
            new_subs,
            reactivated,
            churned,
            arpu,
            support_cost,
            fee_rate,
            setup_fee,
        ))
    return rows


def build_workbook(output_file):
    wb = Workbook()
    subs = wb.active
    subs.title = 'Subscribers'
    headers = [
        'Period',
        'Plan',
        'Starting Subs',
        'New Subs',
        'Reactivated Subs',
        'Churned Subs',
        'ARPU',
        'Support Cost per Sub',
        'Payment Fee Rate',
        'Setup Fee Revenue',
    ]
    subs.append(headers)
    for cell in subs[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        subs.append(list(row))

    summary = wb.create_sheet('Summary')
    summary_headers = [
        'Period',
        'Plan',
        'Ending Subs',
        'Gross Adds',
        'Lost Subs',
        'Subscription Revenue',
        'Support Cost',
        'Payment Fees',
        'Net Revenue',
        'ARPU Retention',
    ]
    summary.append(summary_headers)
    for cell in summary[1]:
        cell.font = Font(bold=True)
    for row_num in range(2, ROW_COUNT + 2):
        summary[f'A{row_num}'] = f'=Subscribers!A{row_num}'
        summary[f'B{row_num}'] = f'=Subscribers!B{row_num}'
        summary[f'C{row_num}'] = f'=Subscribers!C{row_num}+Subscribers!D{row_num}-Subscribers!F{row_num}'
        summary[f'D{row_num}'] = f'=Subscribers!D{row_num}'
        summary[f'E{row_num}'] = f'=Subscribers!C{row_num}'
        summary[f'F{row_num}'] = f'=C{row_num}*Subscribers!G{row_num}'
        summary[f'G{row_num}'] = f'=C{row_num}+Subscribers!H{row_num}'
        summary[f'H{row_num}'] = f'=F{row_num}*0'
        summary[f'I{row_num}'] = f'=F{row_num}-G{row_num}'
        summary[f'J{row_num}'] = f'=C{row_num}/0'
    summary[f'A{ROW_COUNT + 2}'] = 'Portfolio Total'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'subscription_report.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {
                'task_id': 'formula_repair/task_003_fix_subscription_summary_formulas',
                'target_file': 'subscription_report.xlsx',
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
