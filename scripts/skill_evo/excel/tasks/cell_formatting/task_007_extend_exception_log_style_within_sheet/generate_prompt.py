import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `renewal_exception_log.xlsx`，并根据同一张 sheet 中已有区域的样式完成格式统一：
1. 工作簿只有一个 `Exceptions` sheet，不要改动 sheet 名、已有值、行数、列顺序或插入删除行列
2. `G1:K21` 是已经整理好的参考区域，`A1:E201` 是待整理的新数据区域，两块区域列含义完全一致
3. 请参照 `G1:K21` 的表头样式和各列数据样式，将同样的格式规则应用到 `A1:E201`；其中表头底色为棕色（填充颜色编码 `7F6000`）、表头字体为白色粗体（字体颜色编码 `FFFFFFFF`）、数据字体颜色为黑色（字体颜色编码 `FF000000`）、`Severity` 列填充为浅红色（填充颜色编码 `F4CCCC`）
4. 只允许修改 `A1:E201` 的单元格格式，不要改动参考区域 `G1:K21`
5. 保存修改后的文件，文件名仍然是 `renewal_exception_log.xlsx`
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
