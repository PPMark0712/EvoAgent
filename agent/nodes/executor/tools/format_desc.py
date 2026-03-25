import json
import os


def format_all_desc_files():
    tools_dir = "."
    for tool_name in os.listdir(tools_dir):
        tool_dir = os.path.join(tools_dir, tool_name)
        if os.path.isdir(tool_dir):
            desc_file = os.path.join(tool_dir, "desc.json")
            if os.path.exists(desc_file):
                try:
                    with open(desc_file, "r") as f:
                        data = json.load(f)
                    with open(desc_file, "w") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"Formatted {desc_file}")
                except Exception as e:
                    print(f"Error formatting {desc_file}: {e}")


if __name__ == "__main__":
    format_all_desc_files()
