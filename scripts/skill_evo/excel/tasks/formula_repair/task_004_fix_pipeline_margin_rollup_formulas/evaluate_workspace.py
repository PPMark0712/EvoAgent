import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 3, 15, 41, 79, 118, 157, 193, 221]
STATIC_CELLS = {
    'Pipeline': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Rollup': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Pipeline'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Rollup'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Rollup': {}}
    for row_num in SAMPLE_ROWS:
        _, _, _, bookings, _, commission_rate, support_cost, expansion_revenue, discount_rate, renewal_probability = rows[row_num - 2]
        gross_revenue = bookings + expansion_revenue
        commission_cost = bookings * commission_rate
        discount_loss = gross_revenue * discount_rate
        weighted_revenue = (gross_revenue - discount_loss) * renewal_probability
        net_margin = weighted_revenue - commission_cost - support_cost
        margin_pct = 0 if weighted_revenue == 0 else net_margin / weighted_revenue
        expected_expansion = expansion_revenue * renewal_probability
        expected['Rollup'][f'C{row_num}'] = gross_revenue
        expected['Rollup'][f'D{row_num}'] = commission_cost
        expected['Rollup'][f'E{row_num}'] = support_cost
        expected['Rollup'][f'F{row_num}'] = discount_loss
        expected['Rollup'][f'G{row_num}'] = weighted_revenue
        expected['Rollup'][f'H{row_num}'] = net_margin
        expected['Rollup'][f'I{row_num}'] = margin_pct
        expected['Rollup'][f'J{row_num}'] = expected_expansion
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'pipeline_margin_rollup.xlsx')
    gold_file = os.path.join(args.gold_path, 'pipeline_margin_rollup.xlsx')
    evaluator = Evaluator('formula_repair/task_004_fix_pipeline_margin_rollup_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Pipeline')
        evaluator.compare_sheet_dimension('Rollup')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate formula repair workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
