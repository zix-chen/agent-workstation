import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mcp_client import MCPClient  # noqa: E402


class ProtocolTests(unittest.TestCase):
    def test_real_stdio_handshake_catalog_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / "AGENTS.md").write_text("Test rules")
            with MCPClient(root) as client:
                initialized = client.initialize()
                self.assertEqual(initialized["serverInfo"]["name"], "agent-workstation")
                names = {x["name"] for x in client.request("tools/list")["tools"]}
                self.assertIn("workspace_guide", names)
                self.assertIn("exec_command", names)
                self.assertNotIn("computer_call", names)
                self.assertNotIn("secret_input", names)
                data = client.tool("read_file", {"path": "AGENTS.md"})["structuredContent"]
                self.assertIn("Test rules", data["content"])
                self.assertTrue(client.tool("workspace_guide")["structuredContent"]["ok"])

    def test_isolated_home_stdio_launch(self):
        with tempfile.TemporaryDirectory() as d:
            with MCPClient(Path(d).resolve(), mode="trusted-workstation", isolated_home=True) as client:
                self.assertEqual(client.initialize()["serverInfo"]["name"], "agent-workstation")

    def test_unsafe_workspace_reports_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, HOME=d)
            result = subprocess.run(
                [sys.executable, "-m", "agent_workstation", "--workspace", d, "--doctor"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unsafe workspace", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_loopback_server_never_resolves_dns(self):
        from agent_workstation.compat.coding_tools import LoopbackHTTPServer, server

        runtime = Mock()
        with patch("socket.getfqdn", side_effect=AssertionError("Reverse DNS must not run")):
            httpd = LoopbackHTTPServer(("127.0.0.1", 0), server.MCPHandler, runtime)
            try:
                self.assertEqual(httpd.server_name, "127.0.0.1")
                self.assertGreater(httpd.server_port, 0)
            finally:
                httpd.server_close()
        runtime.close.assert_called_once()

    def test_nonloopback_server_rejected_before_bind(self):
        from agent_workstation.compat.coding_tools import LoopbackHTTPServer, server

        with self.assertRaises(ValueError):
            LoopbackHTTPServer(("0.0.0.0", 0), server.MCPHandler, Mock())

    def test_failed_bind_preserves_os_error_and_closes_runtime(self):
        from agent_workstation.compat.coding_tools import LoopbackHTTPServer, server

        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            runtime = Mock()
            with self.assertRaises(OSError):
                LoopbackHTTPServer(occupied.getsockname(), server.MCPHandler, runtime)
            runtime.close.assert_called_once()

    def test_demo_server_never_resolves_dns(self):
        from importlib.util import module_from_spec, spec_from_file_location

        path = Path(__file__).resolve().parents[1] / "examples/demo-service/service.py"
        spec = spec_from_file_location("workstation_demo_fixture", path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch("socket.getfqdn", side_effect=AssertionError("Demo reverse DNS must not run")):
            httpd = module.DemoHTTPServer(("127.0.0.1", 0), module.Handler)
            try:
                self.assertEqual(httpd.server_name, "127.0.0.1")
            finally:
                httpd.server_close()

    def test_http_authentication(self):
        with tempfile.TemporaryDirectory() as d, socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
            reserved.close()
            token = secrets.token_urlsafe(32)
            env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "SYSTEMROOT")}
            env["AGENT_WORKSTATION_HTTP_TOKEN"] = token
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            with tempfile.TemporaryFile(mode="w+t") as log:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "agent_workstation",
                        "--workspace",
                        d,
                        "--transport",
                        "http",
                        "--port",
                        str(port),
                    ],
                    stdout=log,
                    stderr=log,
                    env=env,
                )
                url = f"http://127.0.0.1:{port}/mcp"
                data = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "http-test", "version": "1"},
                        },
                    }
                ).encode()
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                try:
                    for _ in range(100):
                        try:
                            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                                break
                        except OSError:
                            if process.poll() is not None:
                                self.fail("HTTP process stopped during startup")
                            time.sleep(0.05)
                    else:
                        log.seek(0)
                        diagnostic = log.read().replace(token, "<redacted>")
                        self.fail("HTTP listener did not become ready. Startup output: " + diagnostic)
                    for bearer in (None, "wrong"):
                        headers = {
                            "Content-Type": "application/json",
                            "Accept": "application/json, text/event-stream",
                        }
                        if bearer:
                            headers["Authorization"] = "Bearer " + bearer
                        with self.assertRaises(urllib.error.HTTPError) as error:
                            opener.open(urllib.request.Request(url, data=data, headers=headers), timeout=5)
                        self.assertIn(error.exception.code, (401, 403))
                        error.exception.close()
                    headers["Authorization"] = "Bearer " + token
                    with opener.open(
                        urllib.request.Request(url, data=data, headers=headers), timeout=5
                    ) as response:
                        self.assertEqual(response.status, 200)
                        result = json.load(response)
                        self.assertEqual(result["result"]["serverInfo"]["name"], "agent-workstation")
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                log.seek(0)
                self.assertNotIn(token, log.read())
