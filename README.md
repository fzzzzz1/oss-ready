# oss-ready

> Audit a project directory **before** you make it public.

`oss-ready` is a zero-dependency Python CLI that answers one question: *is this
repository actually ready to be open sourced?* It looks for the things people
forget at the last minute — a license, a README that explains anything, a
`.gitignore` that keeps caches and `.env` files out, stray build artifacts,
oversized binaries committed by accident, and credentials that leaked into a
source file.

It is deliberately boring: standard library only, no network access, no config
files, one command.

## Install

```bash
pip install .
```

Or run it straight from a checkout:

```bash
PYTHONPATH=src python -m oss_ready .
```

## Usage

```bash
oss-ready                 # audit the current directory
oss-ready path/to/repo    # audit somewhere else
oss-ready --json          # machine-readable output
oss-ready --strict        # warnings count as failures (good for CI)
```

### Sample output

```
oss-ready 0.1.0 - is this project ready to go public?
root: C:\Users\Administrator\Desktop\deepseek1
----------------------------------------------------------------
  [ok]   files       README and LICENSE present
  [ok]   license     LICENSE looks like MIT
  [ok]   readme      README.md has a heading and real content
  [ok]   gitignore   .gitignore covers 6 common patterns
  [ok]   artifacts   no build artifacts at the project root
  [ok]   large files no file over 5 MB
  [ok]   secrets     no obvious credentials in tracked text files
  [ok]   ci          CI config found at .github/workflows
----------------------------------------------------------------
  score 100%   (8 ok, 0 warn, 0 error)
  verdict: ready to publish
```

## What it checks

| Check | Looks for | If missing |
| --- | --- | --- |
| `files` | `README`, `LICENSE` at the root | error |
| `license` | a recognised standard license text (MIT, Apache-2.0, GPL, MPL, BSD, Unlicense) | error / warn |
| `readme` | a heading and at least 200 characters of content | warn |
| `gitignore` | at least 3 of the common ignore patterns | warn |
| `artifacts` | `dist/`, `build/`, `node_modules/`, `__pycache__/`… | warn |
| `large files` | any file over 5 MB | warn |
| `secrets` | AWS keys, `sk-…` keys, GitHub/Slack tokens, private key blocks, hardcoded credentials | error |
| `ci` | GitHub Actions, GitLab CI, CircleCI, Jenkins… | warn |

Exit codes: `0` clean, `1` problems found, `2` bad invocation.

## What it does **not** do

- It is not a legal review. A passing score does not mean you have the right
  to publish the code or its dependencies.
- Secret detection is pattern-based and heuristic. A clean run lowers risk; it
  does not prove anything.
- It does not read git history. Secrets deleted in a later commit are still in
  the history — scan that separately with a dedicated tool.

## Development

```bash
python -m unittest discover -s tests -v   # 13 tests
python -m oss_ready .                     # self-audit
```

See `CONTRIBUTING.md` for the ground rules.

## License

MIT — see `LICENSE`.
