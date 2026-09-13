# Architecture and decisions

```text
MCP client + model (not provided here)
              |
   stdio / authenticated loopback HTTP
              |
        Agent Workstation
     /         |          explicit   target     bounded
 host mode  guide      previews
              |
   pinned Coding Tools MCP runtime
              |
      local files / Git / commands
              |
 user-installed API/CLI tools and credentials
```

## Why an adapter, not a replacement?

File patching, process lifetimes, Git operations and MCP protocol semantics already exist upstream.
This release reuses them and concentrates upstream imports/hooks in one compat module.
The runtime is subclassed for HOME, command normalization, output defaults and guide handling.
Two remaining process-global hooks extend input schemas/tool registration and instruction discovery.
They are idempotent but not a stable upstream extension API: do not load multiple incompatible
adapter versions into one Python process. Startup verifies VCS provenance, not just version text.

## Context

Startup checks actual `.git` roots and direct child directories; it does not traverse every file.
Git metadata is preferred for repository rules. Generated and worktree directories are excluded
from startup discovery. This is a performance choice, not permission to ignore their rules:
workspace_guide resolves the selected target and walks its ancestors for applicable instructions.
Safe symlink checks and physical-file deduplication avoid outside-root aliases and duplicate rules.
Bounds return warnings; catalogs are not claimed complete after truncation.

`workspace_guide` returns names/descriptions/paths, not all Skill bodies. Agent selection and
instruction reuse are workflow behavior, not a built-in semantic router or token cache.
Nested `.agents/skills` plus explicitly configured roots form the skill catalog. Recipes only
reference Skill files. No `eval`, script execution, production access or extra authority is granted.

## Output

The first response favors a byte-bounded preview with start/end excerpts. A short error stream
gets its own budget. Explicit caller options override defaults. The adapter preserves upstream
exit status, command IDs, eviction/truncation markers and output references. A continuation can
read only what upstream still retains. Buffer loss is not hidden and replay is not invented.
Benchmark output sizes, not subscription savings or LLM success rates.

## Trust

Workspace policy is different from OS confinement. Host mode trades isolation for user identity
and CLI reuse; it cannot also promise that secrets are inaccessible to the model. HTTP requires
an operator-provided token and a loopback bind; remote TLS/OAuth is a separate deployment concern.
No GUI/secret broker is published until its usefulness and policy guarantees can be validated.

## Useful review questions

- Can a caller's explicit output budget override the defaults?
- Can workspace mode silently become host mode through an environment variable?
- Does a truncated search or lost log segment still look complete?
- Can a config or Skill execute code simply by being loaded?
- What is validated by a direct API call, and what still requires UI evidence?
- Which measurements come from this adapter and which are inherited from upstream?
