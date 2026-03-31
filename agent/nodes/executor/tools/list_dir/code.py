import os


def list_dir(dir_path: str, max_depth: int = 1, max_entries: int = 20, show_info: bool = True) -> dict:
    try:
        root = os.path.abspath(dir_path)
        max_depth = int(max_depth)
        max_entries = int(max_entries)
        show_info = bool(show_info)
        if max_depth < 0:
            return {"status": "error", "error": "ValueError: max_depth must be >= 1"}
        if max_entries < 1:
            return {"status": "error", "error": "ValueError: max_entries must be >= 1"}
        if not os.path.isdir(root):
            return {"status": "error", "error": f"NotADirectoryError: {root}"}

        info_cache: dict[str, tuple[int, int]] = {}
        truncated = False
        printed_entries = 0

        def _safe_scandir(path: str):
            try:
                with os.scandir(path) as it:
                    return list(it)
            except (OSError, PermissionError):
                return []

        def _sorted_children(path: str):
            children = _safe_scandir(path)

            def _is_dir(entry) -> bool:
                try:
                    return entry.is_dir(follow_symlinks=False)
                except OSError:
                    return False

            children.sort(key=lambda e: (not _is_dir(e), e.name))
            return children

        def _subtree_info(path: str) -> tuple[int, int]:
            if not show_info:
                return (0, 0)
            cached = info_cache.get(path)
            if cached is not None:
                return cached
            max_depth_to_leaf = 0
            total_entries = 0
            for child in _safe_scandir(path):
                total_entries += 1
                try:
                    is_dir = child.is_dir(follow_symlinks=False)
                except OSError:
                    is_dir = False
                if is_dir:
                    child_depth, child_size = _subtree_info(child.path)
                    total_entries += child_size
                    max_depth_to_leaf = max(max_depth_to_leaf, 1 + child_depth)
            info_cache[path] = (max_depth_to_leaf, total_entries)
            return (max_depth_to_leaf, total_entries)

        def _format_dir_label(path: str, depth_from_root: int) -> str:
            name = os.path.basename(path.rstrip(os.sep)) or path
            if not show_info:
                return f"{name}/"
            depth_to_leaf, size = _subtree_info(path)
            return f"{name}/ (depth={depth_to_leaf}, size={size})"

        if show_info:
            root_depth, root_size = _subtree_info(root)
            lines: list[str] = [f"{root}/ (depth={root_depth}, size={root_size})"]
        else:
            lines = [f"{root}/"]

        def _walk_dir(path: str, depth: int, prefix: str):
            nonlocal printed_entries, truncated
            if truncated:
                return
            if depth >= max_depth:
                return

            children = _sorted_children(path)
            for i, child in enumerate(children):
                if printed_entries >= max_entries:
                    truncated = True
                    lines.append(prefix + "… (truncated, consider lower max_depth or larger max_entries)")
                    return
                is_last = i == len(children) - 1
                connector = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                try:
                    is_dir = child.is_dir(follow_symlinks=False)
                except OSError:
                    is_dir = False

                child_depth = depth + 1
                if is_dir:
                    lines.append(prefix + connector + _format_dir_label(child.path, child_depth))
                else:
                    lines.append(prefix + connector + child.name)
                printed_entries += 1

                if is_dir:
                    _walk_dir(child.path, child_depth, next_prefix)
                    if truncated:
                        return

        _walk_dir(root, 0, "")

        result_str = "\n".join(lines)

        index_path = os.path.join(root, "index.md")
        if os.path.isfile(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_content = f.read().rstrip()
                if index_content:
                    result_str += "\n\n[index.md]\n" + index_content + "\n"
            except OSError:
                pass

        return {"status": "success", "result": result_str}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)}"}
