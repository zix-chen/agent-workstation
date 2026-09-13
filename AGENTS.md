# Agent Workstation contribution rules

Keep upstream-specific imports and hooks inside `agent_workstation/compat/`.
Do not copy private configuration, credentials, production URLs or personal paths.
Workspace mode is a policy boundary, not a complete operating-system sandbox.
Skills and recipes are guidance, not executable authorization or access controls.
Keep tool annotations truthful. Do not start external services during unit tests.
Use temporary workspaces for integration tests. Run `python -m unittest discover -s tests -v`,
`python scripts/check_release.py`, and `python scripts/demo.py` before release.
Never change the developer's other repositories or installed MCP runtime.
