"""Bounded multi-repository rule discovery. No upstream/private imports here."""

from pathlib import Path
from typing import Callable

NAMES = ("AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD")
SKIP = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
        "target",
        "__pycache__",
        ".worktrees",
        ".codex-worktrees",
        ".validation",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".reference",
    }
)


def safe_file(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
        return resolved.is_file()
    except (OSError, ValueError, RuntimeError):
        return False


def discover(
    root: Path, git_files: Callable, warnings: list[str], *, max_children: int = 128, max_files: int = 512
) -> list[str]:
    """Only use Git metadata at actual repo roots; never recurse the workspace."""
    root = root.resolve(strict=True)
    found: list[str] = []
    seen: set[tuple[int, int]] = set()

    def add(path: Path) -> None:
        if not safe_file(path, root):
            return
        relative = path.relative_to(root)
        if any(p in SKIP for p in relative.parts[:-1]):
            return
        stat = path.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity not in seen:
            seen.add(identity)
            found.append(relative.as_posix())

    def scan(directory: Path) -> None:
        # is_file also covers a git worktree's .git indirection file.
        paths = git_files(directory) if (directory / ".git").exists() else None
        if paths is None:
            paths = list(NAMES)
        for relative in paths:
            p = Path(relative)
            if p.is_absolute() or ".." in p.parts:
                continue
            add(directory / p)

    scan(root)
    if not (root / ".git").exists():
        visited = 0
        # Cap both scanned entries and repositories, rather than sorting an entire tree.
        for entry_index, child in enumerate(root.iterdir()):
            if entry_index >= 4096:
                warnings.append("Workspace entry scan capped at 4096; use workspace_guide for your target.")
                break
            if child.name in SKIP or child.is_symlink() or not child.is_dir():
                continue
            if visited >= max_children:
                warnings.append("Child-directory scan capped; use workspace_guide for the target repository.")
                break
            visited += 1
            scan(child)
    if len(found) > max_files:
        warnings.append("Instruction catalog truncated; target-path discovery is still required.")
    return sorted(found)[:max_files]


def target_directory(root: Path, target: str) -> Path:
    root = root.resolve(strict=True)
    candidate = Path(target)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Target must be workspace-relative without '..'.")
    resolved = (root / candidate).resolve(strict=True)
    resolved.relative_to(root)
    return resolved if resolved.is_dir() else resolved.parent


def ancestors(root: Path, target: str) -> list[Path]:
    directory = target_directory(root, target)
    result = [directory]
    while result[-1] != root:
        result.append(result[-1].parent)
    return list(reversed(result))
