import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `inventory_network_plan.xlsx`，并修复 `Plan` sheet 中损坏的跨 sheet 公式：
1. `Demand` sheet 提供每个 SKU 的 `Forecast Units` 与 `Backlog Units`
2. `Supply` sheet 提供同一 SKU 对应的 `Yield Rate`、`Unit Cost` 和 `Expedite Rate`
3. 注意：`Demand` 与 `Supply` 并不是按同一物理行对齐的，必须按 `SKU` 进行匹配，不能假设相同行就是同一产品
4. `Plan` sheet 需要满足：`Demand Units = Forecast Units + Backlog Units`，`Production Units = Demand Units / Yield Rate`，`Base Spend = Production Units * Unit Cost`，`Expedite Spend = Base Spend * Expedite Rate`，`Total Spend = Base Spend + Expedite Spend`，`Spend Per Demand Unit = Total Spend / Demand Units`，并对除法做好 0 值保护
5. 保留 `A:B`、sheet 名、记录顺序和所有输入数据不变；所有结果必须保留为 Excel 公式，不要写成静态数值
6. 保存后的文件名仍然是 `inventory_network_plan.xlsx`"""


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
