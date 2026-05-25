import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator


TARGET_SAMPLE_ROWS = [1, 2, 7, 39, 84, 133, 177, 201]
REFERENCE_SAMPLE_ROWS = [1, 2, 5, 11, 21]
VALUE_CELLS = {'Exceptions': ['G23', 'G24']}
STYLE_CELLS = {'Exceptions': []}
for row_num in TARGET_SAMPLE_ROWS:
    VALUE_CELLS['Exceptions'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
for row_num in REFERENCE_SAMPLE_ROWS:
    VALUE_CELLS['Exceptions'].extend([f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}', f'K{row_num}'])
for row_num in TARGET_SAMPLE_ROWS:
    STYLE_CELLS['Exceptions'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
for row_num in REFERENCE_SAMPLE_ROWS:
    STYLE_CELLS['Exceptions'].extend([f'G{row_num}', f'H{row_num}', f'I{row_num}', f'J{row_num}', f'K{row_num}'])


def main(args):
    target_file = os.path.join(args.workspace_path, 'renewal_exception_log.xlsx')
    gold_file = os.path.join(args.gold_path, 'renewal_exception_log.xlsx')
    evaluator = Evaluator('cell_formatting/task_007_extend_exception_log_style_within_sheet', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Exceptions')
        evaluator.compare_selected_cells(VALUE_CELLS)
        evaluator.compare_cell_styles(STYLE_CELLS, normalize_number_formats=True, compare_font_color=True, compare_alignment=True)
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cell formatting workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
