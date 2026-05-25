import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `quarterly_plan.xlsx`，并原地修复 `Plan` sheet 中的未来季度预测公式：
1. `Drivers` sheet 给出了 Q1/Q2 的实际 units 与 price，以及 Q3/Q4 的增长与提价 driver；`Plan` sheet 需要根据这些输入补齐未来季度预测区
2. 结合列标题语义修复 `E:L` 的损坏公式，其中 `Q3 Units` 和 `Q3 Price` 都应从 Q2 基数继续向前滚动，而不是回看 Q1；`Q3 Revenue = Q3 Units * Q3 Price`
3. `Q4 Units` 和 `Q4 Price` 都应继续基于已经预测出的 Q3 结果再向前滚动，`Q4 Revenue = Q4 Units * Q4 Price`；`H2 Revenue = Q3 Revenue + Q4 Revenue`
4. `H2 Growth %` 在本题中以 `Q2 Revenue` 为对比基数，即比较 `H2 Revenue` 相对 `Q2 Revenue` 的增长，不要用 `Q1+Q2` 作为分母；对增长率计算做好 0 值保护
5. 保留 `A:D`、sheet 名、记录顺序和输入数据不变，所有结果必须保留为 Excel 公式，不要写成静态数值；保存后的文件名仍然是 `quarterly_plan.xlsx`
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
