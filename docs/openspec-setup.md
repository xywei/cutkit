# OpenSpec Setup

This repository is initialized with OpenSpec for spec-driven changes.

## Prerequisites

- Node.js 20.19.0 or newer
- `openspec` CLI available on `PATH`

## Initialize (already done in this repo)

```bash
openspec init --tools opencode,codex
```

This creates:

- `openspec/` change and spec directories
- `.opencode/command/opsx-*.md` slash commands
- `.opencode/skills/openspec-*/SKILL.md` skills
- `.codex/skills/openspec-*/SKILL.md` skills

## Recommended Daily Flow

1. Start a proposal:

   ```text
   /opsx-propose <change-name-or-idea>   # OpenCode
   /opsx:propose <change-name-or-idea>   # tools with namespace slash commands
   ```

2. Implement the change tasks:

   ```text
   /opsx-apply <change-name>
   /opsx:apply <change-name>
   ```

3. Archive after completion:

   ```text
   /opsx-archive <change-name>
   /opsx:archive <change-name>
   ```

4. Run repository checks before merge:

   ```bash
   make dev
   uv run python scripts/run_cutpanel_eval.py
   ```

## Notes

- Keep plan artifacts inside `openspec/changes/<change>/`.
- Keep architecture and quality docs in `docs/` updated as behavior evolves.
