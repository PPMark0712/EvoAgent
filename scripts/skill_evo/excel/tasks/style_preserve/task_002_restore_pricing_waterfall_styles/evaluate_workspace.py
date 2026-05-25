import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import GUIDE_ROW_COUNT, build_rows


SAMPLE_ROWS = [2, 6, 12, 24, 39, 77, 108, 142, 181]
VALUE_CELLS = {
    'StyleGuide': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1'],
    'Waterfall': ['A1', 'B1', 'C1', 'D1', 'F1', 'G1'],
}
STYLE_CELLS = {'Waterfall': ['E1', 'H1', 'I1']}
for row_num in SAMPLE_ROWS:
    VALUE_CELLS['StyleGuide'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']])
    VALUE_CELLS['Waterfall'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'F', 'G']])
    STYLE_CELLS['Waterfall'].extend([f'E{row_num}', f'H{row_num}', f'I{row_num}'])


def build_expected_formulas():
    rows = build_rows(180, GUIDE_ROW_COUNT + 1)
    expected = {'Waterfall': {}}
    for row_num in SAMPLE_ROWS:
        _product, _region, list_price, discount, _net_price, units, unit_cost, _revenue, _gross_margin = rows[row_num - 2]
        net_price = list_price * (1 - discount)
        revenue = net_price * units
        gross_margin = 0 if revenue == 0 else (revenue - units * unit_cost) / revenue
        expected['Waterfall'][f'E{row_num}'] = net_price
        expected['Waterfall'][f'H{row_num}'] = revenue
        expected['Waterfall'][f'I{row_num}'] = gross_margin
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'pricing_waterfall_style.xlsx')
    gold_file = os.path.join(args.gold_path, 'pricing_waterfall_style.xlsx')
    evaluator = Evaluator('style_preserve/task_002_restore_pricing_waterfall_styles', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('StyleGuide')
        evaluator.compare_sheet_dimension('Waterfall')
        evaluator.compare_selected_cells(VALUE_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
        evaluator.compare_cell_styles(STYLE_CELLS, normalize_number_formats=True, compare_font_color=True, compare_alignment=True)
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate style preserve workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
