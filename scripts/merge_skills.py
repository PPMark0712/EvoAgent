import argparse
import json
import os
import signal

from agent import Agent
from agent.nodes.base import BaseNode
from agent.utils import get_argparser


PROMPT_TEMPLATE = """
你现在担任【高级知识架构师】，任务是审计并合并外部 Agent 技能库。

### 核心任务
目录 `{skill_path}` 是一个在线技能库。你必须判断其内容的工程价值，并将高价值内容永久内化到你的“记忆知识库”中。

### 阶段一：多维度价值评估
在合并前，请基于以下维度对 `{skill_path}` 下的每个技能进行打分（内部逻辑）：
1. **通用复用性**：该技能是否是某类场景下的高价值方法论，比如启动浏览器的通用流程。你不需要读取LICENCE相关文件，若需要则直接复制过来。
2. **特殊场景增强**：是否解决了某些特定场景的难题，比如某个特定网页的API用法示例。
3. **冗余排查**：如果该技能与你现有记忆重合，则进行部分合并整理或者拒绝合并。

### 阶段二：知识内化与重构指令
由于合并后你将失去对原路径的访问权，请执行以下“深层迁移”操作：
1. **全量克隆**：禁止使用外部链接引用。若需要内化知识，必须将技能目录完整复制到你的记忆目录中，可以整理到某个子目录。用复制命令而非逐文件file_write，以提高效率。
2. **目录树治理**：
    - **宽度限制**：若根目录或某个分类下的目录或文件数量过多，必须进行“子目录重构”，例如将 python 和 go 编写规范整理到一个代码规范目录下。
    - **索引维护**：维护所有修改过的目录的 `index.md`，确保新增技能的描述准确且路径可追踪。
    - **合并重复**：若发现重复或相似的目录或文件，可以考虑扩充成一个更大的目录并合并。
3. **无缝整合**：新内容必须符合你现有记忆的命名规范和文档格式。

### 阶段三：记忆目录
完成知识内化后，必须检查所有编辑过的记忆目录，确保目录结构符合要求（宽度限制、索引维护、合并重复）。
"""

PROMPT_COMFIRM = """
请再次确认目录结构的宽度和深度符合要求。
结构上限约束：除了最小SKILL单元内部以外，每一级目录尽量保持不超过 10 个子目录、不超过 10 个文件。
若超过，考虑新增一些分类目录，并将相关记忆移动到分类目录中，同时更新index。

### 期望确认格式
在完成知识内化（或忽略）、记忆整理后，最终给用户一个确认消息，放在一个json代码块中，格式如下：
```json
{{
    "evaluation_report": "说明你如何评估这一目录下的技能，比如哪些价值高，哪些价值低。",
    "memory_changes": "str，说明内化的知识，以及变更的记忆目录。",
    "drops": "str，说明被舍弃的内容，以及舍去技能的原因。"
}}
```
"""


def parse_args():
    parser = get_argparser()
    parser.add_argument("--data_path", type=str, required=True, help="Path to skills root directory.")
    return parser.parse_args()


def provider_from_list(items: list[str]):
    idx = 0
    def provider() -> str:
        nonlocal idx
        if idx >= len(items):
            raise EOFError
        v = items[idx]
        idx += 1
        return v
    return provider


def main():
    def _sigint_handler(_signum, _frame):
        raise SystemExit(130)
    signal.signal(signal.SIGINT, _sigint_handler)

    args = parse_args()
    base_output_path = args.output_path
    entries = sorted(os.listdir(args.data_path))
    print(json.dumps(entries, indent=2))
    for entry in entries:
        # need_continue = input(f"Ready to process {entry}? (y/n)")
        # if need_continue.lower() != "y":
        #     continue
        skill_path = os.path.join(args.data_path, entry)
        if not os.path.isdir(skill_path):
            continue

        prompt = PROMPT_TEMPLATE.format(skill_path=skill_path)
        provider = provider_from_list([prompt, PROMPT_COMFIRM])

        run_args = argparse.Namespace(**vars(args))
        run_args.output_path = base_output_path
        run_args.save_name = entry

        BaseNode.set_user_input_provider(provider)
        agent = Agent()
        try:
            agent.run(run_args)
        except EOFError:
            continue


if __name__ == '__main__':
    main()

"""bash script
model_name=...
merge_skills_output_path=/path/to/merge_skills
python scripts/merge_skills2.py --model ${model_name} \
    --output_path $merge_skills_output_path/${model_name}/logs \
    --memory_dir $merge_skills_output_path/${model_name}/result \
    --data_path /path/to/skills
"""
