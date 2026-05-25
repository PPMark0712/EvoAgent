import argparse
import os

PROMPT = '你现在在一个 Excel benchmark 工作区中工作。\n\n请读取工作区中的 `roster_raw.xlsx`，并创建一个新的输出文件 `roster_clean.xlsx`：\n1. 从 `Raw` sheet 读取原始数据，注意数据表头在第 3 行，sheet 中混有标题说明和侧边备注\n2. 生成一个名为 `Clean` 的 sheet，列顺序固定为 `Employee ID`, `Department`, `Location`, `Status`, `Manager`\n3. 只保留有效数据行，忽略空白和表格外干扰内容\n4. 将部门统一为 `Engineering`、`Sales`、`Finance`、`Operations`、`People`\n5. 将地点统一为 `Beijing`、`Shanghai`、`Shenzhen`、`Singapore`，将状态统一为 `Active`、`Leave`、`Inactive`\n6. 保留 `Manager` 原始值不变，保持员工编号和列顺序不变\n7. 输出文件只需要包含 `Clean` 一个 sheet\n'

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
