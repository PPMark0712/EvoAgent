import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `capacity_dashboard_audit.xlsx`，并完成一次 workbook audit：
1. `Staffing` sheet 提供每个团队的 seats、occupancy rate、revenue per occupied seat 和 support cost per seat
2. 请修复 `Utilization` sheet，使其满足：`Occupied Seats = Seats * Occupancy Rate`，`Revenue = Occupied Seats * Revenue Per Occupied Seat`，`Support Cost = Seats * Support Cost Per Seat`，`Contribution = Revenue - Support Cost`，`Utilization Rate = Occupied Seats / Seats` 并做好 0 值保护
3. `Dashboard` sheet 也有损坏公式，需要按区域汇总 `Total Revenue`、`Total Contribution`，并给出 `Average Utilization`
4. 注意：`Utilization` 中各区域记录是交错分布的，`Dashboard` 只能按区域标签聚合，不能假设某个区域占据连续区间
5. 请把这视为一次完整 workbook audit：除了目标列，也要保证下游 dashboard 指标正确，不要改动输入数据、sheet 名、记录顺序和标题
6. 所有结果必须保留为 Excel 公式，不要写成静态数值；保存后的文件名仍然是 `capacity_dashboard_audit.xlsx`"""


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
