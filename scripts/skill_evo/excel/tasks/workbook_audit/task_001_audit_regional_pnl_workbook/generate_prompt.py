import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `regional_pnl_audit.xlsx`，并完成一次 workbook audit：
1. `Drivers` sheet 是 source of truth，`PnL` 和 `Summary` 都应与它保持一致
2. 当前错误不是单点故障：有些 `PnL` 行用了错误输入或错误符号，有些边界行发生了错位，`Operating Margin` 还存在除零风险
3. `Summary` sheet 也需要一起审计。它应按区域汇总修复后的 `PnL` 结果，并与下游利润率口径保持一致
4. 注意：`PnL` 中各区域记录是交错分布的，不能假设某个区域占据连续区间；请确保修复后的上游和下游公式链条都能正常工作
5. 只修复派生公式单元格，不要改动输入数据、sheet 名、记录顺序和标题；所有结果必须保留为 Excel 公式，不要写成静态数值
6. 保存后的文件名仍然是 `regional_pnl_audit.xlsx`"""


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
