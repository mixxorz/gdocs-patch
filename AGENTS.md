# AGENTS.md
- Use Python 3.10+ and manage dependencies and commands with `uv`.
- Keep model classes ordinary, mutable, hand-written, and explicitly typed.
- Use keyword-only constructors, `snake_case` attributes, and inline `Literal` types.
- Group Docs models by semantic feature under `packages/gdocs-patch/src/gdocs_patch/models/`.
- Preserve intentional `UNSET` and proto-default behavior.
- Test meaningful behavior and invariants; avoid tests that restate definitions.
- Run pytest, Ruff lint/format, Fixit, Pyright, and pre-commit before completion.
- Use a dedicated feature branch or worktree for non-trivial changes.
