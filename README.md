# Agent Workstation

[简体中文](README.zh-CN.md) · [Security](SECURITY.md) · [Architecture](docs/architecture.md) · [Client setup](docs/clients.md)

**Bring an MCP client into your developer workflow. Prefer APIs and CLIs over clicking screens.**

A small, opinionated adapter built on [Coding Tools MCP](https://github.com/xyTom/coding-tools-mcp).
It adds explicit workstation trust, multi-repository context discovery, a lazy rules/skills/recipes
entry point, and bounded command previews. It does **not** implement a new model, agent loop,
SQL engine, browser driver, or secret vault.

## What is actually new?

| Inherited from Coding Tools MCP | Added here |
| --- | --- |
| Files, patches, search, Git, process lifecycle, MCP transport | Explicit `workspace` / `trusted-workstation` launch modes |
| Output retention, references, pagination | 8 KiB default head/tail preview with stderr budgeting |
| Root instruction loading | Bounded multi-repo discovery and target-path rule lookup |
| Generic command execution | `workspace_guide`: on-demand skill metadata and opt-in recipe routing |

The adapter pins upstream commit `bedb632e1afd2e9ec9b268a50fe0b04695c22c64`.
Its package metadata says 0.3.0; this is **not** a claimed upstream 0.5 release.
Upstream-private imports/hooks are isolated in `agent_workstation/compat/coding_tools.py`.
A mismatched upstream build fails at startup rather than silently running an untested adapter.

## Install and try

Requirements: Python 3.11+, Git; macOS or Linux. Your own MCP client supplies the model.
No Codex installation or model API key is required by this server.
The package is installed from GitHub; it is not published to PyPI in this release.

```bash
# An isolated environment; does not alter another MCP installation.
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "git+https://github.com/zix-chen/agent-workstation.git@v0.1.1"
agent-workstation --workspace /path/to/repository --doctor
agent-workstation --workspace /path/to/repository --stdio
```

Generic stdio MCP configuration (use an absolute executable path):

```json
{
  "mcpServers": {
    "agent-workstation": {
      "command": "/absolute/path/to/.venv/bin/agent-workstation",
      "args": ["--workspace", "/absolute/path/to/work", "--mode", "workspace", "--stdio"]
    }
  }
}
```

Ask the client: **“Call workspace_guide for this repository, read the relevant rules/skill,
then review this change. Report evidence and what you did not verify.”**

### Explicit workstation access

```bash
agent-workstation --workspace "$HOME/work" --mode trusted-workstation --stdio
```

**This gives commands your real HOME, local developer configuration, network access and
access outside the workspace. Commands can read secrets, modify files and operate services
with your user privileges. It is NOT secret isolation or protection from prompt injection.**
Use trusted code and a trusted agent, or a disposable account/VM with reduced credentials.

Default `workspace` mode retains upstream safe command gates, isolated HOME and structured
path validation. **It is not a complete OS sandbox**, especially on macOS. Repository rules
are workflow guidance, not permission enforcement. See [SECURITY.md](SECURITY.md).

### Rules, skills and recipes

```text
work/
  AGENTS.md
  repo-a/
    AGENTS.md
    .agents/skills/review/SKILL.md
  repo-b/
    src/AGENTS.md
```

`workspace_guide(path="repo-a")` returns applicable rule paths and skill name/description/hash.
It does **not** inject every skill's full body. The agent selects and fully reads the smallest
relevant skill. Same-name skills retain their source paths. Startup avoids recursive workspace
walks, skips generated/worktree directories and uses Git metadata at actual repository roots.
Target-path lookup can still find rules under a skipped tree when explicitly selected.

Recipes are explicitly loaded TOML, never auto-executed:

```bash
agent-workstation --workspace "$PWD/examples/demo-service"   --config "$PWD/examples/demo-service/workstation.toml" --stdio
```

See the [runnable example](examples/demo-service) and [configuration contract](docs/configuration.md).
External skill roots require explicit config **and** trusted-workstation mode.
`kubectl`, `mysql`, `redis-cli`, cloud CLIs and their credentials are user-managed, not bundled integrations.

## Reproduce the demo and benchmark

```bash
git clone https://github.com/zix-chen/agent-workstation.git
cd agent-workstation
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python scripts/demo.py
python scripts/benchmark_output.py
python scripts/check_release.py
```

The demo uses a **temporary copy** of a fake backend, calls real MCP tools, checks a local HTTP
health endpoint, diagnoses a missing demo configuration, and verifies the corrected process.
It uses no private infrastructure or model credentials. It is a deterministic integration demo,
**not** a claim of autonomous model task success.

The benchmark reports output bytes and serialized response bytes. It does not measure model
tokens, subscription quotas, speedups, or dollars saved. Explicit output arguments override
defaults. Follow `read_output` references when previews truncate; retained output can expire
or lose its middle segment. Save an authorized log file for durable/full logs.

## HTTP and remote clients

An optional loopback HTTP listener requires a bearer token even on localhost:

```bash
# Supply a random 32+ character secret through your process supervisor/secret manager.
# Never put the real value in this repo, the README, or a model prompt.
agent-workstation --workspace /path/to/work --transport http --port 8765
# Reads AGENT_WORKSTATION_HTTP_TOKEN; startup refuses an absent/short token.
```

Remote access requires your own authenticated HTTPS transport and a compatible client.
OAuth registration and tunnels are **not** implemented by this V1. A generic stdio configuration
is not a ChatGPT web connection. See [client setup and verification boundaries](docs/clients.md).
No public listener or tunnel is installed automatically.

A real run transcript is available in [docs/demo-output.txt](docs/demo-output.txt).

## Scope and status

V0.1 is a small developer-tool release, not an enterprise platform. Computer/browser automation,
GUI secret filling, company-specific integrations, production deployment automation and a plugin
marketplace are intentionally excluded. See [validation](docs/validation.md) for actual test results.

[Design decisions](docs/architecture.md) cover the adapter architecture, trust model, and verification boundaries.

## License and attribution

Apache-2.0. Built on Coding Tools MCP, Copyright 2026 Coding Tools MCP Contributors.
See [NOTICE](NOTICE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No private
repository history, employee accounts, business code or production configuration is distributed.

The pinned upstream read_file also caps a page at 2,000 lines. Raising max_bytes does not
remove that cap; use next_start_line to read the remaining pages.
