import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 7, 24, 53, 88, 124, 161, 199, 221]
STATIC_CELLS = {
    'Drivers': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Plan': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', 'L1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Drivers'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Plan'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Plan': {}}
    for row_num in SAMPLE_ROWS:
        _, _, q1_units, q1_price, q2_units, q2_price, q3_unit_growth, q4_unit_growth, q3_price_lift, q4_price_lift = rows[row_num - 2]
        q2_revenue = q2_units * q2_price
        q3_units = q2_units * (1 + q3_unit_growth)
        q3_price = q2_price * (1 + q3_price_lift)
        q3_revenue = q3_units * q3_price
        q4_units = q3_units * (1 + q4_unit_growth)
        q4_price = q3_price * (1 + q4_price_lift)
        q4_revenue = q4_units * q4_price
        h2_revenue = q3_revenue + q4_revenue
        h2_growth = 0 if q2_revenue == 0 else (h2_revenue - q2_revenue) / q2_revenue
        expected['Plan'][f'E{row_num}'] = q3_units
        expected['Plan'][f'F{row_num}'] = q3_price
        expected['Plan'][f'G{row_num}'] = q3_revenue
        expected['Plan'][f'H{row_num}'] = q4_units
        expected['Plan'][f'I{row_num}'] = q4_price
        expected['Plan'][f'J{row_num}'] = q4_revenue
        expected['Plan'][f'K{row_num}'] = h2_revenue
        expected['Plan'][f'L{row_num}'] = h2_growth
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'quarterly_plan.xlsx')
    gold_file = os.path.join(args.gold_path, 'quarterly_plan.xlsx')
    evaluator = Evaluator('formula_repair/task_006_extend_quarterly_plan_forecast_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Drivers')
        evaluator.compare_sheet_dimension('Plan')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate formula repair workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
