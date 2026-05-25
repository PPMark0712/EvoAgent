import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `cash_conversion_audit.xlsx`，并完成一次 workbook audit：
1. `Inputs` sheet 提供每个客户的 invoiced revenue、collection rate、deferred rate、payroll 和 vendor spend；`CashFlow` sheet 需要据此产出现金流明细
2. 请修复 `CashFlow` sheet 中损坏的公式列，使其满足：`Invoiced Revenue` 直接引用输入，`Cash Collected = Invoiced Revenue * Collection Rate`，`Deferred Revenue = Invoiced Revenue * Deferred Rate`，`Operating Spend = Payroll + Vendor Spend`，`Net Cash = Cash Collected - Operating Spend`，`Cash Conversion = Net Cash / Invoiced Revenue`，并对除法做好 0 值保护
3. `Covenant` sheet 也有损坏公式，需要按 segment 汇总 `Total Cash Collected`、`Total Net Cash`，并计算 `Average Cash Conversion`
4. 注意：`CashFlow` 中各 segment 记录是交错分布的，`Covenant` 只能按 segment 标签聚合，不能假设某个 segment 占据连续区间
5. 请把这当成一次完整 workbook audit：除了修复目标列本身，也要确保下游 covenant 指标可正常工作，不要改动输入数据、sheet 名、记录顺序和标题
6. 所有结果必须保留为 Excel 公式，不要写成静态数值；保存后的文件名仍然是 `cash_conversion_audit.xlsx`"""


def main(args):
    parent = os.path.dirname(args.output_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(args.output_path, 'w', encoding='utf-8') as f:
        f.write(PROMPT)
    print(os.path.abspath(args.output_path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Write the benchmark prompt file')
    parser.add_argument('output_path', help='Path to write prompt text')
    main(parser.parse_args())
