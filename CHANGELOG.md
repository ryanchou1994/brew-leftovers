# Changelog

## 1.0.0 - 2026-10-19

First public release. The checker evolved from a private script (2026-09, two adversarial review rounds, 95 cases) that has been in daily use since late September 2026; this release makes it a standalone tool.

- `brew leftovers` works as a Homebrew external command once `brew-leftovers` is on `PATH`.
- English output with stable ASCII verdict labels (`in-use`, `unverified`, `keep`, `removable`, `not-installed`, `cask`) next to the emoji.
- `--json`: one machine-readable object, `schema_version` 1.
- "Mark as wanted" suggestions: prints `brew tab --installed-on-request ...` for formulae judged `in-use` (and, separately, for `keep`), only when `brew tab` exists and the formula is not already marked. Never executed.
- git hooks and pre-commit: `<project>/.git/hooks/*`, the global `core.hooksPath` directory and `~/.cache/pre-commit` environments are scanned (new evidence kind `git-hook`).
- `brew` is found on `PATH`, `/opt/homebrew/bin` or `/usr/local/bin` (Apple silicon and Intel); the prefix comes from `HOMEBREW_PREFIX` when run through `brew`.
- `BREW_LEFTOVERS_EXTRA_ROOTS` for extra folders; all variables are prefixed `BREW_LEFTOVERS_`.
- Refuses to run on anything but macOS (exit 2) instead of failing half-way.
- Tests: 116 cases (`tests/run.sh`), GitHub Actions on macOS with shellcheck.
