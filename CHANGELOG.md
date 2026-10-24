# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-25

### Added

- `oss-ready` CLI with seven checks: required files, license, README,
  `.gitignore`, build artifacts, large files, secrets and CI config.
- Machine-readable output via `--json`.
- `--strict` mode that fails the run on warnings as well as errors.
- Exit codes: `0` clean, `1` problems found, `2` bad invocation.
