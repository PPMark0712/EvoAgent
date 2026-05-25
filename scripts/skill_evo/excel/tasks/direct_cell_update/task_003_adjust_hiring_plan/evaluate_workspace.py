import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator
from create_workspace import DATA_ROW_COUNT, canonical_rows


INPUT_SAMPLES = [1, 2, 49, 97, 142, 200]
STATIC_CELLS = {"Hiring": ["A1", "B1", "C1", "D1", "E1"], "Notes": ["A1", "A2", "A3"]}
for idx in INPUT_SAMPLES:
    row_num = idx + 1
    STATIC_CELLS["Hiring"].extend([f"A{row_num}", f"B{row_num}", f"C{row_num}", f"D{row_num}", f"E{row_num}"])



def build_expected_formulas():
    rows = canonical_rows()
    summary_row = DATA_ROW_COUNT + 2
    hires_values = [row[1] for row in rows]
    attrition_values = [row[2] for row in rows]
    budget_values = [row[3] for row in rows]
    headcount_values = [row[4] for row in rows]
    return {
        "Hiring": {
            f"B{summary_row}": sum(hires_values),
            f"C{summary_row}": sum(attrition_values) / len(attrition_values),
            f"D{summary_row}": sum(budget_values),
            f"E{summary_row}": sum(headcount_values) / len(headcount_values),
        }
    }



def main(args):
    target_file = os.path.join(args.workspace_path, "workforce_plan.xlsx")
    gold_file = os.path.join(args.gold_path, "workforce_plan.xlsx")
    evaluator = Evaluator("direct_cell_update/task_003_adjust_hiring_plan", target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension("Hiring")
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
