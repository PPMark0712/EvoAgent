import argparse
import os


PROMPT = '你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `budget_update.xlsx`，并在 `Inputs` 表现有 200 条 scenario 数据之后追加一行统计行：\n1. 保留前面的 200 条数据记录和 `Notes` sheet 不变，不要改动原有行的值、顺序或表头\n2. 统计行的 `Scenario ID` 写成 `Portfolio Summary`\n3. 在统计行中，为 `Growth Rate`、`Marketing Budget`、`Headcount`、`Revenue Target` 这 4 列分别写入 Excel 公式，用来计算平均增长率、总营销预算、平均人数和最大收入目标\n4. 这些统计结果必须由公式生成，不要直接填写数字\n5. 保存修改后的文件，文件名仍然是 `budget_update.xlsx`\n'



def main(args):
    parent = os.path.dirname(args.output_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        f.write(PROMPT)
    print(os.path.abspath(args.output_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write the benchmark prompt file")
    parser.add_argument("output_path", help="Path to write prompt text")
    main(parser.parse_args())
