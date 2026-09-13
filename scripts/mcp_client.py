"""Small synchronous MCP test/demo driver with bounded waits; no model involved."""

import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading


class MCPClient:
    def __init__(self, workspace: Path, *, mode="workspace", config=None, isolated_home=False):
        self.inbox = queue.Queue()
        self.counter = 0
        self.stderr = tempfile.TemporaryFile(mode="w+t")
        self.home = tempfile.TemporaryDirectory(prefix="workstation-demo-home-") if isolated_home else None
        argv = [sys.executable, "-m", "agent_workstation", "--workspace", str(workspace), "--mode", mode]
        if config:
            argv += ["--config", str(config)]
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "TMPDIR", "LANG", "SYSTEMROOT")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if isolated_home:
            env["HOME"] = self.home.name
        self.process = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True, env=env
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.process.stdout:
                self.inbox.put(json.loads(line))
        except Exception as exc:
            self.inbox.put(exc)
        finally:
            self.inbox.put(None)

    def request(self, method, params=None):
        self.counter += 1
        request = {"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params or {}}
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        response = self.inbox.get(timeout=30)
        if response is None or isinstance(response, Exception):
            raise RuntimeError("MCP subprocess closed or returned invalid output.")
        if response.get("id") != self.counter or "error" in response:
            raise RuntimeError("Unexpected MCP response: " + repr(response))
        return response["result"]

    def initialize(self):
        return self.request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "workstation-validation", "version": "1"},
            },
        )

    def tool(self, name, arguments=None):
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self):
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        self.process.stdout.close()
        self.stderr.close()
        if self.home is not None:
            self.home.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
