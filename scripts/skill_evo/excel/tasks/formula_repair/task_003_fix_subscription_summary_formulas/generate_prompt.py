import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `subscription_report.xlsx`，并原地修复 `Summary` sheet 中的大表公式：
1. `Subscribers` sheet 给出了订阅期初、拉新、召回、流失、ARPU、Support Cost per Sub、Payment Fee Rate 和 Setup Fee Revenue 等输入，`Summary` sheet 需要产出一致的订阅汇总结果
2. 结合列标题语义修复 `C:J` 的损坏公式，其中 `Ending Subs = Starting Subs + New Subs + Reactivated Subs - Churned Subs`，`Gross Adds = New Subs + Reactivated Subs`，`Lost Subs = Churned Subs`
3. `Subscription Revenue` 需要同时包含 recurring revenue 和 `Setup Fee Revenue`；`Support Cost = Ending Subs * Support Cost per Sub`；`Payment Fees = Subscription Revenue * Payment Fee Rate`；`Net Revenue = Subscription Revenue - Support Cost - Payment Fees`
4. `ARPU Retention` 在本题中表示订阅保留比例，即 `Ending Subs` 相对 `Starting Subs` 的比率，不是直接引用 ARPU；对涉及除法的列做好 0 值保护
5. 最后一行需要保留汇总用途：`A222` 为 `Portfolio Total`，`B222` 为 `All Plans`，`C:I` 为合计公式，`J` 为平均值公式；所有计算结果必须保留为 Excel 公式，不要改写成静态数值；不要改动标题、sheet 名、记录顺序和输入数据，保存后的文件名仍然是 `subscription_report.xlsx`
"""


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
