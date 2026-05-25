import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `pipeline_margin_rollup.xlsx`，并原地修复 `Rollup` sheet 中的大表公式：
1. `Pipeline` sheet 提供 bookings、扩容收入、折扣率、续约概率、提成率和支持成本等输入，`Rollup` sheet 需要按列标题生成一致的利润汇总指标
2. 结合列标题语义修复 `C:J` 的损坏公式，其中 `Gross Revenue = Bookings + Expansion Revenue`，`Commission Cost = Bookings * Sales Commission Rate`，`Support Cost` 直接引用输入里的 `Support Cost`
3. `Discount Loss = Gross Revenue * Discount Rate`，`Weighted Revenue = (Gross Revenue - Discount Loss) * Renewal Probability`，`Net Margin = Weighted Revenue - Commission Cost - Support Cost`，`Expected Expansion = Expansion Revenue * Renewal Probability`
4. `Margin %` 以 `Weighted Revenue` 为分母，并对涉及除法的列做好 0 值保护；保留 `A:B` 现有引用公式、sheet 名、记录顺序和所有输入数据不变，所有结果必须保留为 Excel 公式，不要写成静态数值
5. 保存后的文件名仍然是 `pipeline_margin_rollup.xlsx`
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
