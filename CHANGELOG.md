# Changelog

## 0.1.1

- Avoid reverse DNS during fixed-loopback HTTP listener and demo backend startup.
- Preserve and cleanly report socket bind failures; add readiness diagnostics and regressions.
- Follow-up to hosted macOS HTTP-test startup timeouts in 0.1.0; published tags are not rewritten.

## 0.1.0

Initial extracted, company-independent release:
- Explicit workspace and trusted-workstation modes; truthful security boundaries.
- Pinned upstream compatibility layer using runtime subclassing.
- On-demand target rules, Skill metadata and opt-in TOML recipes.
- Multi-repo discovery with bounded traversal and symlink checks.
- Default bounded stdout/stderr head-tail previews and output continuation.
- Stdio plus authenticated loopback HTTP transport.
- Temporary-backend MCP demo, output-byte benchmark, tests and release scanning.

Not included: GUI/browser automation, secret filling, company integrations or automatic tunnels.
