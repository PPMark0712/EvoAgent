import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator


GUIDE_SAMPLE_ROWS = [2, 6, 12, 21]
TARGET_SAMPLE_ROWS = [2, 5, 41, 96, 141, 186, 201]
VALUE_CELLS = {
    'Reference Layout': ['A1', 'B1', 'C1', 'D1', 'E1'],
    'Launch Queue': ['A1', 'B1', 'C1', 'D1', 'E1'],
}
STYLE_CELLS = {
    'Reference Layout': ['A1', 'B1', 'C1', 'D1', 'E1'],
    'Launch Queue': ['A1', 'B1', 'C1', 'D1', 'E1'],
}
for row_num in GUIDE_SAMPLE_ROWS:
    VALUE_CELLS['Reference Layout'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
    STYLE_CELLS['Reference Layout'].extend([f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
for row_num in TARGET_SAMPLE_ROWS:
    VALUE_CELLS['Launch Queue'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
    STYLE_CELLS['Launch Queue'].extend([f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])


def main(args):
    target_file = os.path.join(args.workspace_path, 'campaign_launch_queue.xlsx')
    gold_file = os.path.join(args.gold_path, 'campaign_launch_queue.xlsx')
    evaluator = Evaluator('cell_formatting/task_005_copy_campaign_layout_from_reference_sheet', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Reference Layout')
        evaluator.compare_sheet_dimension('Launch Queue')
        evaluator.compare_selected_cells(VALUE_CELLS)
        evaluator.compare_cell_styles(STYLE_CELLS, normalize_number_formats=True, compare_font_color=True, compare_alignment=True)
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cell formatting workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
