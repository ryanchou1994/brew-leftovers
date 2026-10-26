# brew-leftovers

Before (or after) `brew uninstall`, find out who **outside Homebrew** still uses a formula. Read-only: it never removes anything. Offline, too: the tool itself never connects to the network or uploads anything; it only reads files on your Mac and queries your local `brew`.

`brew uninstall` also removes the dependencies that were "only installed for" the formula you removed. Homebrew's dependency graph is accurate for Homebrew, but it cannot see the other users on your Mac: pipx tools and project virtualenvs bound to a Homebrew Python, launchd jobs, shell and tool configs, scripts that hard-code `/opt/homebrew/opt/...`, compiled apps that link a Homebrew library, git hooks. `brew uses --installed` answers "which *formulae* depend on it"; `brew-leftovers` answers "who *else* does".

Two real incidents behind this tool: removing one CLI took `python@3.12` with it, which broke a pipx tool and two project virtualenvs that were only noticed seven weeks later; removing another CLI took `ripgrep` with it, which some apps call at run time.

## What it does

Output of a real run against a test fixture (mock `brew`; the fake home folder is shown as `/Users/me`):

```
$ brew leftovers
Checking 3 formula(e) (read-only; scans project folders, config files and apps; usually a few minutes, longer with large project folders)…
────────────────────────────────────────
🔴 in-use  python@3.14: something still uses it -> keep
     · python-env: /Users/me/.local/pipx/venvs/pip-audit /Users/me/Projects/site/.venv
     · git-hook: /Users/me/Projects/site/.git/hooks/pre-commit
────────────────────────────────────────
🟡 keep  ripgrep: no users found in the scanned locations (which does not prove there are none), but it provides commands (rg) -> keep by default
     · note: some apps and scripts run a command only when needed, which a file scan cannot see; confirm before removing
────────────────────────────────────────
🟢 removable  libyaml: library only, no users found in the scanned locations -> may be removed (confirm first)
────────────────────────────────────────
Summary: in-use 1 / unverified 0 / keep 1 / removable 1 / not-installed 0 / cask 0
Scanned: brew dependents; Python environments (pipx, project .venv, poetry/uv, pre-commit); ~/.local/bin, LaunchAgents/Daemons, shell and git/ssh/npm/pip configs; git hooks; project folders (~/Projects); apps and compiled binaries; running processes; open files; symlinks
Not scanned: other user accounts; external drives; cloud-synced folders not under a project root; uses on other machines
Reinstall if removed by mistake: brew install libyaml
Remove only after confirming (nothing is removed by this script): HOMEBREW_NO_AUTOREMOVE=1 brew uninstall libyaml
Mark as wanted (in use) so brew stops listing them as removable: brew tab --installed-on-request python@3.14
If you decide to keep these, mark them as wanted: brew tab --installed-on-request ripgrep
```

With no arguments it checks everything `brew autoremove --dry-run` would remove. With names it checks those formulae, which is the thing to do *before* `brew uninstall something`:

```
$ brew leftovers python@3.14 ripgrep
```

### Verdicts

Every result line starts with a stable label; `--json` uses the same strings.

| Label | Meaning | What to do |
|-------|---------|------------|
| `in-use` | Something outside Homebrew uses it; the evidence is listed | keep |
| `unverified` | A brew query or a scan failed, timed out, or could not read a file or folder, so nobody can vouch for it | keep |
| `keep` | No user found in the scanned locations, but the formula provides commands or data files (shell plugins, completions, certificates, configs) that programs may use only at run time | keep by default |
| `removable` | Library only, and no user found in the scanned locations | may be removed, after you confirm |
| `not-installed` | Homebrew has nothing by that name | nothing |
| `cask` | An app; only command-line formulae are checked | keep |

The bias is deliberate: proving that nothing uses a library is impossible, so every doubt resolves to "keep". If you remove something by mistake, `brew install <name>` brings it back.

### Where it looks

