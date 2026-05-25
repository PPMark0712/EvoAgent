import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_EVO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR))))
if SKILL_EVO_DIR not in sys.path:
    sys.path.insert(0, SKILL_EVO_DIR)

from excel.evaluator import Evaluator

def build_target_cells():
    cols = ["A", "B", "C", "D", "E"]
    rows = [1, 2, 3, 110, 111, 220, 221]
    return {"Clean": [f"{col}{row}" for row in rows for col in cols]}


def main(args):
    target_file = os.path.join(args.workspace_path, "expense_clean.xlsx")
    gold_file = os.path.join(args.gold_path, "expense_clean.xlsx")
    evaluator = Evaluator("data_cleaning/task_002_normalize_expense_export", target_file, gold_file)
    if evaluator.require_target() and evaluator.require_gold():
        evaluator.compare_sheetnames()
        evaluator.compare_sheet_dimension("Clean")
        evaluator.compare_selected_cells(build_target_cells())
    evaluator.write_result(args.output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate data cleaning workspace")
    parser.add_argument("workspace_path", help="Workspace directory to evaluate")
    parser.add_argument("gold_path", help="Gold directory")
    parser.add_argument("output_path", help="Result JSON path")
    main(parser.parse_args())
