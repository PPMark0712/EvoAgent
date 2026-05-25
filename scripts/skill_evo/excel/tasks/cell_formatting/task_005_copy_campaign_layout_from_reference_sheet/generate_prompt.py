import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `campaign_launch_queue.xlsx`，并根据工作簿中已有样式完成格式统一：
1. 工作簿包含 `Reference Layout` 和 `Launch Queue` 两个 sheet，不要改动 sheet 名、行数、列顺序或任何单元格值
2. `Reference Layout` sheet 已经给出了同类运营表的格式规则，请参照它的表头样式和各列数据样式；其中表头底色为深青色（填充颜色编码 `134F5C`）、表头字体为白色粗体（字体颜色编码 `FFFFFFFF`）、数据字体颜色为黑色（字体颜色编码 `FF000000`）、`Approval State` 列填充为浅橙色（填充颜色编码 `FCE5CD`）
3. 将同样的样式规则应用到 `Launch Queue` sheet 的整张表，包括表头行和全部数据行
4. 只允许修改 `Launch Queue` sheet 的单元格格式，不要改动 `Reference Layout` sheet
5. 保存修改后的文件，文件名仍然是 `campaign_launch_queue.xlsx`
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
