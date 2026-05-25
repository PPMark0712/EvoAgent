import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `operating_profit_summary.xlsx`，并原地修复 `Summary` sheet 中的大表公式：
1. `Transactions` sheet 提供销售额、退货、折扣率、订单量和单单成本，`Rates` sheet 提供全局费率，`Summary` sheet 需要按列标题生成利润汇总结果
2. 结合列标题语义修复 `C:K` 的损坏公式，其中 `Gross Revenue = Gross Sales - Returns`，`Discount Loss = Gross Revenue * Discount Rate`，`Net Revenue = Gross Revenue - Discount Loss`
3. `COGS`、`Fulfillment Cost` 和 `Support Cost` 都应基于订单量计算，其中 `Support Cost` 还需要乘 `Rates` sheet 中的 `Support Multiplier`；`Operating Profit = Net Revenue - COGS - Fulfillment Cost - Support Cost`
4. `Tax Expense` 需要使用 `Rates` sheet 中的 `Tax Rate`，且只有 `Operating Profit` 为正时才计提；`Net Profit = Operating Profit - Tax Expense`
5. 最后一行需要保留汇总用途：`A222` 为 `Network Total`，`B222` 为 `All Channels`，`C:K` 为合计公式；所有结果必须保留为 Excel 公式，不要写成静态数值，保留 `A:B`、sheet 名、记录顺序和输入数据不变；保存后的文件名仍然是 `operating_profit_summary.xlsx`
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
