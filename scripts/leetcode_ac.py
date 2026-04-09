text = f"""
力扣题目首页：https://leetcode.cn/problemset/。
找一道没做过的题目，通过它。
注意，你必须先先仔细读取力口提交相关记忆，否则很可能找不到代码编辑的方法。
先本地运行，再填入代码编辑区，再测试运行，再提交。
""".strip()

def provider():
    return text
# python main.py --model ... --loop_provider scripts/leetcode_ac.py --loop_interval 300
