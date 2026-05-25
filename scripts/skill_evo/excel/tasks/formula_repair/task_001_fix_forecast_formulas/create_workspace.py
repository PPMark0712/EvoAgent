import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font


ROW_COUNT = 220
REGIONS = ['North', 'South', 'East', 'West']
ZERO_VALUE_ROWS = {1, 56, 111, 166, 220}


def canonical_rows():
    rows = []
    for idx in range(ROW_COUNT):
        jan_units = 80 + (idx % 35) * 3
        jan_price = 45 + (idx % 9) * 2
        feb_units = jan_units + 4 + (idx % 5)
        feb_price = jan_price + (idx % 4)
        mar_units = feb_units + 5 + (idx % 6)
        mar_price = feb_price + 1 + (idx % 3)
        apr_units = mar_units + 6 + (idx % 4)
        apr_price = mar_price + (idx % 5)
        if idx + 1 in ZERO_VALUE_ROWS:
            if idx % 2 == 0:
                jan_units = 0
            if idx % 3 == 0:
                feb_price = 0
            if idx % 5 == 0:
                mar_units = 0
            if idx % 7 == 0:
                apr_price = 0
        rows.append((
            f'DEAL-{idx + 1:03d}',
            REGIONS[idx % len(REGIONS)],
            jan_units,
            jan_price,
            feb_units,
            feb_price,
            mar_units,
            mar_price,
            apr_units,
            apr_price,
        ))
    return rows


def build_workbook(output_file):
    wb = Workbook()
    inputs = wb.active
    inputs.title = 'Inputs'
    headers = [
        'Deal ID',
        'Region',
        'Jan Units',
        'Jan Price',
        'Feb Units',
        'Feb Price',
        'Mar Units',
        'Mar Price',
        'Apr Units',
        'Apr Price',
    ]
    inputs.append(headers)
    for cell in inputs[1]:
        cell.font = Font(bold=True)
    for row in canonical_rows():
        inputs.append(list(row))

    forecast = wb.create_sheet('Forecast')
    forecast_headers = [
        'Deal ID',
        'Region',
        'Jan Revenue',
        'Feb Revenue',
        'Mar Revenue',
        'Apr Revenue',
        'Total Revenue',
        'Average Price',
        'Peak Revenue',
        'Floor Revenue',
    ]
    forecast.append(forecast_headers)
    for cell in forecast[1]:
        cell.font = Font(bold=True)

    for row_num in range(2, ROW_COUNT + 2):
        forecast[f'A{row_num}'] = f'=Inputs!A{row_num}'
        forecast[f'B{row_num}'] = f'=Inputs!B{row_num}'
        jan_source_row = row_num
        if row_num in (2, ROW_COUNT + 1) or row_num % 47 == 0:
            jan_source_row = min(ROW_COUNT + 1, row_num + 1)
        apr_source_row = row_num
        if row_num in (2, ROW_COUNT + 1) or row_num % 53 == 0:
            apr_source_row = max(2, row_num - 1)
        forecast[f'C{row_num}'] = f'=Inputs!C{jan_source_row}*Inputs!D{row_num}'
        forecast[f'D{row_num}'] = f'=Inputs!E{row_num}*Inputs!H{row_num}'
        forecast[f'E{row_num}'] = f'=Inputs!G{row_num}*Inputs!F{row_num}'
        forecast[f'F{row_num}'] = f'=Inputs!I{apr_source_row}*Inputs!H{row_num}'
        if row_num % 9 == 0:
            forecast[f'G{row_num}'] = f'=SUM(D{row_num}:F{row_num})'
        else:
            forecast[f'G{row_num}'] = f'=SUM(C{row_num}:E{row_num})'
        forecast[f'H{row_num}'] = f'=AVERAGE(Inputs!D{row_num},Inputs!F{row_num},Inputs!H{row_num},Inputs!J{row_num})'
        forecast[f'I{row_num}'] = f'=MAX(C{row_num}:F{row_num})'
        forecast[f'J{row_num}'] = f'=MIN(C{row_num}:F{row_num})'

    wb.save(output_file)
    wb.close()


def main(args):
    os.makedirs(args.output_path, exist_ok=True)
    output_file = os.path.join(args.output_path, 'forecast_model.xlsx')
    build_workbook(output_file)
    with open(os.path.join(args.output_path, 'task_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {
                'task_id': 'formula_repair/task_001_fix_forecast_formulas',
                'target_file': 'forecast_model.xlsx',
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(os.path.abspath(args.output_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create workspace for formula repair task')
    parser.add_argument('output_path', help='Directory to create workspace in')
    main(parser.parse_args())
