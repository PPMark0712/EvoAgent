import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 4, 10, 23, 61, 97, 134, 169, 208, 221]
STATIC_CELLS = {'Orders': ['A1', 'B1', 'C1'], 'Pricing': ['A1', 'B1', 'C1'], 'Costs': ['A1', 'B1', 'C1'], 'Bridge': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Orders'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['Pricing'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['Costs'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['Bridge'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Bridge': {}}
    for row_num in SAMPLE_ROWS:
        _order_id, _region, units, asp, discount_rate, unit_cost, support_cost = rows[row_num - 2]
        gross_revenue = units * asp
        discount_loss = gross_revenue * discount_rate
        net_revenue = gross_revenue - discount_loss
        cogs = units * unit_cost
        contribution = net_revenue - cogs - support_cost
        expected['Bridge'][f'C{row_num}'] = gross_revenue
        expected['Bridge'][f'D{row_num}'] = discount_loss
        expected['Bridge'][f'E{row_num}'] = net_revenue
        expected['Bridge'][f'F{row_num}'] = cogs
        expected['Bridge'][f'G{row_num}'] = contribution
        expected['Bridge'][f'H{row_num}'] = 0 if net_revenue == 0 else contribution / net_revenue
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'multi_sheet_margin_bridge.xlsx')
    gold_file = os.path.join(args.gold_path, 'multi_sheet_margin_bridge.xlsx')
    evaluator = Evaluator('cross_sheet_reasoning/task_003_repair_multi_sheet_margin_bridge', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Orders')
        evaluator.compare_sheet_dimension('Pricing')
        evaluator.compare_sheet_dimension('Costs')
        evaluator.compare_sheet_dimension('Bridge')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cross sheet reasoning workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
