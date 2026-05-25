import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 5, 18, 37, 66, 104, 143, 177, 205, 221]
STATIC_CELLS = {
    'Orders': ['A1', 'B1', 'C1'],
    'PriceBook': ['A1', 'B1', 'C1'],
    'Rebates': ['A1', 'B1', 'C1'],
    'Terms': ['A1', 'B1', 'C1'],
    'MarginStack': ['A1', 'B1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Orders'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['PriceBook'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['Rebates'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['Terms'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['MarginStack'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'MarginStack': {}}
    for row_num in SAMPLE_ROWS:
        _order_id, _region, units, asp, discount_rate, rebate_rate, service_attach, renewal_rate, support_cost_per_unit = rows[row_num - 2]
        gross_revenue = units * asp
        discount_loss = gross_revenue * discount_rate
        rebate_loss = gross_revenue * rebate_rate
        net_revenue = (gross_revenue - discount_loss - rebate_loss) * renewal_rate
        services_arr = net_revenue * service_attach
        final_arr = net_revenue + services_arr
        final_margin = 0 if final_arr == 0 else (final_arr - units * support_cost_per_unit) / final_arr
        expected['MarginStack'][f'C{row_num}'] = gross_revenue
        expected['MarginStack'][f'D{row_num}'] = discount_loss
        expected['MarginStack'][f'E{row_num}'] = rebate_loss
        expected['MarginStack'][f'F{row_num}'] = net_revenue
        expected['MarginStack'][f'G{row_num}'] = services_arr
        expected['MarginStack'][f'H{row_num}'] = final_arr
        expected['MarginStack'][f'I{row_num}'] = final_margin
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'hidden_helper_margin_stack.xlsx')
    gold_file = os.path.join(args.gold_path, 'hidden_helper_margin_stack.xlsx')
    evaluator = Evaluator('cross_sheet_reasoning/task_004_repair_hidden_helper_margin_stack', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        for sheet in ['Orders', 'PriceBook', 'Rebates', 'Terms', 'MarginStack']:
            evaluator.compare_sheet_dimension(sheet)
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate hard cross sheet reasoning task')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
