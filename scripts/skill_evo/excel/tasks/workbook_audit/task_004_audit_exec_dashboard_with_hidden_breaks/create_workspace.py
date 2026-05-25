import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
SEGMENT_COUNT = 4
BLOCK_SIZE = ROW_COUNT // SEGMENT_COUNT
SEGMENTS = ['Enterprise', 'Commercial', 'SMB', 'Public']
REORDER_STEP = 41
TARGETS = {
    'Enterprise': (195000, 0.30),
    'Commercial': (210000, 0.29),
    'SMB': (225000, 0.28),
    'Public': (240000, 0.27),
}


def canonical_rows():
    grouped_rows = []
    for idx in range(ROW_COUNT):
        segment = SEGMENTS[idx // BLOCK_SIZE]
        account_id = f'ACC-{idx + 1:03d}'
        starting_arr = 3800 + idx * 28
        collection_rate = round(0.72 + (idx % 6) * 0.03, 4)
        service_cost_rate = round(0.11 + (idx % 5) * 0.015, 4)
        headcount_cost = 360 + (idx % 7) * 32
        expansion_rate = round(0.05 + (idx % 4) * 0.0125, 4)
        churn_rate = round(0.01 + (idx % 5) * 0.008, 4)
        grouped_rows.append((account_id, segment, starting_arr, collection_rate, service_cost_rate, headcount_cost, expansion_rate, churn_rate))
    return [grouped_rows[(idx * REORDER_STEP) % ROW_COUNT] for idx in range(ROW_COUNT)]


def build_workbook(output_file):
    wb = Workbook()
    rows = canonical_rows()

    drivers = wb.active
    drivers.title = 'Drivers'
    drivers.append(['Account ID', 'Segment', 'Starting ARR', 'Collection Rate', 'Service Cost Rate', 'Headcount Cost'])
    for cell in drivers[1]:
        cell.font = Font(bold=True)

    adjustments = wb.create_sheet('Adjustments')
    adjustments.append(['Account ID', 'Expansion Rate', 'Churn Rate'])
    for cell in adjustments[1]:
        cell.font = Font(bold=True)
    adjustments.sheet_state = 'hidden'

    targets = wb.create_sheet('Targets')
    targets.append(['Segment', 'Min Ending ARR', 'Min EBITDA Margin'])
    for cell in targets[1]:
        cell.font = Font(bold=True)
    targets.sheet_state = 'hidden'

    model = wb.create_sheet('OperatingModel')
    model.append(['Account ID', 'Segment', 'Ending ARR', 'Cash In', 'Service Cost', 'EBITDA', 'EBITDA Margin'])
    for cell in model[1]:
        cell.font = Font(bold=True)

    dashboard = wb.create_sheet('Dashboard')
    dashboard.append(['Segment', 'Total Ending ARR', 'Total EBITDA', 'Average EBITDA Margin'])
    for cell in dashboard[1]:
        cell.font = Font(bold=True)

    alerts = wb.create_sheet('Alerts')
    alerts.append(['Segment', 'Margin Status', 'ARR Status'])
    for cell in alerts[1]:
        cell.font = Font(bold=True)

    for account_id, segment, starting_arr, collection_rate, service_cost_rate, headcount_cost, expansion_rate, churn_rate in rows:
        drivers.append([account_id, segment, starting_arr, collection_rate, service_cost_rate, headcount_cost])
        adjustments.append([account_id, expansion_rate, churn_rate])

    for idx, segment in enumerate(SEGMENTS, start=2):
        min_arr, min_margin = TARGETS[segment]
        targets.append([segment, min_arr, min_margin])
        dashboard[f'A{idx}'] = segment
        alerts[f'A{idx}'] = segment

    for row_num in range(2, ROW_COUNT + 2):
        model[f'A{row_num}'] = f'=Drivers!A{row_num}'
        model[f'B{row_num}'] = f'=Drivers!B{row_num}'
        model[f'C{row_num}'] = f'=Drivers!C{row_num}*(1+Adjustments!B{row_num}+Adjustments!C{row_num})'
        model[f'D{row_num}'] = f'=C{row_num}*Drivers!E{row_num}'
        model[f'E{row_num}'] = f'=C{row_num}*Drivers!D{row_num}'
        model[f'F{row_num}'] = f'=D{row_num}+E{row_num}+Drivers!F{row_num}'
        model[f'G{row_num}'] = f'=F{row_num}/0'

    for idx, _segment in enumerate(SEGMENTS, start=2):
        start = 2 + (idx - 2) * BLOCK_SIZE
        end = start + BLOCK_SIZE - 1
        dashboard[f'B{idx}'] = f'=SUM(OperatingModel!C{start}:C{end})'
        dashboard[f'C{idx}'] = f'=SUM(OperatingModel!F{start}:F{end})'
        dashboard[f'D{idx}'] = f'=MAX(OperatingModel!G{start}:G{end})'
        alerts[f'B{idx}'] = f'=IF(Dashboard!D{idx}>Targets!C{idx},"OK","ALERT")'
        alerts[f'C{idx}'] = f'=IF(Dashboard!B{idx}>Targets!B{idx},"OK","ALERT")'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'exec_dashboard_audit.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump({'task_id': 'workbook_audit/task_004_audit_exec_dashboard_with_hidden_breaks', 'target_file': 'exec_dashboard_audit.xlsx'}, f, ensure_ascii=False, indent=2)
    print(os.path.abspath(args.output_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create workspace for hard workbook audit task')
    parser.add_argument('output_path', help='Directory to create workspace in')
    main(parser.parse_args())
