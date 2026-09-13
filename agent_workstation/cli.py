"""An explicit launch surface: no inherited permission-mode shortcuts."""

import argparse
import json
import os
from pathlib import Path
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Connect an MCP client to a developer workstation.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=["workspace", "trusted-workstation"], default="workspace")
    parser.add_argument("--config", type=Path, help="Explicit local TOML recipe/skill-root configuration.")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--stdio", action="store_true", help="Compatibility alias for --transport stdio.")
    parser.add_argument("--port", type=int, default=8765, help="HTTP binds only to 127.0.0.1.")
    parser.add_argument(
        "--doctor", action="store_true", help="Print runtime capabilities without executing commands."
    )
    return parser


def validate_launch(args, environ) -> str | None:
    if args.stdio and args.transport == "http":
        raise ValueError("--stdio conflicts with --transport http.")
    if not 1 <= args.port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    if args.transport == "http":
        token = environ.get("AGENT_WORKSTATION_HTTP_TOKEN", "")
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError(
                "HTTP requires AGENT_WORKSTATION_HTTP_TOKEN (32+ non-whitespace ASCII characters)."
            )
        return token
    return None


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        token = validate_launch(args, os.environ)
        workspace = args.workspace.expanduser().resolve(strict=True)
        if not workspace.is_dir():
            raise ValueError("Workspace must be an existing directory.")
        from .compat.coding_tools import create_runtime, serve

        runtime = create_runtime(
            workspace, mode=args.mode, config=args.config, auth_token=token, transport=args.transport
        )
        if args.doctor:
            try:
                print(json.dumps(runtime.server_info(), indent=2, ensure_ascii=False))
            finally:
                runtime.close()
            return 0
        print(
            "Workspace mode is not a complete OS sandbox; use a disposable VM/container for untrusted code.",
            file=sys.stderr,
        )
        if args.mode == "trusted-workstation":
            print(
                "TRUSTED WORKSTATION: commands use your real HOME and developer identity. "
                "They can read/write outside the workspace and access credentials. "
                "Use only with a trusted agent and trusted code.",
                file=sys.stderr,
            )
        return serve(runtime, transport=args.transport, port=args.port)
    except (ValueError, OSError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
