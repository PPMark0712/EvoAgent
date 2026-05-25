import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import ROW_COUNT, canonical_rows


TOTAL_ROW = ROW_COUNT + 2
SAMPLE_ROWS = [2, 5, 19, 48, 83, 117, 154, 189, 221]
STATIC_CELLS = {
    'Subscribers': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Summary': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', f'A{TOTAL_ROW}', f'B{TOTAL_ROW}'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Subscribers'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Summary'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Summary': {}}
    totals = {key: 0 for key in 'CDEFGHI'}
    retention_values = []
    for row_num in SAMPLE_ROWS:
        _, _, starting_subs, new_subs, reactivated, churned, arpu, support_cost, fee_rate, setup_fee = rows[row_num - 2]
        ending_subs = starting_subs + new_subs + reactivated - churned
        gross_adds = new_subs + reactivated
        lost_subs = churned
        subscription_revenue = ending_subs * arpu + setup_fee
        support_total = ending_subs * support_cost
        payment_fees = subscription_revenue * fee_rate
        net_revenue = subscription_revenue - support_total - payment_fees
        retention = 0 if starting_subs == 0 else ending_subs / starting_subs
        expected['Summary'][f'C{row_num}'] = ending_subs
        expected['Summary'][f'D{row_num}'] = gross_adds
        expected['Summary'][f'E{row_num}'] = lost_subs
        expected['Summary'][f'F{row_num}'] = subscription_revenue
        expected['Summary'][f'G{row_num}'] = support_total
        expected['Summary'][f'H{row_num}'] = payment_fees
        expected['Summary'][f'I{row_num}'] = net_revenue
        expected['Summary'][f'J{row_num}'] = retention
    for _, _, starting_subs, new_subs, reactivated, churned, arpu, support_cost, fee_rate, setup_fee in rows:
        ending_subs = starting_subs + new_subs + reactivated - churned
        gross_adds = new_subs + reactivated
        lost_subs = churned
        subscription_revenue = ending_subs * arpu + setup_fee
        support_total = ending_subs * support_cost
        payment_fees = subscription_revenue * fee_rate
        net_revenue = subscription_revenue - support_total - payment_fees
        totals['C'] += ending_subs
        totals['D'] += gross_adds
        totals['E'] += lost_subs
        totals['F'] += subscription_revenue
        totals['G'] += support_total
        totals['H'] += payment_fees
        totals['I'] += net_revenue
        retention_values.append(0 if starting_subs == 0 else ending_subs / starting_subs)
    for col in 'CDEFGHI':
        expected['Summary'][f'{col}{TOTAL_ROW}'] = totals[col]
    expected['Summary'][f'J{TOTAL_ROW}'] = sum(retention_values) / len(retention_values)
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'subscription_report.xlsx')
    gold_file = os.path.join(args.gold_path, 'subscription_report.xlsx')
    evaluator = Evaluator('formula_repair/task_003_fix_subscription_summary_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Subscribers')
        evaluator.compare_sheet_dimension('Summary')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate formula repair workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
