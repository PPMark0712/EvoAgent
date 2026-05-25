import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import BLOCK_LABELS, BLOCK_SIZE, canonical_rows


SAMPLE_ROWS = [2, 4, 12, 33, 71, 108, 146, 182, 214, 221]
STATIC_CELLS = {
    'Staffing': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1'],
    'Utilization': ['A1', 'B1'],
    'Dashboard': ['A1', 'B1', 'C1', 'D1', 'A2', 'A3', 'A4', 'A5'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Staffing'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F']])
    STATIC_CELLS['Utilization'].extend([f'{col}{row_num}' for col in ['A', 'B']])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'Utilization': {}, 'Dashboard': {}}
    for row_num in SAMPLE_ROWS:
        _team_id, _region, seats, occupancy_rate, revenue_per_occ_seat, support_cost_per_seat = rows[row_num - 2]
        occupied_seats = seats * occupancy_rate
        revenue = occupied_seats * revenue_per_occ_seat
        support_cost = seats * support_cost_per_seat
        contribution = revenue - support_cost
        expected['Utilization'][f'C{row_num}'] = occupied_seats
        expected['Utilization'][f'D{row_num}'] = revenue
        expected['Utilization'][f'E{row_num}'] = support_cost
        expected['Utilization'][f'F{row_num}'] = contribution
        expected['Utilization'][f'G{row_num}'] = 0 if seats == 0 else occupied_seats / seats
    for idx, label in enumerate(BLOCK_LABELS, start=2):
        label_rows = [row for row in rows if row[1] == label]
        total_revenue = 0
        total_contribution = 0
        utilization_values = []
        for _team_id, _region, seats, occupancy_rate, revenue_per_occ_seat, support_cost_per_seat in label_rows:
            occupied_seats = seats * occupancy_rate
            revenue = occupied_seats * revenue_per_occ_seat
            support_cost = seats * support_cost_per_seat
            contribution = revenue - support_cost
            total_revenue += revenue
            total_contribution += contribution
            utilization_values.append(0 if seats == 0 else occupied_seats / seats)
        expected['Dashboard'][f'B{idx}'] = total_revenue
        expected['Dashboard'][f'C{idx}'] = total_contribution
        expected['Dashboard'][f'D{idx}'] = sum(utilization_values) / BLOCK_SIZE
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'capacity_dashboard_audit.xlsx')
    gold_file = os.path.join(args.gold_path, 'capacity_dashboard_audit.xlsx')
    evaluator = Evaluator('workbook_audit/task_003_audit_capacity_dashboard_workbook', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Staffing')
        evaluator.compare_sheet_dimension('Utilization')
        evaluator.compare_sheet_dimension('Dashboard')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate workbook audit workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
