"""The only upstream-dependent module. Pinned hooks; subclassed runtime behavior.

Coding Tools MCP is Apache-2.0; see NOTICE and THIRD_PARTY_NOTICES.md.
The upstream schema/context hooks are process-global. Use one adapter version per process.
"""

from copy import deepcopy
import json
from importlib import metadata
import os
from pathlib import Path
import shlex

from coding_tools_mcp import project_context, server

from .. import __version__
from ..context import discover
from ..integrations import Catalog, WORKFLOW
from ..output_policy import TOOL_DEFAULTS, command_preview

UPSTREAM_COMMIT = "bedb632e1afd2e9ec9b268a50fe0b04695c22c64"
_INSTALLED = False


def verify_upstream() -> None:
    distribution = metadata.distribution("coding-tools-mcp")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    actual = direct.get("vcs_info", {}).get("commit_id")
    if actual != UPSTREAM_COMMIT:
        raise RuntimeError(
            "Unsupported Coding Tools MCP build. Reinstall this project's pinned VCS dependency."
        )
    for name in ("_format_command_output", "_command_env", "command_home_dir", "exec_command"):
        if not hasattr(server.Runtime, name):
            raise RuntimeError("Unsupported upstream runtime interface: " + name)


def install_hooks() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    verify_upstream()
    original_schemas = server.input_schemas

    def schemas():
        result = deepcopy(original_schemas())
        for name, defaults in TOOL_DEFAULTS.items():
            for key, value in defaults.items():
                result[name]["properties"][key]["default"] = value
        result["workspace_guide"] = server.object_schema(
            {
                "path": {
                    "type": "string",
                    "default": ".",
                    "description": "Existing workspace-relative target repository, directory or file.",
                }
            }
        )
        return result

    server.input_schemas = schemas
    server.TOOL_REGISTRY["workspace_guide"] = server.ToolSpec(
        title="Find target rules, skills and recipes",
        description="Find applicable repository instructions and skill metadata for a target path. "
        "Read the selected full files before acting; no execution or permission grant.",
        read_only=True,
        destructive=False,
        idempotent=True,
        content_builder=lambda p: [{"type": "text", "text": json.dumps(p, ensure_ascii=False)}],
    )
    project_context._discover_context_files = lambda root, warnings: discover(
        root, project_context._git_context_files, warnings
    )
    _INSTALLED = True


