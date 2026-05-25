import argparse
import os


PROMPT = "你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `board_kpi_style.xlsx`，并在修复公式的同时恢复 `BoardKPI` 的模板保真：\n1. `Reference` sheet 提供了目标表派生指标区域和整体布局应遵循的模板线索；`BoardKPI` 是需要修复的目标表\n2. 请修复 `BoardKPI` 中损坏的派生指标公式，使其与现有业务列一致，并对增长率计算做好 0 值保护；所有结果必须保留为 Excel 公式\n3. 需要恢复的不只是单元格样式，还包括目标区域应有的模板表现，例如数字格式、填充色、字体颜色、对齐、边框，以及工作表布局线索\n4. 只恢复与派生指标区域和模板布局相关的内容，不要覆盖 `BoardKPI` 里非目标区域已经存在的本地强调样式\n5. 不要改动非目标数据列、sheet 名、记录顺序和标题；保存后的文件名仍然是 `board_kpi_style.xlsx`"


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
