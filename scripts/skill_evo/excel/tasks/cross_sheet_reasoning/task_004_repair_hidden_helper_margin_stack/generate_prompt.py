import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `hidden_helper_margin_stack.xlsx`，并修复 `MarginStack` sheet：
1. `Orders` 提供订单粒度的 `Units` 和 `Region`；`PriceBook`、`Rebates`、`Terms` 提供同一订单对应的价格、折扣、返利、服务 attach、续费率和支持成本
2. 注意：`PriceBook`、`Rebates`、`Terms` 都不是按同一物理行对齐的，至少有一个辅助 sheet 还是隐藏的；必须按 `Order ID` 匹配，不能假设相同行就是同一订单
3. `MarginStack` 需要恢复以下指标，且保留为 Excel 公式：`Gross Revenue`、`Discount Loss`、`Rebate Loss`、`Net Revenue`、`Services ARR`、`Final ARR`、`Final Margin`
4. 业务定义为：`Gross Revenue = Units * ASP`，`Discount Loss = Gross Revenue * Discount Rate`，`Rebate Loss = Gross Revenue * Rebate Rate`，`Net Revenue = (Gross Revenue - Discount Loss - Rebate Loss) * Renewal Rate`，`Services ARR = Net Revenue * Service Attach`，`Final ARR = Net Revenue + Services ARR`，`Final Margin = (Final ARR - Units * Support Cost Per Unit) / Final ARR`，并对除法做好 0 值保护
5. 不要改动输入数据、sheet 名、记录顺序和标题；保存后的文件名仍然是 `hidden_helper_margin_stack.xlsx`"""


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
