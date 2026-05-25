import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import BLOCK_SIZE, SEGMENTS, TARGETS, canonical_rows


SAMPLE_ROWS = [2, 6, 19, 41, 73, 109, 145, 181, 207, 221]
STATIC_CELLS = {
    'Drivers': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1'],
    'Adjustments': ['A1', 'B1', 'C1'],
    'Targets': ['A1', 'B1', 'C1', 'A2', 'A3', 'A4', 'A5'],
    'OperatingModel': ['A1', 'B1'],
    'Dashboard': ['A1', 'B1', 'C1', 'D1', 'A2', 'A3', 'A4', 'A5'],
    'Alerts': ['A1', 'B1', 'C1', 'A2', 'A3', 'A4', 'A5'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Drivers'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}'])
    STATIC_CELLS['Adjustments'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}'])
    STATIC_CELLS['OperatingModel'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'OperatingModel': {}, 'Dashboard': {}, 'Alerts': {}}
    for row_num in SAMPLE_ROWS:
        _account_id, _segment, starting_arr, collection_rate, service_cost_rate, headcount_cost, expansion_rate, churn_rate = rows[row_num - 2]
        ending_arr = starting_arr * (1 + expansion_rate - churn_rate)
        cash_in = ending_arr * collection_rate
        service_cost = ending_arr * service_cost_rate
        ebitda = cash_in - service_cost - headcount_cost
        margin = 0 if cash_in == 0 else ebitda / cash_in
        expected['OperatingModel'][f'C{row_num}'] = ending_arr
        expected['OperatingModel'][f'D{row_num}'] = cash_in
        expected['OperatingModel'][f'E{row_num}'] = service_cost
        expected['OperatingModel'][f'F{row_num}'] = ebitda
        expected['OperatingModel'][f'G{row_num}'] = margin

    for idx, segment in enumerate(SEGMENTS, start=2):
        segment_rows = [row for row in rows if row[1] == segment]
        total_ending_arr = 0
        total_ebitda = 0
        margin_values = []
        for _account_id, _segment, starting_arr, collection_rate, service_cost_rate, headcount_cost, expansion_rate, churn_rate in segment_rows:
            ending_arr = starting_arr * (1 + expansion_rate - churn_rate)
            cash_in = ending_arr * collection_rate
            service_cost = ending_arr * service_cost_rate
            ebitda = cash_in - service_cost - headcount_cost
            total_ending_arr += ending_arr
            total_ebitda += ebitda
            margin_values.append(0 if cash_in == 0 else ebitda / cash_in)
        avg_margin = sum(margin_values) / BLOCK_SIZE
        min_arr, min_margin = TARGETS[segment]
        expected['Dashboard'][f'B{idx}'] = total_ending_arr
        expected['Dashboard'][f'C{idx}'] = total_ebitda
        expected['Dashboard'][f'D{idx}'] = avg_margin
        expected['Alerts'][f'B{idx}'] = 'ALERT' if avg_margin < min_margin else 'OK'
        expected['Alerts'][f'C{idx}'] = 'ALERT' if total_ending_arr < min_arr else 'OK'
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'exec_dashboard_audit.xlsx')
    gold_file = os.path.join(args.gold_path, 'exec_dashboard_audit.xlsx')
    evaluator = Evaluator('workbook_audit/task_004_audit_exec_dashboard_with_hidden_breaks', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        for sheet in ['Drivers', 'Adjustments', 'Targets', 'OperatingModel', 'Dashboard', 'Alerts']:
            evaluator.compare_sheet_dimension(sheet)
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate hard workbook audit task')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
