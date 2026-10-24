# Contributing

Thanks for taking a look. This is a small, dependency-free project, so the
workflow is deliberately short.

## Development setup

```bash
python -m unittest discover -s tests -v
python -m oss_ready .        # run the tool on itself
```

The package lives in `src/`. To run it straight from a checkout without
installing:

```bash
PYTHONPATH=src python -m oss_ready .
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m oss_ready .
```

## Ground rules

- **No third-party dependencies.** Standard library only, so the tool can
  audit machines that have nothing installed.
- **Checks must not crash.** A malformed file is a finding, not an exception.
- **Every new check needs a test** in `tests/test_checks.py`, including the
  failure path.
- **Keep messages actionable.** Say what is wrong and what to do about it.

## Submitting a change

1. Add a test that fails for the right reason.
2. Make it pass.
3. Run the full suite and the self-audit.
4. Describe the user-visible effect in the pull request.

By contributing you agree that your work is licensed under the MIT License
(see `LICENSE`).
