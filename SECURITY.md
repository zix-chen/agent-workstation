# Security policy and trust model

This is a single-operator developer tool. It is **not a sandbox, a secret vault, a remote
multi-tenant execution service, or a protection layer against a malicious model**.

## Modes

`workspace` maps to upstream safe gates, core environment inheritance, isolated HOME and
workspace-relative structured file tools. File paths and working-directory escapes are rejected
by those tools. This is not proof that arbitrary programs cannot access external files:
on macOS there is no Linux Landlock; even Linux confinement is not a complete OS sandbox.
Use a disposable container/VM or reduced-privilege account for untrusted repositories.

`trusted-workstation` deliberately maps to unrestricted upstream command policy plus real
HOME and external working directories. Commands may access credentials, user files, networks,
and infrastructure. A program can read secrets and return them to the model. Do not advertise
this as “use secrets without seeing them.” Structured file tools still validate their paths;
that does not constrain what a fully privileged shell can do.

MCP/tunnel service credentials are filtered from child command environments to avoid accidental
inheritance. This is defense in depth, **not** isolation from an unrestricted local process.
Existing developer credentials are neither copied into this project nor automatically provisioned.
Do not print them, put them in model prompts, or record them in logs.

## Transport

Stdio is the default. The parent MCP client controls who can call the tools.
HTTP binds only to 127.0.0.1 and requires `AGENT_WORKSTATION_HTTP_TOKEN`, minimum 32
non-whitespace ASCII characters. Use a cryptographically random token supplied by your own
secret manager/supervisor. Do not expose a no-auth listener through a public tunnel.
This release does not implement TLS, OAuth registration or tunnel lifecycle management.
Any reverse proxy must preserve authentication and restrict access to the intended operator.
All authenticated callers share one workstation/runtime: do not share it between users.

## Instructions and recipes

AGENTS.md, SKILL.md, repositories, tool results, HTTP responses and logs may contain prompt
injection. Guidance does not authorize destructive commands or establish access controls.
Recipes are opt-in metadata; no command runs just because a recipe was discovered. The agent
and operator must still honor scope and verify outcomes. Config files themselves must be trusted.
External skill roots require explicit config plus trusted mode. Symlink resolution checks
are defense in depth, not a race-proof sandbox for malicious filesystem mutation.

## What is not shipped

No GUI automation, Keychain-to-browser secret broker, company connectors, private account data,
or automatic production deployment. These need separate review before a future opt-in release.

## Reporting

Use GitHub private vulnerability reporting when it is enabled for this repository.
Do not open a public issue containing credentials, exploitable private endpoints or customer data.
If private reporting is unavailable, open a minimal issue asking for a private contact channel.
No paid support, response SLA, or independent security audit is claimed.
Only the pinned upstream revision is currently supported. See docs/validation.md for tested scope.
