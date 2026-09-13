"""Small release hygiene gate, complementary to a real secret scanner."""

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "__pycache__", "dist", "build", ".ruff_cache", ".pytest_cache"}
PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE" + r" KEY-----")),
    ("personal home path", re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/")),
    (
        "private IPv4",
        re.compile(
            r"(?<![0-9])(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?![0-9])"
        ),
    ),
]


def files(directory):
    for path in directory.iterdir():
        if path.name in SKIP or path.name.startswith(".venv-") or path.name.endswith(".egg-info"):
            continue
        if path.is_symlink():
            yield path
        elif path.is_dir():
            yield from files(path)
        else:
            yield path


def main():
    errors = []
    count = 0
    for path in files(ROOT):
        relative = path.relative_to(ROOT)
        count += 1
        if path.is_symlink():
            errors.append(f"{relative}: release tree must not contain symlinks")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            errors.append(f"{relative}: unexpected binary in source tree")
            continue
        for name, pattern in PATTERNS:
            if pattern.search(text):
                errors.append(f"{relative}: {name}")
        if path.suffix == ".py":
            tree = ast.parse(text)
            if "compat" not in relative.parts and relative.parts[0] == "agent_workstation":
                for node in ast.walk(tree):
                    names = (
                        [node.module or ""]
                        if isinstance(node, ast.ImportFrom)
                        else [x.name for x in node.names]
                        if isinstance(node, ast.Import)
                        else []
                    )
                    if any(n.startswith("coding_tools_mcp") for n in names):
                        errors.append(f"{relative}: upstream import outside compat")
    for name in ("LICENSE", "NOTICE", "SECURITY.md", "README.md", "README.zh-CN.md", "pyproject.toml"):
        if not (ROOT / name).is_file():
            errors.append(f"missing {name}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"PASS: {count} source files; privacy patterns, syntax, attribution and compat boundary checked.")
    print("This is not a complete secret scan or legal/IP audit; run Gitleaks before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
