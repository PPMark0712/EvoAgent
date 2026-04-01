import argparse


def get_argparser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(description="EvoAgent main entry point")

    # Core runtime config
    parser.add_argument("--api_type", type=str, default=None, choices=["openai", "anthropic"], help="Force API type (optional).")
    parser.add_argument("--model", type=str, required=True, help="Model name or path for WorkerNode")
    parser.add_argument("--no_stream", action="store_true", help="Disable streaming")
    parser.add_argument("--show_system_prompt", action="store_true", help="Show system prompt in outputs")

    # I/O and persistence
    parser.add_argument("--load_path", type=str, default="", help="Existing run output directory to load history from (absolute or project-relative).")
    parser.add_argument("--memory_dir", type=str, default="memory", help="Memory directory (absolute or project-relative).")
    parser.add_argument("--output_path", type=str, default="output", help="Path to store output files and logs")
    parser.add_argument("--save_name", type=str, default="", help="Save name for output directory prefix.")

    # Loop mode
    parser.add_argument("--loop_interval", type=int, default=300, help="Minimum interval in seconds between loop input.")
    parser.add_argument("--loop_provider", type=str, default=None, help="Path to a python file that defines provider() -> str.")

    # Web server
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host")
    parser.add_argument("--max_graphs", type=int, default=5, help="Max active graphs in web mode")
    parser.add_argument("--port", type=int, default=8000, help="Web server port")
    parser.add_argument("--web", action="store_true", help="Run web server (Bottle + SSE)")
    return parser