| Evidence kind | Locations |
|---------------|-----------|
| `brew-dependents` | `brew uses --installed` |
| `python-env` | `pyvenv.cfg` files under pipx, `~/.virtualenvs`, poetry and uv caches, pyenv, pre-commit's cache and your project folders, whose `home` points at the formula |
| `config-file` | `~/.local/bin` scripts, shell startup files, `~/.config`, git/ssh/npm/pip/bundler/cargo/docker/colima/lima configs, VS Code-family settings, Claude Code and Codex settings, `/etc/paths*` |
| `git-hook` | `<project>/.git/hooks/*` and the global `core.hooksPath` directory (pre-commit hard-codes the Python it was installed with) |
| `launchd` | `~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`, Automator workflows; binary plists are converted before matching |
| `crontab` | your crontab |
| `symlink` | links under `~/.local`, `~/bin`, `~/.config`, LaunchAgents and home dotfiles that point into the Homebrew prefix |
| `project-file` | scripts and configuration files in your project folders (`.sh`, `.py`, `Makefile`, `Dockerfile`, `CMakeLists.txt`, `package.json` scripts, ...), including extension-less scripts |
| `binary` | Mach-O executables and libraries that link the formula: `/Applications`, `~/Applications`, `~/.local/bin`, `~/.cargo/bin`, `~/go/bin`, language runtimes (rbenv, pyenv, mise/asdf, nvm, volta, bun, gems), virtualenv site-packages, `@rpath` references |
| `process`, `open-file` | running processes and `lsof` |

Project folders default to `~/Desktop`, `~/Documents`, `~/Developer`, `~/Projects`, `~/code` and `~/src` (those that exist). Only file names are ever printed, never file contents.

It also lists **broken Python environments**: virtualenvs whose Homebrew Python is already gone, which is exactly the damage this tool exists to prevent.

## Install

Requirements: macOS, Homebrew, the `python3` that ships with macOS Command Line Tools (used for the binary scan and `--json`), and `coreutils` for `gtimeout` (`brew install coreutils`). Without `timeout`/`gtimeout` nothing is cut short and the tool treats the missing time limit as a warning, so every formula that is not proven `in-use` comes out `unverified` and nothing is ever reported `removable`.

```
git clone https://github.com/ryanchou1994/brew-leftovers.git
ln -s "$PWD/brew-leftovers/brew-leftovers" ~/.local/bin/brew-leftovers   # any directory on your PATH
brew leftovers --version
```

Homebrew runs any executable named `brew-<something>` found on `PATH` as `brew <something>`, so once the file is on your PATH both `brew leftovers` and `brew-leftovers` work. `brew help leftovers` shows the short help.

## Close the loop: mark keepers as wanted

A verdict of `in-use` does not change Homebrew's own bookkeeping: the formula is still "installed as a dependency" in brew's eyes, so `brew autoremove` will list it again next time, and a manual `brew autoremove` on a machine without `HOMEBREW_NO_AUTOREMOVE=1` would still remove it. Homebrew's way to say "I want this" is:

```
brew tab --installed-on-request <formula>
```

`brew-leftovers` prints that command, filled in, for every formula it judged `in-use`, and a second, clearly separate line for the `keep` ones in case you decide to keep them. It only prints the command; it never runs it. (`brew tab` exists since Homebrew 4.3.6; on older versions the lines are simply not printed.)

Recommended companion setting, so that `brew uninstall`, `brew upgrade` and `brew cleanup` stop removing dependencies on their own:

```
echo 'HOMEBREW_NO_AUTOREMOVE=1' >> "$(brew --prefix)/etc/homebrew/brew.env"
```

That file is read by `brew` itself, so it also covers launchd jobs and non-interactive shells. Note that a manual `brew autoremove` ignores this setting; that is what `brew leftovers` is for.

## Machine-readable output

```
brew leftovers --json [<formula> ...]
```

prints one JSON object (`schema_version` 1). Adding fields will not bump the schema version; changing or removing one will. Abridged example (one result shown, some arrays shortened):

```json
{
  "schema_version": 1,
  "tool": "brew-leftovers",
  "version": "1.0.1",
  "mode": "autoremove-list",
  "brew_prefix": "/opt/homebrew",
  "results": [
    {
      "name": "python@3.14",
      "canonical": "python@3.14",
      "verdict": "in-use",
      "evidence": [
        {"kind": "python-env", "items": ["/Users/me/Projects/site/.venv"]},
        {"kind": "git-hook", "items": ["/Users/me/Projects/site/.git/hooks/pre-commit"]}
      ],
      "warnings": [],
      "provides": {"commands": ["python3.14"], "linked": true, "data_files": true},
      "installed_on_request": false
    }
  ],
  "summary": {"in-use": 1, "unverified": 0, "keep": 0, "removable": 0, "not-installed": 0, "cask": 0},
  "warnings": [],
  "suggestions": {
    "mark_wanted": "brew tab --installed-on-request python@3.14",
    "mark_wanted_if_keeping": null,
    "reinstall": null,
    "remove_after_confirming": null
  },
  "scanned": {"project_roots": ["/Users/me/Projects"], "not_scanned": ["other user accounts", "..."]},
  "broken_python_envs": []
}
```

