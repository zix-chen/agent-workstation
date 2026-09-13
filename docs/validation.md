# Validation record

This file records only measurements from this release, not historical private-runtime results.
The repository's CI workflow is the authoritative record for its commit and OS/Python matrix.
Local validation: 2026-09-13, macOS arm64, CPython 3.11.16, isolated project virtual environment.

- 57 automated tests passed, including real stdio handshake/tool calls and loopback HTTP bearer auth.
- Ruff passed. Source hygiene/compat-boundary checks passed.
- Deterministic MCP demo passed: actual local health 503 before configuration, 200 after a corrected process.
- Python wheel and source distribution built successfully.
- A non-editable wheel install into a second clean virtual environment passed --doctor from outside the source tree.
- Local byte benchmark: full visible output 100,020 bytes; preview 8,192 bytes.
  Serialized MCP result in this run: 200,998 bytes full vs 17,840 bytes preview.
  Serialization metadata can vary between runs. This is not a token/cost or model-quality benchmark.
- See GitHub Actions for Linux/macOS and Python 3.11/3.12 results on each published commit.

A separate release gate scans the new Git history using checksummed Gitleaks 8.30.1.
The public repository does not contain the source private repository's commit history.

## Reproduce

```bash
python -m unittest discover -s tests -v
ruff check .
python scripts/demo.py
python scripts/benchmark_output.py
python scripts/check_release.py
python -m build
```

## Not claimed

No independent security audit; no proof of complete OS sandboxing; no cross-client UI certification;
no browser/desktop/secret-filling tests; no production database/cloud/deployment checks;
no measured LLM task success, subscription quota reduction or token/cost savings.
The fake-backend demo is deterministic, uses loopback networking and a temporary workspace,
and cannot establish real enterprise service behavior.
