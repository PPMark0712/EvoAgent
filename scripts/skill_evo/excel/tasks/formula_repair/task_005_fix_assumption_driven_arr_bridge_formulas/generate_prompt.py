import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `arr_bridge.xlsx`，并原地修复 `Bridge` sheet 中的大表公式：
1. `Accounts` sheet 提供 account 级 ARR、扩容 ARR、流失 ARR、续约概率、支持工时、费率、growth uplift 和 onboarding credit，`Assumptions` sheet 提供全局 driver，`Bridge` sheet 需要按列标题生成 ARR bridge 指标
2. 结合列标题语义修复 `C:J` 的损坏公式，其中 `Gross ARR` 需要同时包含当前 ARR 和 expansion ARR，`Renewal ARR` 需要基于扣除流失后的 ARR 再乘 `Renewal Probability`
3. `Upsell ARR` 需要使用 `Assumptions` 中的 upsell rate，并同时考虑 account 自身的 `Growth Uplift`；`Risk Adjusted ARR` 需要对 `Renewal ARR + Upsell ARR` 应用 `Assumptions` 中的 risk discount
4. `Support Cost` 需要使用 `Support Hours` 和 `Assumptions` 中的 `Cost per Support Hour`；`Payment Fees` 以 `Risk Adjusted ARR` 为基数乘 account 自身费率；`Net ARR` 需要在 `Risk Adjusted ARR` 基础上扣除成本和手续费，再加上 `Onboarding Credit` 与 `Assumptions` 中的 `Retention Bonus`
5. `Net ARR Margin %` 以 `Risk Adjusted ARR` 为分母，并对涉及除法的列做好 0 值保护；需要正确使用 `Assumptions` sheet 中的全局参数，所有计算结果必须保留为 Excel 公式，不要写成静态数值；保留 `A:B`、sheet 名、记录顺序和输入数据不变，保存后的文件名仍然是 `arr_bridge.xlsx`
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
