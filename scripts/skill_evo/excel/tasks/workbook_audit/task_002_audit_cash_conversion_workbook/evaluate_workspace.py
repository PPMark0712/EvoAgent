import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import BLOCK_LABELS, BLOCK_SIZE, canonical_rows


SAMPLE_ROWS = [2, 5, 13, 29, 66, 101, 144, 177, 209, 221]
STATIC_CELLS = {
    'Inputs': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1'],
    'CashFlow': ['A1', 'B1'],
    'Covenant': ['A1', 'B1', 'C1', 'D1', 'A2', 'A3', 'A4', 'A5'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Inputs'].extend([f'{col}{row_num}' for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']])
    STATIC_CELLS['CashFlow'].extend([f'{col}{row_num}' for col in ['A', 'B']])


def build_expected_formulas():
    rows = canonical_rows()
    expected = {'CashFlow': {}, 'Covenant': {}}
    for row_num in SAMPLE_ROWS:
        _customer_id, _segment, revenue, collection_rate, deferred_rate, payroll, vendor_spend = rows[row_num - 2]
        cash_collected = revenue * collection_rate
        deferred_revenue = revenue * deferred_rate
        operating_spend = payroll + vendor_spend
        net_cash = cash_collected - operating_spend
        expected['CashFlow'][f'C{row_num}'] = revenue
        expected['CashFlow'][f'D{row_num}'] = cash_collected
        expected['CashFlow'][f'E{row_num}'] = deferred_revenue
        expected['CashFlow'][f'F{row_num}'] = operating_spend
        expected['CashFlow'][f'G{row_num}'] = net_cash
        expected['CashFlow'][f'H{row_num}'] = 0 if revenue == 0 else net_cash / revenue
    for idx, label in enumerate(BLOCK_LABELS, start=2):
        label_rows = [row for row in rows if row[1] == label]
        total_cash_collected = 0
        total_net_cash = 0
        conversions = []
        for _customer_id, _segment, revenue, collection_rate, deferred_rate, payroll, vendor_spend in label_rows:
            cash_collected = revenue * collection_rate
            net_cash = cash_collected - (payroll + vendor_spend)
            total_cash_collected += cash_collected
            total_net_cash += net_cash
            conversions.append(0 if revenue == 0 else net_cash / revenue)
        expected['Covenant'][f'B{idx}'] = total_cash_collected
        expected['Covenant'][f'C{idx}'] = total_net_cash
        expected['Covenant'][f'D{idx}'] = sum(conversions) / BLOCK_SIZE
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'cash_conversion_audit.xlsx')
    gold_file = os.path.join(args.gold_path, 'cash_conversion_audit.xlsx')
    evaluator = Evaluator('workbook_audit/task_002_audit_cash_conversion_workbook', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Inputs')
        evaluator.compare_sheet_dimension('CashFlow')
        evaluator.compare_sheet_dimension('Covenant')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate workbook audit workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
