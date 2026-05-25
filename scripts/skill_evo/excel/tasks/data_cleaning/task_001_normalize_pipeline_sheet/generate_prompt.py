import argparse
import os


PROMPT = '你现在在一个 Excel benchmark 工作区中工作。\\n\\n请读取工作区中的 `pipeline_raw.xlsx`，并创建一个新的输出文件 `pipeline_clean.xlsx`：\\n1. 从 `Raw` sheet 读取原始数据，注意真正的数据表头在第 3 行，工作表中还混有标题说明和侧边注释\\n2. 生成一个名为 `Clean` 的 sheet，列顺序固定为 `Deal ID`, `Stage`, `Amount`, `Owner`, `Region`\\n3. 跳过空白、说明性单元格和表格外的干扰内容，只保留有效数据行\\n4. 将阶段统一为 `Proposal`、`Closed Won`、`Qualified`、`Negotiation`\\n5. 将金额统一为数值，去掉空格、货币符号和千分位分隔符\\n6. 保留 `Owner` 原始值不变，将区域统一为 `North`、`South`、`West`、`East`\\n7. 输出文件只需要包含 `Clean` 一个 sheet\\n'


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
