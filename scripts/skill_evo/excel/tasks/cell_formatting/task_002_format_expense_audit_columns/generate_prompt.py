import argparse
import os

PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `expense_audit.xlsx`，并按列为 `Expenses` sheet 设置格式：
1. 保持所有现有值、行数、列顺序和 sheet 名不变，只修改单元格格式
2. 将表头行设置为深绿色底（填充颜色编码 `38761D`）、白色粗体字（字体颜色编码 `FFFFFFFF`），并水平居中
3. 将 `Expense Date` 列的数据设置为 `YYYY-MM-DD` 日期格式，数据字体颜色使用黑色（字体颜色编码 `FF000000`）
4. 将 `Amount` 列的数据设置为美元两位小数格式，将 `Variance %` 列的数据设置为百分比格式，保留 1 位小数，以上数据字体颜色均使用黑色（字体颜色编码 `FF000000`）
5. 将 `Status` 列的数据单元格设置为浅红色底（填充颜色编码 `F4CCCC`），并水平居中
6. 保存修改后的文件，文件名仍然是 `expense_audit.xlsx`
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
