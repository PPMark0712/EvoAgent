import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `multi_sheet_margin_bridge.xlsx`，并修复 `Bridge` sheet 中损坏的跨 sheet 公式：
1. `Orders` sheet 提供每个订单的 `Units` 与 `Region`
2. `Pricing` sheet 提供同一订单对应的 `ASP` 与 `Discount Rate`，`Costs` sheet 提供同一订单对应的 `Unit Cost` 与 `Support Cost`
3. 注意：`Orders`、`Pricing`、`Costs` 三张表不是按同一物理行对齐的，必须按 `Order ID` 进行匹配，不能假设相同行就是同一订单
4. `Bridge` sheet 需要满足：`Gross Revenue = Units * ASP`，`Discount Loss = Gross Revenue * Discount Rate`，`Net Revenue = Gross Revenue - Discount Loss`，`COGS = Units * Unit Cost`，`Contribution = Net Revenue - COGS - Support Cost`，`Contribution Margin = Contribution / Net Revenue`，并对除法做好 0 值保护
5. 保留 `A:B`、sheet 名、记录顺序和所有输入数据不变；所有结果必须保留为 Excel 公式，不要写成静态数值
6. 保存后的文件名仍然是 `multi_sheet_margin_bridge.xlsx`"""


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
