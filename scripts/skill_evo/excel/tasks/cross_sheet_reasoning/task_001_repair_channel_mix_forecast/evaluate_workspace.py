import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import build_mix_rows, canonical_rows


SAMPLE_ROWS = [2, 3, 11, 25, 42, 57, 91, 128, 166, 203, 221]
STATIC_CELLS = {
    'Drivers': ['A1', 'B1', 'C1', 'D1', 'E1'],
    'Mix': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'A222', 'B222', 'C222'],
    'Output': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1'],
}
for row_num in SAMPLE_ROWS:
    STATIC_CELLS['Drivers'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}'])
    STATIC_CELLS['Mix'].extend([f'A{row_num}', f'B{row_num}', f'C{row_num}', f'D{row_num}', f'E{row_num}', f'F{row_num}'])
    STATIC_CELLS['Output'].extend([f'A{row_num}', f'B{row_num}'])


def build_expected_formulas():
    rows = canonical_rows()
    active_mix = {}
    for account_id, region, status, enterprise_share, partner_discount, service_attach in build_mix_rows():
        if status != 'Active':
            continue
        active_mix[(account_id, region)] = (
            enterprise_share or 0,
            partner_discount or 0,
            service_attach or 0,
        )
    expected = {'Output': {}}
    for row_num in SAMPLE_ROWS:
        account_id, region, base_units, base_price, renewal_probability, *_ = rows[row_num - 2]
        enterprise_share, partner_discount, service_attach = active_mix[(account_id, region)]
        gross_sales = base_units * base_price
        enterprise_sales = gross_sales * enterprise_share
        partner_discount_value = gross_sales * partner_discount
        net_sales = (gross_sales - partner_discount_value) * renewal_probability
        services = net_sales * service_attach
        expected['Output'][f'C{row_num}'] = gross_sales
        expected['Output'][f'D{row_num}'] = enterprise_sales
        expected['Output'][f'E{row_num}'] = partner_discount_value
        expected['Output'][f'F{row_num}'] = net_sales
        expected['Output'][f'G{row_num}'] = services
        expected['Output'][f'H{row_num}'] = net_sales + services
    return expected


def main(args):
    target_file = os.path.join(args.workspace_path, 'channel_mix_forecast.xlsx')
    gold_file = os.path.join(args.gold_path, 'channel_mix_forecast.xlsx')
    evaluator = Evaluator('cross_sheet_reasoning/task_001_repair_channel_mix_forecast', target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension('Drivers')
        evaluator.compare_sheet_dimension('Mix')
        evaluator.compare_sheet_dimension('Output')
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate cross sheet reasoning workspace')
    parser.add_argument('workspace_path', help='Workspace directory to evaluate')
    parser.add_argument('gold_path', help='Gold directory')
    parser.add_argument('output_path', help='Result JSON path')
    main(parser.parse_args())
