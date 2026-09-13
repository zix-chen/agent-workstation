# Demo service rules

This is a fake service; only operate on a temporary copy during tests and demos.
Use local HTTP health, config and logs to establish behavior. Never access external infrastructure.
Read `.agents/skills/backend-incident/SKILL.md` for an incident request.
Do not modify a running process based solely on a log message; check its configuration and health.
