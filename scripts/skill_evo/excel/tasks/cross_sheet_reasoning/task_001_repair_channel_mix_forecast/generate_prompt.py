import argparse
import os


PROMPT = """你现在在一个 Excel benchmark 工作区中工作。

请读取工作区中的 `channel_mix_forecast.xlsx`，并修复 `Output` sheet 中损坏的跨 sheet 公式：
1. `Drivers` sheet 提供每个账户的 `Base Units`、`Base Price` 和 `Renewal Probability`
2. `Mix` sheet 提供与账户相关的渠道 mix 信息，但其中包含重复 key、归档行、缺失值和干扰行
3. 注意：`Drivers` 与 `Mix` 并不是按同一物理行对齐的，不能假设相同行就是同一账户；只有与 `Output` 当前账户/区域一致的有效 mix 记录才应参与计算
4. `Output` sheet 需要恢复为可重算的派生结果表：先得到 gross sales，再据此得到 enterprise sales、partner discount、net sales、services 和 total ARR；缺失的折扣率或 attach rate 应按 0 处理
5. 保留 `A:B`、sheet 名、记录顺序和所有输入数据不变；所有结果必须保留为 Excel 公式，不要写成静态数值
6. 保存后的文件名仍然是 `channel_mix_forecast.xlsx`"""


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
