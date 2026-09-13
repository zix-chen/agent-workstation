"""Deterministic MCP/API workflow over a disposable backend; no LLM or private services."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading

from mcp_client import MCPClient


@contextmanager
def backend(root, ready=False):
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "SYSTEMROOT")}
    env["HOME"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if ready:
        env["DEMO_UPSTREAM"] = "mock://ready"
    process = subprocess.Popen(
        [sys.executable, str(root / "service.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
    )
    inbox = queue.Queue()
    threading.Thread(target=lambda: inbox.put(process.stdout.readline()), daemon=True).start()
    try:
        line = inbox.get(timeout=10)
        port = json.loads(line)["port"]
        yield port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()


def health(client, port):
    code = (
        "import json,urllib.request,urllib.error; "
        "url=" + repr(f"http://127.0.0.1:{port}/health") + ";\n"
        "try:\n r=urllib.request.urlopen(url,timeout=5)\n"
        "except urllib.error.HTTPError as e:\n r=e\n"
        "print(json.dumps({'http_status':r.code,'body':json.loads(r.read())}))"
    )
    result = client.tool(
        "exec_command",
        {
            "cmd": shlex.quote(sys.executable) + " -c " + shlex.quote(code),
            "verbosity": "full",
            "yield_time_ms": 1000,
        },
    )["structuredContent"]
    while result["status"] == "running":
        result = client.tool(
            "write_stdin", {"command_id": result["command_id"], "yield_time_ms": 1000, "verbosity": "full"}
        )["structuredContent"]
    if result.get("exit_code") != 0:
        raise RuntimeError("Demo health command failed.")
    return json.loads(result["stdout"])


def main():
    source = Path(__file__).resolve().parents[1] / "examples" / "demo-service"
    with tempfile.TemporaryDirectory(prefix="agent-workstation-demo-") as temporary:
        root = Path(temporary).resolve() / "service"
        shutil.copytree(source, root)
        with MCPClient(
            root, mode="trusted-workstation", config=root / "workstation.toml", isolated_home=True
        ) as client:
            client.initialize()
            guide = client.tool("workspace_guide")["structuredContent"]
            assert guide["skills"] and guide["recipes"]
            print("1. MCP discovery: target rules, backend-incident Skill and recipe found.")
            for file in (
                "AGENTS.md",
                ".agents/skills/backend-incident/SKILL.md",
                "settings.json",
                "service.log.txt",
            ):
                assert not client.tool("read_file", {"path": file}).get("isError")
            print("2. Read full instructions, Skill, settings and evidence log through MCP.")
            with backend(root) as port:
                before = health(client, port)
            assert before["http_status"] == 503
            print("3. Actual HTTP before:", json.dumps(before))
            print("4. Minimal correction: set DEMO_UPSTREAM=mock://ready in a fresh disposable process.")
            with backend(root, ready=True) as port:
                after = health(client, port)
            assert after["http_status"] == 200 and after["body"]["status"] == "ok"
            print("5. Actual HTTP after:", json.dumps(after))
    print("PASS: temporary processes stopped; no private systems, external model, UI or deployment involved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
