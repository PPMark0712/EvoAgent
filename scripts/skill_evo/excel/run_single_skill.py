import argparse
import json
import os
import shutil
import signal
import subprocess
import sys

from agent import Agent
from agent.nodes.base import BaseNode
from agent.utils import get_argparser
from tqdm import tqdm


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLETION_TAG = "completion_tag"
SINGLE_SKILL_PROMPT_TEMPLATE = """你现在要使用一个指定的 Excel skill 来完成任务。
先阅读记忆中的这个 skill：`{skill_name}`
然后只基于这个skill的方法和规则来完成下面任务，禁止使用记忆中其他skill。
任务如下：
{task_prompt}
"""
NO_SKILL_PROMPT_TEMPLATE = """你现在要在不读取任何记忆、不使用任何 skill 的前提下完成 Excel 任务。

禁止读取记忆中的任何 skill。
禁止使用任何已有 skill 的方法说明。
你只能基于当前任务描述和工作区内文件自行完成任务。

任务如下：
{task_prompt}
"""


def parse_args():
    parser = get_argparser()
    parser.add_argument("--tasks_root", type=str, default=os.path.join(CURRENT_DIR, "tasks"), help="Root directory containing Excel benchmark tasks.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for the number of tasks to run. 0 means no limit.")
    parser.add_argument("--bon", type=int, default=1, help="Independent run count for each task.")
    parser.add_argument("--mode", type=str, default="single_skill", choices=["single_skill", "no_skill"], help="Runner mode.")
    parser.add_argument(
        "--tasks",
        type=str,
        default="",
        help="Optional comma-separated task group filters, e.g. 'data_cleaning,summary_sheet'.",
    )
    parser.add_argument(
        "--skills_root",
        type=str,
        default="",
        help="Optional skills root. In single-skill mode, each first-level subdirectory under this path is treated as one skill. If provided, it must be the same as memory_dir.",
    )
    return parser.parse_args()


def safe_name(s):
    s = (s or "").strip()
    if not s:
        return "default"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in s)[:80]


def _normalize_task_filters(tasks):
    return [part.strip().strip("/\\") for part in (tasks or "").split(",") if part.strip()]


def _match_task_filter(rel_path, task_filters):
    if not task_filters:
        return True
    task_group = rel_path.strip("/\\").split(os.sep)[0]
    return task_group in task_filters


def find_task_dirs(tasks_root, limit, tasks=None):
    task_dirs = []
    task_filters = _normalize_task_filters(tasks)
    for root, _dirs, files in os.walk(tasks_root):
        del _dirs
        required = {
            "generate_prompt.py",
            "create_workspace.py",
            "create_gold.py",
            "evaluate_workspace.py",
        }
        if required.issubset(set(files)):
            rel = os.path.relpath(root, tasks_root)
            if _match_task_filter(rel, task_filters):
                task_dirs.append(root)
    task_dirs.sort()
    if limit > 0:
        task_dirs = task_dirs[:limit]
    return task_dirs


def find_skill_dirs(skills_root):
    if not os.path.isdir(skills_root):
        raise ValueError("skills root does not exist")
    skill_dirs = []
    for name in sorted(os.listdir(skills_root)):
        path = os.path.join(skills_root, name)
        if os.path.isdir(path):
            skill_dirs.append(path)
    if not skill_dirs:
        raise ValueError("no skill directories found under memory_dir; expected each first-level subdirectory to be a skill")
    return skill_dirs


def run_python(script_path, output_path, extra_args=None):
    cmd = [sys.executable, script_path]
    if output_path is not None:
        cmd.append(output_path)
    if extra_args:
        cmd.extend(extra_args)
    subprocess.run(cmd, check=True)


def find_latest_run_dir(output_path):
    names = sorted(os.listdir(output_path))
    dirs = [os.path.join(output_path, name) for name in names if os.path.isdir(os.path.join(output_path, name))]
    return dirs[-1] if dirs else None


