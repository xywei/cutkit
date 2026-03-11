# Contributing

Thanks for your interest in CUTKIT.

## Development setup

1. Ensure `uv` is installed and Python 3.12+ is available.
2. Bootstrap development tooling and run checks:

```bash
make dev
```

3. Run checks manually as needed:

```bash
uv run prek run --all-files
```

4. For feature work, use OpenSpec change artifacts:

```text
/opsx-propose <idea>  # OpenCode
/opsx-apply <change>  # OpenCode
/opsx-archive <change>  # OpenCode

# Or namespace form in tools that support it:
/opsx:propose <idea>
/opsx:apply <change>
/opsx:archive <change>
```

## Pull requests

- Keep changes focused.
- Add tests for new behavior.
- Update docs when API behavior changes.
