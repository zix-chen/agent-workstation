"""Pure output policy; no runtime hooks or global monkey-patching."""

from collections.abc import Callable

TOOL_DEFAULTS = {
    "exec_command": {"verbosity": "preview", "preview_bytes": 8192},
    "write_stdin": {"verbosity": "preview", "preview_bytes": 8192},
    "kill_command": {"verbosity": "preview", "preview_bytes": 8192},
    "read_file": {"max_bytes": 32768},
    "git_diff": {"max_bytes": 65536},
    "git_show": {"max_bytes": 65536},
    "search_text": {"max_results": 200, "max_preview_bytes": 320},
    "list_files": {"max_results": 1000},
}


def excerpt(data: bytes, budget: int) -> bytes:
    if len(data) <= budget:
        return data
    marker = b"\n... [preview omitted; use read_output] ...\n"
    if budget <= len(marker):
        return data[-budget:] if budget else b""
    available = budget - len(marker)
    head = available // 3
    return data[:head] + marker + data[-(available - head) :]


def command_preview(segments: Callable, limit: int) -> tuple[str, list[str]]:
    """Give short stderr its share; preserve upstream eviction gaps honestly."""
    streams = []
    for name in ("stdout", "stderr"):
        head, tail, tail_start, total, _ = segments(name)
        if not total:
            continue
        gap = tail_start > len(head)
        data = (
            head + b"\n... [retained output gap] ...\n" + tail
            if gap
            else head + tail[max(0, len(head) - tail_start) :]
        )
        streams.append((name, data, gap))
    if not streams:
        return "", []
    labels = [f"--- {name} ---\n".encode() for name, _, _ in streams]
    remaining = max(0, limit - sum(map(len, labels)) - len(streams) + 1)
    budgets = [0] * len(streams)
    order = sorted(range(len(streams)), key=lambda i: len(streams[i][1]))
    for position, index in enumerate(order):
        share = remaining // (len(order) - position)
        budgets[index] = min(len(streams[index][1]), share)
        remaining -= budgets[index]
    sections, omitted = [], []
    for index, (name, data, gap) in enumerate(streams):
        sections.append(labels[index] + excerpt(data, budgets[index]))
        if gap or len(data) > budgets[index]:
            omitted.append(name)
    return b"\n".join(sections)[:limit].decode("utf-8", errors="ignore"), omitted