`mode` is `autoremove-list` (no arguments) or `explicit`. Evidence lists use the same caps as the text output: at most six items for most kinds, four for `symlink` and three for `process`; `python-env`, `launchd` and `brew-dependents` are not capped (`crontab` and `open-file` always have a single item). Exit status is 0 whenever the check ran, whatever the verdicts; 2 when it could not run (no brew, bad arguments, not macOS, no python3 for `--json`).

## Using it with an AI coding assistant

Assistants are good at `brew uninstall` and bad at noticing what else went away. Two things work well:

1. Tell the assistant to run `brew leftovers <name>` before any `brew uninstall <name>`, and `brew leftovers --json` afterwards, and to treat anything but `removable` as "keep". The ASCII labels and `--json` exist so that it does not have to read emoji.
2. With Claude Code, a `PreToolUse` hook on `Bash` can remind it. A minimal version:

```bash
#!/usr/bin/env bash
# ~/.claude/hooks/brew-uninstall-reminder.sh — add it to settings.json under hooks.PreToolUse (matcher "Bash")
cmd=$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("command",""))')
case "$cmd" in
  *"brew uninstall"*|*"brew remove"*|*"brew rm"*|*"brew autoremove"*)
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"Run `brew leftovers <name>` before removing, and `brew leftovers` afterwards; keep anything that is not removable."}}\n' ;;
esac
exit 0
```

## Limits

- **macOS only.** It relies on `plutil`, BSD `stat`, `lsof` and Mach-O parsing. Linuxbrew would need ELF parsing and a different file layout; not planned for now.
- **It never removes anything**, and it never will. The `brew uninstall` line in the output is for you to copy after you have decided.
- **"No users found" means "none in the scanned locations".** Other user accounts, external drives, cloud-synced folders outside your project roots and other machines are not scanned, and programs that call a command by name at run time leave no trace in any file. That is why formulae with commands are `keep`, not `removable`.
- **It errs towards keeping.** A command name that is a prefix of another tool's name (`zzc` vs `zzc-helper`) can produce a false `in-use`. That is accepted: the safe direction.
- **Scans take time.** Usually a few minutes, longer with large project folders; each scan group has a timeout (`BREW_LEFTOVERS_SCAN_TIMEOUT`, default 240 s) and a timeout turns the verdict into `unverified`, never into `removable`.
- **Unreadable files count as "not checked".** If any scan cannot read a file or folder (no permission, or macOS privacy protection, e.g. a terminal without Full Disk Access reading `~/Desktop` or `~/Documents`), every formula not already proven `in-use` becomes `unverified`, and the reason line names the first path it could not read. Give the terminal access, or fix the permission, and run it again.

Environment variables: `BREW_LEFTOVERS_PROJECT_ROOTS` (colon-separated project folders), `BREW_LEFTOVERS_SYSTEM_ROOTS` (`/Applications:/Library/LaunchAgents:/Library/LaunchDaemons` by default; empty string to skip), `BREW_LEFTOVERS_EXTRA_ROOTS` (extra folders to scan for both text references and binaries), `BREW_LEFTOVERS_SCAN_TIMEOUT`.

## Tests

```
bash tests/run.sh
```

132 cases run against a fake `HOME` with a mock `brew` and mock `lsof`; nothing touches your real Homebrew. They include two adversarial rounds inherited from the private version of this script (config files in unusual places, symlinked dotfiles, binary plists with non-ASCII strings, prefixes with spaces, broken `python3`, scans that time out) plus a holdout set written from the spec for the 1.0.0 additions, and (1.0.1) cases for unreadable files and folders and for timed-out searches, with a second blind holdout set that also checks ordinary oddities (broken symlinks, empty folders, odd file names) do not raise false warnings. Two cases are expected failures and are reported as `XFAIL`: a known over-match that errs towards keeping, and a fixture limitation covered by another case. `coreutils` is needed here too: without `gtimeout` the two timeout cases fail and most verdicts collapse to `unverified`.

## License

[MIT](LICENSE).

繁體中文說明：[README.zh-TW.md](README.zh-TW.md)
