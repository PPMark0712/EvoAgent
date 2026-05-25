import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import RATE_VALUES, ROW_COUNT, canonical_rows


TOTAL_ROW = ROW_COUNT + 2
SAMPLE_ROWS = [2, 9, 31, 62, 96, 134, 173, 205, 221]
STATIC_CELLS = {
    'Transactions': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Rates': ['A1', 'B1', 'A2', 'B2', 'A3', 'B3'],
    'Summary': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', f'A{TOTAL_ROW}', f'B{TOTAL_ROW}'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Transactions'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Summary'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Summary': {}}
    tax_rate = RATE_VALUES['Tax Rate']
    support_multiplier = RATE_VALUES['Support Multiplier']
    totals = {col: 0 for col in 'CDEFGHIJK'}
    for row_num in SAMPLE_ROWS:
        _, _, gross_sales, returns, discount_rate, orders, cogs_per_order, shipping_per_order, support_per_order, _ = rows[row_num - 2]
        gross_revenue = gross_sales - returns
        discount_loss = gross_revenue * discount_rate
        net_revenue = gross_revenue - discount_loss
        cogs = orders * cogs_per_order
        fulfillment = orders * shipping_per_order
        support_cost = orders * support_per_order * support_multiplier
        operating_profit = net_revenue - cogs - fulfillment - support_cost
        tax_expense = 0 if operating_profit <= 0 else operating_profit * tax_rate
        net_profit = operating_profit - tax_expense
        expected['Summary'][f'C{row_num}'] = gross_revenue
        expected['Summary'][f'D{row_num}'] = discount_loss
        expected['Summary'][f'E{row_num}'] = net_revenue
        expected['Summary'][f'F{row_num}'] = cogs
        expected['Summary'][f'G{row_num}'] = fulfillment
        expected['Summary'][f'H{row_num}'] = support_cost
        expected['Summary'][f'I{row_num}'] = operating_profit
        expected['Summary'][f'J{row_num}'] = tax_expense
        expected['Summary'][f'K{row_num}'] = net_profit
    for _, _, gross_sales, returns, discount_rate, orders, cogs_per_order, shipping_per_order, support_per_order, _ in rows:
        gross_revenue = gross_sales - returns
        discount_loss = gross_revenue * discount_rate
        net_revenue = gross_revenue - discount_loss
        cogs = orders * cogs_per_order
        fulfillment = orders * shipping_per_order
        support_cost = orders * support_per_order * support_multiplier
        operating_profit = net_revenue - cogs - fulfillment - support_cost
        tax_expense = 0 if operating_profit <= 0 else operating_profit * tax_rate
        net_profit = operating_profit - tax_expense
        totals['C'] += gross_revenue
        totals['D'] += discount_loss
        totals['E'] += net_revenue
        totals['F'] += cogs
        totals['G'] += fulfillment
        totals['H'] += support_cost
        totals['I'] += operating_profit
        totals['J'] += tax_expense
        totals['K'] += net_profit
    for col in 'CDEFGHIJK':
        expected['Summary'][f'{col}{TOTAL_ROW}'] = totals[col]
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'operating_profit_summary.xlsx')
    gold_file = os.path.join(args.gold_path, 'operating_profit_summary.xlsx')
    evaluator = Evaluator('formula_repair/task_007_fix_operating_profit_summary_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Transactions')
        evaluator.compare_sheet_dimension('Rates')
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
