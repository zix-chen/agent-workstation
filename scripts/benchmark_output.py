"""Measure bytes, not tokens, quota, task quality, or model latency."""

import json
from pathlib import Path
import shlex
import sys
import tempfile
from mcp_client import MCPClient


def main():
    code = "import sys;print('BEGIN'+('x'*100000)+'END');print('DEMO_ERROR',file=sys.stderr)"
    command = shlex.quote(sys.executable) + " -c " + shlex.quote(code)
    sizes = {}
    with (
        tempfile.TemporaryDirectory() as d,
        MCPClient(Path(d).resolve(), mode="trusted-workstation", isolated_home=True) as client,
    ):
        client.initialize()
        for label, opts in [("full", {"verbosity": "full", "max_output_bytes": 200000}), ("preview", {})]:
            result = client.tool("exec_command", {"cmd": command, "yield_time_ms": 1000, **opts})
            payload = result["structuredContent"]
            while payload["status"] == "running":
                result = client.tool(
                    "write_stdin", {"command_id": payload["command_id"], "yield_time_ms": 1000, **opts}
                )
                payload = result["structuredContent"]
            assert payload["exit_code"] == 0
            sizes[label] = {
                "serialized_result_bytes": len(json.dumps(result, ensure_ascii=False).encode()),
                "visible_output_bytes": len(
                    (payload.get("preview") or payload.get("stdout", "") + payload.get("stderr", "")).encode()
                ),
            }
    print(json.dumps({"metric": "bytes_only", "results": sizes}, indent=2))


if __name__ == "__main__":
    main()
