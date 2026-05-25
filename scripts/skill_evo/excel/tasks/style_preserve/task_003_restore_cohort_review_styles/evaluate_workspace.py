import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import GUIDE_ROW_COUNT, build_rows


SAMPLE_ROWS = [2, 8, 17, 35, 52, 88, 119, 151, 181]
VALUE_CELLS = {
    'Template': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1'],
    'Cohorts': ['A1', 'B1', 'C1', 'D1', 'E1'],
}
STYLE_CELLS = {'Cohorts': ['F1', 'G1']}
for row_num in SAMPLE_ROWS:
    VALUE_CELLS['Template'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']])
    VALUE_CELLS['Cohorts'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E']])
    STYLE_CELLS['Cohorts'].extend([f'F{row_num}', f'G{row_num}'])


def build_expected_formulas():
    rows = build_rows(180, GUIDE_ROW_COUNT + 1)
    expected = {'Cohorts': {}}
    for row_num in SAMPLE_ROWS:
        _cohort, _region, start_mrr, expansion, churn = rows[row_num - 2]
        end_mrr = start_mrr * (1 + expansion - churn)
        expected['Cohorts'][f'F{row_num}'] = end_mrr
        expected['Cohorts'][f'G{row_num}'] = 0 if start_mrr == 0 else end_mrr / start_mrr
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'cohort_review_style.xlsx')
    gold_file = os.path.join(args.gold_path, 'cohort_review_style.xlsx')
    evaluator = Evaluator('style_preserve/task_003_restore_cohort_review_styles', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Template')
        evaluator.compare_sheet_dimension('Cohorts')
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
