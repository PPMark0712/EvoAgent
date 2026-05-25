import argparse
import os


PROMPT = "你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `pricing_waterfall_style.xlsx`，并在修复公式的同时恢复样式：\n1. `StyleGuide` sheet 提供目标格式，`Waterfall` sheet 是待修复的目标表\n2. 请修复 `Waterfall` 中的公式：`Net Price = List Price * (1 - Discount %)`，`Revenue = Net Price * Units`，`Gross Margin % = (Revenue - Units * Unit Cost) / Revenue`，并做好 0 值保护\n3. 修复后，相关指标列需要与 `StyleGuide` sheet 保持一致的数字格式、填充色、字体颜色和对齐方式\n4. 不要改动非目标数据列、sheet 名、记录顺序和标题；所有结果必须保留为 Excel 公式\n5. 保存后的文件名仍然是 `pricing_waterfall_style.xlsx`"


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
