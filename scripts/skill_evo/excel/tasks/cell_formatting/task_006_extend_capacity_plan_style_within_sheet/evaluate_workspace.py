import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator


REFERENCE_SAMPLE_ROWS = [1, 2, 6, 12, 21]
TARGET_SAMPLE_ROWS = [24, 25, 29, 63, 118, 173, 224]
VALUE_CELLS = {'Capacity Plan': ['A22', 'A23']}
STYLE_CELLS = {'Capacity Plan': []}
for row_num in REFERENCE_SAMPLE_ROWS:
    VALUE_CELLS['Capacity Plan'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
for row_num in TARGET_SAMPLE_ROWS:
    VALUE_CELLS['Capacity Plan'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
for row_num in [1, 2, 6, 12, 21, 24, 25, 29, 63, 118, 173, 224]:
    STYLE_CELLS['Capacity Plan'].extend([f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
STYLE_CELLS['Capacity Plan'].extend(['A1', 'A24'])


def main(args):
    target_file = os.path.join(args.workspace_path, 'quarterly_capacity_plan.xlsx')
    gold_file = os.path.join(args.gold_path, 'quarterly_capacity_plan.xlsx')
    evaluator = Evaluator('cell_formatting/task_006_extend_capacity_plan_style_within_sheet', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Capacity Plan')
        evaluator.compare_selected_cells(VALUE_CELLS)
        evaluator.compare_cell_styles(STYLE_CELLS, normalize_number_formats=True, compare_font_color=True, compare_alignment=True)
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cell formatting workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
