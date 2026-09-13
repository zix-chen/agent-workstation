import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent_workstation.cli import build_parser, validate_launch
from agent_workstation.compat import coding_tools as compat
from agent_workstation.output_policy import TOOL_DEFAULTS


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.runtime = compat.WorkstationRuntime(self.root, mode="trusted-workstation")

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def call(self, name, args=None):
        result = self.runtime.call_tool(name, args or {})
        return result["structuredContent"]

    def finished(self, args):
        result = self.call("exec_command", args)
        for _ in range(20):
            if result.get("status") != "running":
                return result
            result = self.call(
                "write_stdin",
                {
                    "command_id": result["command_id"],
                    "yield_time_ms": 1000,
                    "verbosity": args.get("verbosity", "preview"),
                },
            )
        self.fail("Command did not finish")

    def test_real_home_explicit_mode(self):
        self.assertEqual(self.runtime.command_home_dir(), Path.home())
        self.assertTrue(self.runtime.server_info()["agent_workstation"]["host_identity"])

    def test_workspace_mode_isolated_home(self):
        safe = compat.WorkstationRuntime(self.root)
        try:
            self.assertNotEqual(safe.command_home_dir(), Path.home())
            self.assertEqual(safe.permission_mode, "safe")
            self.assertFalse(safe.server_info()["agent_workstation"]["complete_os_sandbox"])
        finally:
            safe.close()

    def test_default_mode_not_changed_by_inherited_environment(self):
        with patch.dict(
            os.environ,
            {
                "CODING_TOOLS_MCP_PERMISSION_MODE": "dangerous",
                "CODING_TOOLS_MCP_DANGEROUSLY_FAKE_READONLY_ANNOTATIONS": "1",
            },
        ):
            safe = compat.WorkstationRuntime(self.root)
            try:
                self.assertEqual(safe.permission_mode, "safe")
                self.assertFalse(safe.fake_readonly_annotations)
            finally:
                safe.close()

    def test_control_plane_credentials_not_inherited_or_reintroduced(self):
        values = {
            "CONTROL_PLANE_API_KEY": "test-placeholder",
            "AGENT_WORKSTATION_HTTP_TOKEN": "test-placeholder",
            "CODING_TOOLS_MCP_AUTH_TOKEN": "test-placeholder",
        }
        with patch.dict(os.environ, values):
            env = self.runtime._command_env(values)
        self.assertFalse(set(values) & set(env))

    def test_schema_defaults_match_runtime(self):
        tools = {t["name"]: t for t in self.runtime.list_tools()["tools"]}
        for name, defaults in TOOL_DEFAULTS.items():
            for key, value in defaults.items():
                self.assertEqual(tools[name]["inputSchema"]["properties"][key]["default"], value)
        self.assertTrue(tools["workspace_guide"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["exec_command"]["annotations"]["readOnlyHint"])

    def test_hook_installation_idempotent(self):
        schema = compat.server.input_schemas
        compat.install_hooks()
        self.assertIs(schema, compat.server.input_schemas)

    def test_mismatched_upstream_refused(self):
        distribution = Mock()
        distribution.read_text.return_value = json.dumps({"vcs_info": {"commit_id": "unsupported"}})
        with patch.object(compat.metadata, "distribution", return_value=distribution):
            with self.assertRaises(RuntimeError):
                compat.verify_upstream()

    def test_guide_and_initialization_instructions(self):
        (self.root / "AGENTS.md").write_text("rules")
        guide = self.call("workspace_guide")
        self.assertEqual(guide["rules"][0]["path"], "AGENTS.md")
        self.assertIn("workspace_guide", self.runtime.initialize_result()["instructions"])
        self.assertIn("workspace_guide", self.runtime.discover_payload()["instructions"])

    def test_guide_escape_rejected(self):
        self.assertFalse(self.call("workspace_guide", {"path": ".."})["ok"])

    def test_external_cwd_trusted(self):
        with tempfile.TemporaryDirectory(prefix="workstation space ") as outside:
            result = self.finished({"cmd": "pwd", "workdir": outside, "verbosity": "full"})
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["stdout"].strip(), str(Path(outside).resolve()))

    def test_conflicting_cwd_rejected(self):
        result = self.call("exec_command", {"cmd": "pwd", "cwd": ".", "workdir": "/tmp"})
        self.assertFalse(result["ok"])

    def test_invalid_cwd_rejected(self):
        result = self.call("exec_command", {"cmd": "pwd", "workdir": "absent"})
        self.assertFalse(result["ok"])

    def test_structured_read_escape_blocked_even_when_trusted(self):
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / "not-a-secret.txt"
            path.write_text("synthetic")
            result = self.call("read_file", {"path": str(path)})
            self.assertFalse(result["ok"])

    def test_workspace_cwd_escape_blocked(self):
        safe = compat.WorkstationRuntime(self.root)
        try:
            result = safe.call_tool("exec_command", {"cmd": "pwd", "workdir": "/tmp"})
            self.assertTrue(result["isError"])
        finally:
            safe.close()

    def test_preview_preserves_error_and_continuation(self):
        code = "import sys;print('OUT_BEGIN'+('x'*40000)+'OUT_END');print('IMPORTANT_ERROR',file=sys.stderr);sys.exit(7)"
        result = self.finished({"cmd": shlex.quote(sys.executable) + " -c " + shlex.quote(code)})
        self.assertEqual(result["exit_code"], 7)
        self.assertLessEqual(len(result["preview"].encode()), 8192)
        self.assertIn("IMPORTANT_ERROR", result["preview"])
        self.assertTrue(result["preview_truncated"])
        self.assertIn("next_actions", result)
        recovered = self.call(
            "read_output", {"output_ref": result["output_refs"]["stdout"], "offset": 15000, "limit": 20}
        )
        self.assertEqual(recovered["content"], "x" * 20)

    def test_explicit_full_and_summary(self):
        full = self.finished({"cmd": "printf exact", "verbosity": "full"})
        self.assertEqual(full["stdout"], "exact")
        self.assertNotIn("preview", full)
        summary = self.finished({"cmd": "printf small", "verbosity": "summary"})
        self.assertNotIn("preview", summary)

    def test_read_file_budget_and_override(self):
        (self.root / "large.txt").write_text(("x" * 100 + "\n") * 800)
        limited = self.call("read_file", {"path": "large.txt"})
        self.assertTrue(limited["truncated"])
        self.assertIsNotNone(limited["next_start_line"])
        full = self.call("read_file", {"path": "large.txt", "max_bytes": 100000})
        self.assertFalse(full["truncated"])

    def test_upstream_line_limit_continues_without_claiming_full_output(self):
        (self.root / "many-lines.txt").write_text("line\n" * 8001)
        lines = []
        start = 1
        while True:
            page = self.call(
                "read_file", {"path": "many-lines.txt", "start_line": start, "max_bytes": 100000}
            )
            lines.extend(page["content"].splitlines())
            if page["next_start_line"] is None:
                break
            self.assertGreater(page["next_start_line"], start)
            start = page["next_start_line"]
        self.assertEqual(len(lines), 8001)

    def test_poll_and_kill(self):
        result = self.call("exec_command", {"cmd": "sleep 10", "yield_time_ms": 0})
        self.assertEqual(result["status"], "running")
        killed = self.call("kill_command", {"command_id": result["command_id"]})
        self.assertNotEqual(killed["status"], "running")
        self.assertIn("preview", killed)

    def test_deadline_kills_process(self):
        result = self.finished({"cmd": "sleep 10", "timeout_ms": 100, "yield_time_ms": 1000})
        self.assertTrue(result["timed_out"])


class LaunchTests(unittest.TestCase):
    def test_default_is_stdio_workspace(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.transport, "stdio")
        self.assertEqual(args.mode, "workspace")
        self.assertIsNone(validate_launch(args, {}))

    def test_http_requires_strong_token(self):
        args = build_parser().parse_args(["--transport", "http"])
        for token in ("", "short", "x" * 31, "x" * 31 + " ", "汉" * 32):
            with self.assertRaises(ValueError):
                validate_launch(args, {"AGENT_WORKSTATION_HTTP_TOKEN": token})
        self.assertEqual(validate_launch(args, {"AGENT_WORKSTATION_HTTP_TOKEN": "x" * 32}), "x" * 32)

    def test_conflicting_transport_rejected(self):
        args = build_parser().parse_args(["--stdio", "--transport", "http"])
        with self.assertRaises(ValueError):
            validate_launch(args, {})

    def test_invalid_port_rejected(self):
        for port in ("0", "65536"):
            with self.assertRaises(ValueError):
                validate_launch(build_parser().parse_args(["--port", port]), {})
