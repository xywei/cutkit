# Entire Transcript Policy

This project uses Entire for AI session traceability with the following guardrails.

## Policy

- Use Entire only on feature branches (for example: `feature/*`, `bugfix/*`, or topic branches).
- Do not run active Entire sessions on `main`.
- Never include secrets in prompts or files (API keys, credentials, tokens, private data).
- Treat transcript redaction as best-effort, not guaranteed.

## Recommended Setup

Enable Entire with local settings and disable automatic checkpoint pushes:

```bash
entire enable --local --skip-push-sessions --telemetry=false
```

This keeps transcript metadata local unless you intentionally push it.

## Feature Branch Workflow

1. Create and switch to a feature branch.
2. Run `entire status` and confirm the active branch is not `main`.
3. Work normally with your AI agent.
4. Use `entire explain <commit>` when you need traceability context.
5. Before merge, verify no sensitive content is present in session logs.

## Cleanup / Reset Playbook

- Diagnose stuck sessions:

  ```bash
  entire doctor
  ```

- Remove orphaned local artifacts:

  ```bash
  entire clean
  ```

- Reset Entire metadata for the current HEAD (destructive for session state):

  ```bash
  entire reset --force
  ```

- Disable Entire in this repository:

  ```bash
  entire disable
  ```
