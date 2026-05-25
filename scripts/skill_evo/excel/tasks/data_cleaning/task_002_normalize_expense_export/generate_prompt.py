import argparse
import os

PROMPT = '你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `expense_raw.xlsx`，并创建一个新的输出文件 `expense_clean.xlsx`：\n1. 从 `Raw` sheet 读取原始数据，注意数据表头在第 2 行，sheet 中还有一些侧边注释和非表格单元格\n2. 生成一个名为 `Clean` 的 sheet，列顺序固定为 `Date`, `Category`, `Amount`, `Owner`, `Cost Center`\n3. 只保留有效数据行，忽略空白和表格外干扰内容\n4. 将分类统一为 `Travel`、`Software`、`Office Supplies`、`Meals`、`Marketing`\n5. 将日期统一为 `YYYY-MM-DD` 文本，将金额统一为数值，去掉货币符号、空格和千分位分隔符\n6. 保留 `Owner` 原始值不变，将 `Cost Center` 统一为大写标准格式\n7. 输出文件只需要包含 `Clean` 一个 sheet\n'

def main(args):
    parent = os.path.dirname(args.output_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        f.write(PROMPT)
    print(os.path.abspath(args.output_path))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write the benchmark prompt file")
    parser.add_argument("output_path", help="Path to write prompt text")
    main(parser.parse_args())