class WorkstationRuntime(server.Runtime):
    def __init__(
        self,
        workspace: Path,
        *,
        mode: str = "workspace",
        config: Path | None = None,
        auth_token: str | None = None,
        transport: str = "stdio",
    ):
        if mode not in ("workspace", "trusted-workstation"):
            raise ValueError("Unknown mode.")
        install_hooks()
        self.workstation_mode = mode
        self.host_home = Path.home()
        self.catalog = Catalog(workspace, config, trusted=mode == "trusted-workstation")
        # No telemetry by default, including inherited upstream telemetry.
        os.environ["CODING_TOOLS_MCP_TELEMETRY"] = "off"
        super().__init__(
            workspace,
            permission_mode="dangerous" if mode == "trusted-workstation" else "safe",
            shell_env_policy=server.ShellEnvPolicy(
                inherit="all" if mode == "trusted-workstation" else "core"
            ),
            fake_readonly_annotations=False,
            auth_token=auth_token,
            transport=transport,
        )

    def command_home_dir(self):
        if self.workstation_mode == "trusted-workstation":
            return self.host_home
        return super().command_home_dir()

    def _command_env(self, extra):
        env = super()._command_env(extra)
        # Avoid accidental propagation of MCP/tunnel service credentials. This is
        # NOT a security boundary against arbitrary commands in trusted mode.
        return {
            key: value
            for key, value in env.items()
            if key not in {"CONTROL_PLANE_API_KEY", "AGENT_WORKSTATION_HTTP_TOKEN"}
            and not key.startswith(("CODING_TOOLS_MCP_AUTH_", "CODING_TOOLS_MCP_OAUTH_"))
        }

    def call_tool(self, name, arguments, *, context=None):
        return super().call_tool(name, {**TOOL_DEFAULTS.get(name, {}), **(arguments or {})}, context=context)

    def exec_command(self, args):
        args = dict(args)
        if self.workstation_mode == "trusted-workstation":
            if "workdir" in args and "cwd" in args and args["workdir"] != args["cwd"]:
                raise server.ToolFailure("INVALID_ARGUMENT", "workdir and cwd differ.", category="validation")
            path = Path(args.get("workdir", args.get("cwd", "."))).expanduser()
            resolved = (path if path.is_absolute() else self.workspace.root / path).resolve()
            if not resolved.is_dir():
                raise server.ToolFailure(
                    "NOT_A_DIRECTORY", "workdir is not a directory.", category="validation"
                )
            args.pop("cwd", None)
            try:
                args["workdir"] = str(resolved.relative_to(self.workspace.root))
            except ValueError:
                args["workdir"] = "."
                args["cmd"] = "cd -- " + shlex.quote(str(resolved)) + " && {\n" + args["cmd"] + "\n}"
        return super().exec_command(args)

    def _format_command_output(self, command, payload, args):
        result = super()._format_command_output(command, payload, args)
        if args.get("verbosity") != "preview":
            return result
        preview, omitted = command_preview(command.retained_stream_segments, int(args["preview_bytes"]))
        result["preview"] = preview
        result["preview_truncated"] = bool(omitted)
        result["truncated"] = bool(result.get("truncated") or omitted)
        if omitted:
            streams = sorted(set(result.get("truncated_output_streams", [])) | set(omitted))
            result["truncated_output_streams"] = streams
            result["next_actions"] = [
                {
                    "tool": "read_output",
                    "arguments": {"output_ref": result["output_refs"][s], "offset": 0, "limit": 4096},
                }
                for s in streams
            ]
            if result.get("status") != "running":
                result["next_action"] = result["next_actions"][0]
        return result

    def workspace_guide(self, args):
        try:
            return self.catalog.guide(args.get("path", "."))
        except (ValueError, OSError, RuntimeError):
            raise server.ToolFailure(
                "INVALID_TARGET", "Target must exist inside the workspace.", category="validation"
            ) from None

    def server_info(self, args=None):
        result = super().server_info(args or {})
        result["agent_workstation"] = {
            "version": __version__,
            "mode": self.workstation_mode,
            "upstream_commit": UPSTREAM_COMMIT,
            "host_identity": self.workstation_mode == "trusted-workstation",
            "complete_os_sandbox": False,
            "telemetry": "off",
        }
        return result

    def initialize_result(self, *args, **kwargs):
        result = super().initialize_result(*args, **kwargs)
        result["instructions"] += "\n\n" + WORKFLOW
        result["serverInfo"] = {**result["serverInfo"], "name": "agent-workstation", "version": __version__}
        return result

    def discover_payload(self):
        result = super().discover_payload()
        result["instructions"] += "\n\n" + WORKFLOW
        return result


def serve(runtime: WorkstationRuntime, *, transport: str, port: int) -> int:
    server.install_sigterm_handler()
    if transport == "stdio":
        return server.serve_stdio(runtime)
    try:
        httpd = server.RuntimeHTTPServer(("127.0.0.1", port), server.MCPHandler, runtime)
        try:
            import sys

            print(f"Agent Workstation: authenticated HTTP on 127.0.0.1:{port}/mcp", file=sys.stderr)
            httpd.serve_forever()
        finally:
            httpd.server_close()
    finally:
        runtime.close()
    return 0


def create_runtime(*args, **kwargs):
    """Normalize expected upstream startup errors without exposing tracebacks to clients."""
    try:
        return WorkstationRuntime(*args, **kwargs)
    except server.ToolFailure as exc:
        raise ValueError(f"{exc.code}: {exc.message}") from None
