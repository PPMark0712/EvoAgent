import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `forecast_model.xlsx`，并在不改变现有结构的前提下修复 `Forecast` sheet 的收入块：
1. `Inputs` sheet 是 source of truth。`Forecast` 中每一行都应与同一行 deal 的 1-4 月输入保持逐月一致，不允许跨月混用，也不要把相邻行的数据串到一起
2. 当前错误不只是一种：有些公式引用了错误月份，有些发生了行错位，首尾数据行也存在边界错误。请只修复 `Forecast` 的派生收入区域，使月度收入和四个月汇总都恢复正确
3. `A:B`、`H:J`、标题、sheet 名、记录顺序和所有输入数据都不要改动
4. 所有修复结果必须保留为 Excel 公式，不要写成静态数值
5. 保存修改后的文件，文件名仍然是 `forecast_model.xlsx`
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
