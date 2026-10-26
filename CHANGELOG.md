# Changelog

## 1.0.1 - 2026-10-26

Fix: a search that could not read a file or folder (or timed out) could still end in `removable` and print a `brew uninstall` suggestion. It now ends in `unverified`, as the README always promised.

- Read errors are detected for every search: config-file and project scans (`grep` exits 2 even when it also matched), the extension-less script search and the `grep` over those files, the Python-environment search and each `pyvenv.cfg`, git hook folders, LaunchAgent/Daemon files, symlink search, editor settings, and the binary scan (unreadable Mach-O files and folders).
- The `grep` over extension-less scripts now runs under the scan timeout too; a timeout of the extension-less file search is reported instead of ignored.
- The reason line names the first path that could not be read (path only, never contents).
- Tests: 132 cases (10 new regression cases, 6 new blind holdout cases); `run_case` in the test harness can lock files (`chmods`) and create empty folders.

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
