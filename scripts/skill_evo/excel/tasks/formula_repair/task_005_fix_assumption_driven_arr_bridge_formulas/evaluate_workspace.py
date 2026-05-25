import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import ASSUMPTION_VALUES, ROW_COUNT, canonical_rows


SAMPLE_ROWS = [2, 8, 29, 56, 91, 127, 164, 201, 221]
STATIC_CELLS = {
    'Accounts': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Assumptions': ['A1', 'B1', 'A2', 'B2', 'A3', 'B3', 'A4', 'B4', 'A5', 'B5'],
    'Bridge': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Accounts'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Bridge'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Bridge': {}}
    upsell_rate = ASSUMPTION_VALUES['Upsell Rate']
    risk_discount = ASSUMPTION_VALUES['Risk Discount']
    support_cost_per_hour = ASSUMPTION_VALUES['Cost per Support Hour']
    retention_bonus = ASSUMPTION_VALUES['Retention Bonus']
    for row_num in SAMPLE_ROWS:
        _, _, current_arr, expansion_arr, churned_arr, renewal_probability, support_hours, fee_rate, growth_uplift, onboarding_credit = rows[row_num - 2]
        gross_arr = current_arr + expansion_arr
        renewal_arr = (current_arr - churned_arr) * renewal_probability
        upsell_arr = gross_arr * upsell_rate * (1 + growth_uplift)
        risk_adjusted_arr = (renewal_arr + upsell_arr) * (1 - risk_discount)
        support_cost = support_hours * support_cost_per_hour
        payment_fees = risk_adjusted_arr * fee_rate
        net_arr = risk_adjusted_arr - support_cost - payment_fees + onboarding_credit + retention_bonus
        margin = 0 if risk_adjusted_arr == 0 else net_arr / risk_adjusted_arr
        expected['Bridge'][f'C{row_num}'] = gross_arr
        expected['Bridge'][f'D{row_num}'] = renewal_arr
        expected['Bridge'][f'E{row_num}'] = upsell_arr
        expected['Bridge'][f'F{row_num}'] = risk_adjusted_arr
        expected['Bridge'][f'G{row_num}'] = support_cost
        expected['Bridge'][f'H{row_num}'] = payment_fees
        expected['Bridge'][f'I{row_num}'] = net_arr
        expected['Bridge'][f'J{row_num}'] = margin
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'arr_bridge.xlsx')
    gold_file = os.path.join(args.gold_path, 'arr_bridge.xlsx')
    evaluator = Evaluator('formula_repair/task_005_fix_assumption_driven_arr_bridge_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Accounts')
        evaluator.compare_sheet_dimension('Assumptions')
        evaluator.compare_sheet_dimension('Bridge')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate formula repair workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
