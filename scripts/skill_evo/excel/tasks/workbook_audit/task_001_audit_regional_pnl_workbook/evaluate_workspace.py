import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import BLOCK_LABELS, canonical_rows


SAMPLE_ROWS = [2, 3, 11, 27, 48, 58, 94, 109, 173, 221]
STATIC_CELLS = {
    'Drivers': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1'],
    'PnL': ['A1', 'B1'],
    'Summary': ['A1', 'B1', 'C1', 'D1', 'A2', 'A3', 'A4', 'A5'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Drivers'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F']])
    STATIC_CELLS['PnL'].extend([f'{col}{row_num}' for col in ['A', 'B']])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'PnL': {}, 'Summary': {}}
    for row_num in SAMPLE_ROWS:
        _, _, bookings, discount_rate, cogs_rate, opex = rows[row_num - 2]
        discount_loss = bookings * discount_rate
        net_revenue = bookings - discount_loss
        cogs = net_revenue * cogs_rate
        gross_profit = net_revenue - cogs
        operating_income = gross_profit - opex
        expected['PnL'][f'C{row_num}'] = bookings
        expected['PnL'][f'D{row_num}'] = discount_loss
        expected['PnL'][f'E{row_num}'] = net_revenue
        expected['PnL'][f'F{row_num}'] = cogs
        expected['PnL'][f'G{row_num}'] = gross_profit
        expected['PnL'][f'H{row_num}'] = opex
        expected['PnL'][f'I{row_num}'] = operating_income
        expected['PnL'][f'J{row_num}'] = 0 if net_revenue == 0 else operating_income / net_revenue
    for idx, label in enumerate(BLOCK_LABELS, start=2):
        label_rows = [row for row in rows if row[1] == label]
        total_net_revenue = 0
        total_operating_income = 0
        for _, _, bookings, discount_rate, cogs_rate, opex in label_rows:
            discount_loss = bookings * discount_rate
            net_revenue = bookings - discount_loss
            cogs = net_revenue * cogs_rate
            gross_profit = net_revenue - cogs
            operating_income = gross_profit - opex
            total_net_revenue += net_revenue
            total_operating_income += operating_income
        expected['Summary'][f'B{idx}'] = total_net_revenue
        expected['Summary'][f'C{idx}'] = total_operating_income
        expected['Summary'][f'D{idx}'] = 0 if total_net_revenue == 0 else total_operating_income / total_net_revenue
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'regional_pnl_audit.xlsx')
    gold_file = os.path.join(args.gold_path, 'regional_pnl_audit.xlsx')
    evaluator = Evaluator('workbook_audit/task_001_audit_regional_pnl_workbook', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Drivers')
        evaluator.compare_sheet_dimension('PnL')
        evaluator.compare_sheet_dimension('Summary')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate workbook audit workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
