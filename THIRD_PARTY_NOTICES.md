# Third-party notices

## Coding Tools MCP

Source: https://github.com/xyTom/coding-tools-mcp
Revision: bedb632e1afd2e9ec9b268a50fe0b04695c22c64
Copyright 2026 Coding Tools MCP Contributors. Apache License 2.0.
The upstream NOTICE is reproduced in this repository's NOTICE. Its license is retained as LICENSE.

This project adds adapter behavior around the upstream runtime. It does not claim authorship of
upstream file editing, Git tooling, process management, protocol implementation or permission engine.
Upstream interface adaptations are concentrated in agent_workstation/compat/coding_tools.py.

## PyYAML

Source: https://github.com/yaml/pyyaml
License: MIT. Installed as an external dependency; not vendored.
Used only with safe_load to read bounded Skill front matter.

## Other dependencies and developer tools

Coding Tools MCP's PyJWT dependency, setuptools, wheel, build and Ruff retain their respective
licenses in their distributed packages. Gitleaks is a separately downloaded development scanner;
its binary is not included in this repository or release artifacts. No Peekaboo or document CLI
binary is redistributed.
