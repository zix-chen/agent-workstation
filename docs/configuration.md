# Configuration contract

Pass `--config /absolute/path/workstation.toml` explicitly. No config is auto-loaded from an
untrusted repository. Paths are relative to the config's directory, not the shell's cwd.

```toml
skill_roots = [".agents/skills"]

[recipes.backend-incident]
description = "Diagnose a local backend using API, configuration and log evidence"
skill = ".agents/skills/backend-incident/SKILL.md"
```

Only `skill_roots` and `recipes` are accepted. A recipe has exactly `description` and `skill`.
Unknown keys, executable command definitions, missing files and oversized config are rejected.
Config maximum: 64 KiB; skill roots: 16; recipes: 64. A Skill must have bounded UTF-8 YAML front
matter with nonempty string `name` and `description`; folded multiline YAML is supported.
Metadata discovery reads at most 32 KiB per Skill and returns up to 128 skills with truncation warnings.
The model must read the selected SKILL.md in full before following it.

Workspace mode requires configured roots to remain within the workspace. Trusted mode also
allows explicitly named external roots; a recipe must still point within the workspace or one
of those configured roots. Such files are read through the trusted command entry point, not by
weakening structured read_file validation. Auto-discovered symlink roots outside the workspace
are skipped. Two skills with the same name are kept distinct by path.

Recipe metadata is not an execution plan, permission grant, secret store or scheduling engine.
Do not store passwords or tokens in config. Keep personal configuration in the ignored
`agent-workstation.local.toml` or outside this repository.

The pinned upstream read_file also caps a page at 2,000 lines. Raising max_bytes does not
remove that cap; use next_start_line to read the remaining pages.
