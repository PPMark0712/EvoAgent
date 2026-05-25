import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import GUIDE_ROW_COUNT, build_rows


SAMPLE_ROWS = [2, 5, 11, 27, 44, 72, 94, 139, 181]
VALUE_CELLS = {
    'Reference': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'],
    'BoardKPI': ['A1', 'B1', 'C1', 'D1', 'G1', 'H1'],
}
STYLE_CELLS = {'BoardKPI': ['E1', 'F1', 'G1', 'H1']}
VIEW_CHECKS = {'BoardKPI': {'freeze_panes': True, 'auto_filter': True}}
COLUMN_CHECKS = {'BoardKPI': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']}
ROW_CHECKS = {'BoardKPI': [1]}
for row_num in SAMPLE_ROWS:
    VALUE_CELLS['Reference'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']])
    VALUE_CELLS['BoardKPI'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'G', 'H']])
    STYLE_CELLS['BoardKPI'].extend([f'E{row_num}', f'F{row_num}', f'G{row_num}', f'H{row_num}'])


def build_expected_formulas():
    rows = build_rows(180, GUIDE_ROW_COUNT + 1)
    expected = {'BoardKPI': {}}
    for row_num in SAMPLE_ROWS:
        _team, _region, q1, q2, _h1_revenue, _h1_growth, _renewal, _expansion = rows[row_num - 2]
        h1_revenue = q1 + q2
        expected['BoardKPI'][f'E{row_num}'] = h1_revenue
        expected['BoardKPI'][f'F{row_num}'] = 0 if q1 == 0 else h1_revenue / q1 - 1
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'board_kpi_style.xlsx')
    gold_file = os.path.join(args.gold_path, 'board_kpi_style.xlsx')
    evaluator = Evaluator('style_preserve/task_001_restore_board_kpi_styles_after_formula_fix', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Reference')
        evaluator.compare_sheet_dimension('BoardKPI')
        evaluator.compare_selected_cells(VALUE_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
        evaluator.compare_cell_styles(
            STYLE_CELLS,
            normalize_number_formats=True,
            compare_font_color=True,
            compare_alignment=True,
            compare_borders=True,
        )
        evaluator.compare_sheet_view_settings(VIEW_CHECKS)
        evaluator.compare_column_dimensions(COLUMN_CHECKS)
        evaluator.compare_row_dimensions(ROW_CHECKS)
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate style preserve workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
