import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import canonical_rows


SAMPLE_ROWS = [2, 3, 11, 27, 57, 94, 111, 166, 198, 221]
STATIC_CELLS = {
    'Inputs': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
    'Forecast': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Inputs'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])
    STATIC_CELLS['Forecast'].extend([f'A{row_num}', f'B{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Forecast': {}}
    for row_num in SAMPLE_ROWS:
        _, _, jan_units, jan_price, feb_units, feb_price, mar_units, mar_price, apr_units, apr_price = rows[row_num - 2]
        jan_revenue = jan_units * jan_price
        feb_revenue = feb_units * feb_price
        mar_revenue = mar_units * mar_price
        apr_revenue = apr_units * apr_price
        expected['Forecast'][f'C{row_num}'] = jan_revenue
        expected['Forecast'][f'D{row_num}'] = feb_revenue
        expected['Forecast'][f'E{row_num}'] = mar_revenue
        expected['Forecast'][f'F{row_num}'] = apr_revenue
        expected['Forecast'][f'G{row_num}'] = jan_revenue + feb_revenue + mar_revenue + apr_revenue
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'forecast_model.xlsx')
    gold_file = os.path.join(args.gold_path, 'forecast_model.xlsx')
    evaluator = Evaluator('formula_repair/task_001_fix_forecast_formulas', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Inputs')
        evaluator.compare_sheet_dimension('Forecast')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate formula repair workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
