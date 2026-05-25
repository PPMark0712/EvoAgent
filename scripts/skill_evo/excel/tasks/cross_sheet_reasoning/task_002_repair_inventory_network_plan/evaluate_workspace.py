import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 6, 14, 31, 67, 103, 141, 176, 205, 221]
STATIC_CELLS = {'Demand': ['A1', 'B1', 'C1', 'D1'], 'Supply': ['A1', 'B1', 'C1', 'D1'], 'Plan': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Demand'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}'])
    STATIC_CELLS['Supply'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}'])
    STATIC_CELLS['Plan'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Plan': {}}
    for row_num in SAMPLE_ROWS:
        _sku, _region, forecast_units, backlog_units, yield_rate, unit_cost, expedite_rate = rows[row_num - 2]
        demand_units = forecast_units + backlog_units
        production_units = demand_units / yield_rate
        base_spend = production_units * unit_cost
        expedite_spend = base_spend * expedite_rate
        total_spend = base_spend + expedite_spend
        expected['Plan'][f'C{row_num}'] = demand_units
        expected['Plan'][f'D{row_num}'] = production_units
        expected['Plan'][f'E{row_num}'] = base_spend
        expected['Plan'][f'F{row_num}'] = expedite_spend
        expected['Plan'][f'G{row_num}'] = total_spend
        expected['Plan'][f'H{row_num}'] = 0 if demand_units == 0 else total_spend / demand_units
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'inventory_network_plan.xlsx')
    gold_file = os.path.join(args.gold_path, 'inventory_network_plan.xlsx')
    evaluator = Evaluator('cross_sheet_reasoning/task_002_repair_inventory_network_plan', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Demand')
        evaluator.compare_sheet_dimension('Supply')
        evaluator.compare_sheet_dimension('Plan')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cross sheet reasoning workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