def get_completion_tag_path(task_output_dir):
    return os.path.join(task_output_dir, COMPLETION_TAG)


def prepare_task_output_dir(task_output_dir):
    completion_tag_path = get_completion_tag_path(task_output_dir)
    if os.path.isfile(completion_tag_path):
        return False
    if os.path.isdir(task_output_dir):
        shutil.rmtree(task_output_dir)
    os.makedirs(task_output_dir, exist_ok=True)
    return True


def mark_task_completed(task_output_dir):
    with open(get_completion_tag_path(task_output_dir), "w", encoding="utf-8"):
        pass


def summarize_messages(run_dir):
    path = os.path.join(run_dir, "logging", "messages", "messages.jsonl")
    ai_rounds = 0
    input_tokens = 0
    output_tokens = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                continue
            if item.get("type") == "ai":
                ai_rounds += 1
            data = item.get("data") or {}
            usage = data.get("usage_metadata") or {}
            input_tokens += usage.get("input_tokens", 0) or 0
            output_tokens += usage.get("output_tokens", 0) or 0
    return {
        "ai_rounds": ai_rounds,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def build_task_prompt(task_prompt, workspace_dir, mode, skill_name=""):
    prompt = task_prompt
    if mode == "single_skill" and skill_name:
        prompt = SINGLE_SKILL_PROMPT_TEMPLATE.format(skill_name=skill_name, task_prompt=task_prompt)
    elif mode == "no_skill":
        prompt = NO_SKILL_PROMPT_TEMPLATE.format(task_prompt=task_prompt)
    prompt = (
        prompt
        + "\n\n工作区绝对路径："
        + workspace_dir
        + "\n请只在这个工作区内读写文件，并在完成后保留结果文件在工作区内。"
    )
    return prompt


def run_agent(args, prompt, agent_output_dir, memory_dir, working_dir):
    provided = False

    def provider():
        nonlocal provided
        if provided:
            raise EOFError()
        provided = True
        return prompt

    run_args = argparse.Namespace(**vars(args))
    run_args.output_path = agent_output_dir
    run_args.memory_dir = memory_dir
    run_args.working_dir = working_dir
    run_args.show_system_prompt = True
    BaseNode.set_user_input_provider(provider)
    agent = Agent()
    try:
        agent.run(run_args, emit_to_terminal=False)
    except EOFError:
        pass


def build_stats(results):
    run_count = len(results)
    passed_count = sum(1 for item in results if item.get("passed"))
    ai_rounds = sum(item.get("ai_rounds", 0) or 0 for item in results)
    input_tokens = sum(item.get("input_tokens", 0) or 0 for item in results)
    output_tokens = sum(item.get("output_tokens", 0) or 0 for item in results)
    return {
        "run_count": run_count,
        "acc": (passed_count / run_count) if run_count else 0.0,
        "iters": (ai_rounds / run_count) if run_count else 0.0,
        "avg_input_tokens": (input_tokens / run_count) if run_count else 0.0,
        "avg_output_tokens": (output_tokens / run_count) if run_count else 0.0,
    }


def load_task_prompt(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_results_from_skill_output(skill_output_root):
    results = []
    for root, dirs, files in os.walk(skill_output_root):
        dirs.sort()
        files.sort()
        if "result.json" not in files:
            continue
        if not os.path.isfile(get_completion_tag_path(root)):
            continue
        result_path = os.path.join(root, "result.json")
        with open(result_path, "r", encoding="utf-8") as f:
            results.append(json.load(f))
    results.sort(key=lambda item: (item.get("task_relative_path", ""), item.get("run_index", 0)))
    return results


def build_run_jobs(args, task_dirs, mode_settings_list):
    bon = args.bon if args.bon > 0 else 1
    run_jobs = []
    for mode_settings in mode_settings_list:
        skill_name = mode_settings["skill_name"]
        output_skill_name = mode_settings["output_skill_name"]
        skill_path = mode_settings["skill_path"]
        memory_source_path = mode_settings["memory_source_path"]
        skill_output_root = os.path.join(args.output_path, output_skill_name)
        for task_dir in task_dirs:
            rel = os.path.relpath(task_dir, args.tasks_root)
            task_output_root = os.path.join(skill_output_root, rel)
            for run_index in range(1, bon + 1):
                run_name = "run_%03d" % run_index
                task_output_dir = os.path.join(task_output_root, run_name)
                run_jobs.append(
                    {
                        "mode_settings": mode_settings,
                        "skill_name": skill_name,
                        "output_skill_name": output_skill_name,
                        "skill_path": skill_path,
                        "memory_source_path": memory_source_path,
                        "skill_output_root": skill_output_root,
                        "task_dir": task_dir,
                        "task_relative_path": rel,
                        "task_output_root": task_output_root,
                        "task_output_dir": task_output_dir,
                        "run_index": run_index,
                    }
                )
    return run_jobs


def filter_pending_run_jobs(run_jobs):
    pending_run_jobs = []
    for job in run_jobs:
        if os.path.isfile(get_completion_tag_path(job["task_output_dir"])):
            continue
        pending_run_jobs.append(job)
    return pending_run_jobs


def prepare_memory_backups(args, mode_settings_list):
    if args.mode != "single_skill":
        return
    backup_root = os.path.join(args.output_path, "memory")
    os.makedirs(backup_root, exist_ok=True)
    for mode_settings in mode_settings_list:
        memory_source_path = mode_settings["memory_source_path"]
        backup_dir = os.path.join(backup_root, mode_settings["output_skill_name"])
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
        shutil.copytree(memory_source_path, backup_dir)
        mode_settings["memory_runtime_path"] = backup_dir


def resolve_mode_settings(args):
    if args.mode == "no_skill":
        return [
            {
                "skill_name": "no_skill",
                "output_skill_name": safe_name("no_skill"),
                "skill_path": "",
                "memory_source_path": "",
                "memory_runtime_path": "",
            }
        ]

    source_memory_root = args.memory_dir if os.path.isabs(args.memory_dir) else os.path.abspath(args.memory_dir)
    skills_root = source_memory_root
    if args.skills_root:
        skills_root = args.skills_root if os.path.isabs(args.skills_root) else os.path.abspath(args.skills_root)
        if os.path.normpath(skills_root) != os.path.normpath(source_memory_root):
            raise ValueError("in single-skill mode, memory_dir itself is the skills root, so skills_root must be the same path as memory_dir")
    skill_dirs = find_skill_dirs(skills_root)
    return [
        {
            "skill_name": os.path.basename(skill_dir.rstrip(os.sep)),
            "output_skill_name": safe_name(os.path.basename(skill_dir.rstrip(os.sep))),
            "skill_path": skill_dir,
            "memory_source_path": skill_dir,
            "memory_runtime_path": "",
        }
        for skill_dir in skill_dirs
    ]


def main(args):
    def sigint_handler(*_args):
        del _args
        raise SystemExit(130)

    signal.signal(signal.SIGINT, sigint_handler)
    os.makedirs(args.output_path, exist_ok=True)
    task_dirs = find_task_dirs(args.tasks_root, args.limit, args.tasks)
    mode_settings_list = resolve_mode_settings(args)
    prepare_memory_backups(args, mode_settings_list)
    run_jobs = build_run_jobs(args, task_dirs, mode_settings_list)
    pending_run_jobs = filter_pending_run_jobs(run_jobs)
    total_steps = len(run_jobs)
    completed_steps = total_steps - len(pending_run_jobs)
    progress = tqdm(total=total_steps, initial=completed_steps, desc="Tasks", unit="step")

    for job in pending_run_jobs:
        skill_name = job["skill_name"]
        skill_path = job["skill_path"]
        memory_source_path = job["memory_source_path"]
        memory_runtime_path = job["mode_settings"].get("memory_runtime_path", "")
        skill_output_root = job["skill_output_root"]
        task_dir = job["task_dir"]
        rel = job["task_relative_path"]
        task_output_root = job["task_output_root"]
        task_output_dir = job["task_output_dir"]
        run_index = job["run_index"]
        os.makedirs(skill_output_root, exist_ok=True)
        os.makedirs(task_output_root, exist_ok=True)
        prepare_task_output_dir(task_output_dir)
        workspace_dir = os.path.join(task_output_dir, "workspace")
        gold_dir = os.path.join(task_output_dir, "gold")
        prompt_path = os.path.join(task_output_dir, "prompt.txt")
        evaluator_output_file = os.path.join(task_output_dir, "result.json")
        agent_output_dir = os.path.join(task_output_dir, "agent_runs")
        task_memory_dir = memory_runtime_path if args.mode == "single_skill" else os.path.join(task_output_dir, "empty_memory")

        run_python(os.path.join(task_dir, "create_workspace.py"), workspace_dir)
        run_python(os.path.join(task_dir, "create_gold.py"), gold_dir)
        run_python(os.path.join(task_dir, "generate_prompt.py"), prompt_path)

        task_prompt = load_task_prompt(prompt_path)
        prompt = build_task_prompt(task_prompt, workspace_dir, args.mode, skill_name)

        agent_error = ""
        run_dir = None
        usage_summary = {
            "ai_rounds": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        try:
            if args.mode == "single_skill":
                if not os.path.isdir(task_memory_dir):
                    raise ValueError(f"memory dir does not exist: {task_memory_dir}")
            else:
                os.makedirs(task_memory_dir, exist_ok=True)
            run_agent(args, prompt, agent_output_dir, task_memory_dir, workspace_dir)
            run_dir = find_latest_run_dir(agent_output_dir)
            usage_summary = summarize_messages(run_dir)
        except Exception as e:
            agent_error = str(e)

        eval_cmd = [
            sys.executable,
            os.path.join(task_dir, "evaluate_workspace.py"),
            workspace_dir,
            gold_dir,
            evaluator_output_file,
        ]
        subprocess.run(eval_cmd, check=False)

        with open(evaluator_output_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        result["task_relative_path"] = rel
        result["run_index"] = run_index
        result["skill_name"] = skill_name
        result["skill_path"] = skill_path
        result["memory_source_path"] = memory_source_path
        result["memory_runtime_path"] = task_memory_dir
        result["agent_error"] = agent_error
        result["ai_rounds"] = usage_summary["ai_rounds"]
        result["input_tokens"] = usage_summary["input_tokens"]
        result["output_tokens"] = usage_summary["output_tokens"]
        result["total_tokens"] = usage_summary["total_tokens"]
        with open(evaluator_output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        mark_task_completed(task_output_dir)
        progress.update(1)

    progress.close()

    for mode_settings in mode_settings_list:
        skill_name = mode_settings["skill_name"]
        output_skill_name = mode_settings["output_skill_name"]
        skill_path = mode_settings["skill_path"]
        memory_source_path = mode_settings["memory_source_path"]
        skill_output_root = os.path.join(args.output_path, output_skill_name)
        os.makedirs(skill_output_root, exist_ok=True)
        all_results = load_results_from_skill_output(skill_output_root)

        task_groups = {}
        for result in all_results:
            rel = result.get("task_relative_path", "")
            task_group = rel.split(os.sep)[0] if rel else "unknown"
            if task_group not in task_groups:
                task_groups[task_group] = []
            task_groups[task_group].append(result)

        summary = {
            "overall": build_stats(all_results),
            "task_groups": {},
            "skill_name": skill_name,
            "skill_path": skill_path,
            "memory_source_path": memory_source_path,
        }
        for task_group in sorted(task_groups):
            summary["task_groups"][task_group] = build_stats(task_groups[task_group])

        with open(os.path.join(skill_output_root, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(parse_args())
