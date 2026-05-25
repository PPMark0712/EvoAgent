import argparse
import os

PROMPT = '你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `pricing_model.xlsx`，并在 `Pricing` 表现有 200 条 plan 数据之后追加一行统计行：\n1. 保留前面的 200 条 plan 记录和 `Notes` sheet 不变，不要修改已有数据、顺序或表头\n2. 统计行的 `Plan ID` 写成 `Pricing Summary`\n3. 在统计行中，为 `Base Price`、`Discount Rate`、`Renewal Rate`、`Support Cost` 这 4 列分别写入 Excel 公式，用来统计平均基础价格、平均折扣率、平均续费率和总支持成本\n4. 这些统计结果必须通过公式得到，不要直接填写数字\n5. 保存修改后的文件，文件名仍然是 `pricing_model.xlsx`\n'


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
