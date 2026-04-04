# EvoAgent

一个基于 LangGraph 的轻量级 Agent 框架：`User → Worker(LLM) → Executor(工具)`，支持文件/命令/浏览器三类工具协同与多标签页浏览器操作。

## 🚀 快速开始

### 1. 环境配置

要求 Python 版本：3.12

```bash
# 创建 conda 环境
conda create -n evo_agent python=3.12 -y
conda activate evo_agent

# 安装依赖
pip install -r requirements.txt
```

### 2. API 配置

在项目根目录创建 `.env` 文件，配置模型预设（preset）路径与各 preset 对应的 API 变量。默认 preset 文件路径为 `agent/models/model_presets.json`（也可通过 `EVOAGENT_MODEL_PRESETS_PATH` 覆盖）。

推荐做法：先复制示例配置，再按 preset 增加对应的 API 变量：
```bash
cp .env_example .env
```

以 Qwen 为例：在 `.env` 中新增一组变量，然后在 preset 中通过 `api_key_env` / `api_base_env` 引用即可：

```env
QWEN_OPENAI_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_OPENAI_API_KEY=sk-xxxx
```

可选：配置模型预设列表（推荐用于 WebUI 切换模型）。在 `.env` 中指定：

```env
EVOAGENT_MODEL_PRESETS_PATH=agent/models/model_presets.json
EVOAGENT_DEFAULT_MODEL=qwen3.5-flash
```

`model_presets.json` 结构示例（支持每个模型一套完整 config，包括 special_tokens、extra_body 等）：

```json
{
  "default": {
    "label": "Claude Sonnet",
    "api_type": "anthropic",
    "model": "claude-3-7-sonnet-latest",
    "api_key_env": "ANTHROPIC_API_KEY_MAIN",
    "api_base_env": "ANTHROPIC_API_BASE_MAIN",
    "stream": true,
    "special_tokens": { "thinking": "thinking", "toolcall": "toolcall" },
    "model_kwargs": { "extra_body": { "enable_thinking": false } }
  }
}
```

### 3. 运行

#### WebUI 模式
```bash
python main.py --model {MODEL} --api_type {openai|anthropic} --web --port 1234
```
启动后访问 `http://localhost:1234`。

常用可选参数：
- `--show_system_prompt`：在对话历史中展示 system prompt（默认不展示）
- `--max_graphs`：Web 模式最多同时保活的 graph 数量（LRU，默认 5）
- `--memory_backup`：新建会话时将 `--memory_dir` 备份到该会话目录下（默认不备份）

#### 浏览器驱动（必做一次）
`web_scan` / `web_execute_js` 依赖浏览器侧的 Tampermonkey UserScript，需要先把仓库里的脚本安装到“篡改猴”插件：
- 打开浏览器扩展商店安装 Tampermonkey（篡改猴）
- 在 Tampermonkey 中创建新脚本，将仓库文件内容粘贴进去并保存：
  - [agent/nodes/executor/tools/evoagent_driver.user.js](./agent/nodes/executor/tools/evoagent_driver.user.js)
- 打开任意网页，右下角出现连接状态角标（已连接/未连接）即表示脚本生效
- 可以在部分网页禁用该脚本，如包含重要信息的页面、EvoAgent的localhost页面等，避免重要信息被篡改。
- 建议在默认浏览器中使用，这样EvoAgent使用命令启动浏览器界面时也可以正常工作。

#### CLI 模式
```bash
python main.py --model {MODEL} --api_type {openai|anthropic}
```

#### 自动化循环模式
```bash
python main.py --model {MODEL} --api_type {openai|anthropic} --loop_provider /path/to/provider.py --loop_interval 300
```
- `--loop_provider`: 指定一个 Python 文件的绝对路径，文件内需提供 `provider() -> str`。
- `--loop_interval`: 限制两次任务触发的**最小时间间隔**（秒）。
> 注意：`--web` 与 `--loop_provider` 同时指定时，会忽略 loop 模式并打印 warning。

## 🛠️ 工具箱

| 工具 | 描述 |
|------|------|
| `ask_user` | 向用户发问并等待输入（用于关键决策或被阻塞时） |
| `command_run` | 在终端执行命令 |
| `file_read` | 读取文件内容（可选行范围与行号标记） |
| `file_replace` | 替换文件中第一次出现的指定字符串 |
| `file_write` | 写入文件内容 |
| `list_dir` | 以树状结构查看目录（可选读取 `index.md`） |
| `regex_search` | 正则搜索文件路径或文件内容（可限制返回条数） |
| `task_status_update` | 更新 `agent_state.task_status`，用于跟踪复杂任务进度 |
| `web_execute_js` | 在当前浏览器标签页执行自定义 JavaScript，返回执行结果与页面变化 |
| `web_scan` | 获取网页内容与标签页列表（`simplified_html`/`tabs_only`/`text_only`） |

## 常用参数

- `--host`：Web 服务监听地址
- `--max_graphs`：Web 模式最多同时保活的 graph 数量（LRU）
- `--memory_backup`：新建会话时备份 `--memory_dir` 到会话目录下（默认不备份）
- `--memory_dir`：记忆目录（绝对路径或相对项目路径，默认 `memory`）
- `--model`：指定使用的模型
- `--loop_interval`：循环输入的最小触发间隔（秒）
- `--loop_provider`：指定循环输入 provider（提供则启用循环输入模式）
- `--output_path`：会话输出根目录，默认 `output`，不得有自动保存的会话记录以外的内容
- `--port`：Web 服务监听端口，默认 1234
- `--show_system_prompt`：在输出中展示 system prompt
- `--web`：启动 Web 界面

## 🙏 致谢

本项目中 Web 相关工具（包括 `web_scan`、`web_execute_js`）参考了 [GenericAgent](https://github.com/lsdefine/GenericAgent)。
