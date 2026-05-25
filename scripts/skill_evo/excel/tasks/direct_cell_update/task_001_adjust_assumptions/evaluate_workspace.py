import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import DATA_ROW_COUNT, canonical_rows


INPUT_SAMPLES = [1, 2, 51, 101, 151, 200]
STATIC_CELLS = {"Inputs": ["A1", "B1", "C1", "D1", "E1"], "Notes": ["A1", "A2", "A3"]}
for idx in INPUT_SAMPLES:
    row_num = idx + 1
    STATIC_CELLS["Inputs"].extend([f"A{row_num}", f"B{row_num}", f"C{row_num}", f"D{row_num}", f"E{row_num}"])



def build_expected_formulas():
    rows = canonical_rows()
    summary_row = DATA_ROW_COUNT + 2
    growth_values = [row[1] for row in rows]
    marketing_values = [row[2] for row in rows]
    headcount_values = [row[3] for row in rows]
    revenue_values = [row[4] for row in rows]
    return {
        "Inputs": {
            f"B{summary_row}": sum(growth_values) / len(growth_values),
            f"C{summary_row}": sum(marketing_values),
            f"D{summary_row}": sum(headcount_values) / len(headcount_values),
            f"E{summary_row}": max(revenue_values),
        }
    }



def main(args):
    target_file = os.path.join(args.workspace_path, "budget_update.xlsx")
    gold_file = os.path.join(args.gold_path, "budget_update.xlsx")
    evaluator = Evaluator("direct_cell_update/task_001_adjust_assumptions", target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension("Inputs")
        evaluator.compare_sheet_dimension("Notes")
        evaluator.compare_selected_cells(STATIC_CELLS)
        evaluator.compare_formula_cells_by_value(build_expected_formulas())
    evaluator.write_result(args.output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate direct cell update workspace")
    parser.add_argument("workspace_path", help="Workspace directory to evaluate")
    parser.add_argument("gold_path", help="Gold directory")
    parser.add_argument("output_path", help="Result JSON path")
    main(parser.parse_args())
