import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `unit_economics.xlsx`，并原地修复 `Model` sheet 中的大表公式：
1. `Raw` sheet 给出了 account 级别的 leads、conversions、avg deal size、CAC、服务成本、折扣率和退款率，`Model` sheet 需要产出对应的单元经济结果
2. 结合列标题语义修复 `C:J` 的损坏公式，其中 `Revenue` 应基于 Conversions 和 Avg Deal Size，`Acquisition Spend` 应基于 Leads 和 CAC per Lead，`Service Cost` 应基于 Conversions 和 Service Cost per Conversion
3. `Discount Loss` 与 `Refund Loss` 都以 `Revenue` 为基数；`Net Revenue` 先从 `Revenue` 中扣除这两项；`Contribution` 再从 `Net Revenue` 中扣除获客支出和服务成本
4. `ROI` 以 `Acquisition Spend` 为分母；在 `K` 列新增标题 `Contribution Margin %`，并为 `K2:K221` 填写以 `Net Revenue` 为分母的利润率公式；对涉及除法的列做好 0 值保护
5. 保留 `A:B`、sheet 名、记录顺序和原始输入不变，所有结果必须保留为 Excel 公式，不要写成静态数值；保存后的文件名仍然是 `unit_economics.xlsx`
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
