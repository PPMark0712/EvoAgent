import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `exec_dashboard_audit.xlsx`，并完成一次高难 workbook audit：
1. `Drivers` 提供账户级 `Starting ARR`、`Collection Rate`、`Service Cost Rate`、`Headcount Cost`；至少一个隐藏 sheet 还提供扩张/流失假设和 dashboard 阈值
2. 请修复 `OperatingModel`，恢复 `Ending ARR`、`Cash In`、`Service Cost`、`EBITDA`、`EBITDA Margin`，并保留为 Excel 公式
3. 业务定义为：`Ending ARR = Starting ARR * (1 + Expansion Rate - Churn Rate)`，`Cash In = Ending ARR * Collection Rate`，`Service Cost = Ending ARR * Service Cost Rate`，`EBITDA = Cash In - Service Cost - Headcount Cost`，`EBITDA Margin = EBITDA / Cash In`，并对除法做好 0 值保护
4. `Dashboard` 需要按 segment 汇总 `Total Ending ARR`、`Total EBITDA`、`Average EBITDA Margin`；注意各 segment 记录在明细表中是交错分布的，不能假设连续区间
5. `Alerts` 还要基于隐藏阈值表输出 `Margin Status` 和 `ARR Status`；只有 detail、dashboard、alerts 都正确才算完成 audit
6. 不要改动输入数据、sheet 名、记录顺序和标题；保存后的文件名仍然是 `exec_dashboard_audit.xlsx`"""


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
