#!/usr/bin/env python3
"""Holdout cases for the v1.0.0 additions (written from the spec before the code, never tuned to the implementation):
mark-as-wanted suggestions, --json, pre-commit / git hook scanning, cask handling, argument and OS guards, extra roots."""
import sys, os, json, re, subprocess
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(H), "r2"))
from script_harness import run_case, LIBF, L, FIX, SCRIPT

TAB = "brew tab --installed-on-request"
results = []

def check(name, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    results.append(mark)
    print(f"### {name}\n    [{mark}] {detail}".rstrip())

def text(r): return r.stdout
def lines(r): return r.stdout.splitlines()

# -- H01-H05: mark-as-wanted (brew tab) suggestions; the checker must only print them, never run them --
r = run_case("H01", L, LIBF, mode="auto", home_files={".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})
check("H01 autoremove mode, in-use -> 'Mark as wanted' line names it; brew tab never executed",
      r.returncode == 0 and any(l.startswith("Mark as wanted") and f"{TAB} {L}" in l for l in lines(r)) and not r.executed_tab,
      f"rc={r.returncode} executed_tab={r.executed_tab}")

r = run_case("H02", "zzcmd", ["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], mode="auto")
check("H02 autoremove mode, keep (has a command, nobody found) -> 'If you decide to keep' line; not in the 'Mark as wanted' line",
      r.returncode == 0 and any(l.startswith("If you decide to keep") and f"{TAB} zzcmd" in l for l in lines(r))
      and not any(l.startswith("Mark as wanted") and "zzcmd" in l for l in lines(r)) and not r.executed_tab,
      f"rc={r.returncode}")

r = run_case("H03", L, LIBF, onrequest=True, home_files={".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})
check("H03 explicit mode, already installed_on_request -> no brew tab suggestion at all",
      r.returncode == 0 and TAB not in text(r) and r.cls and r.cls[0].startswith("🔴"), f"rc={r.returncode}")

r = run_case("H04", L, LIBF, home_files={".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})
check("H04 explicit mode, not installed_on_request, in-use -> suggestion present; brew tab never executed",
      r.returncode == 0 and any(l.startswith("Mark as wanted") and f"{TAB} {L}" in l for l in lines(r)) and not r.executed_tab,
      f"rc={r.returncode}")

r = run_case("H05", L, LIBF, notab=True, home_files={".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})
check("H05 old Homebrew without `brew tab` -> no suggestion, still rc 0 and in-use",
      r.returncode == 0 and TAB not in text(r) and r.cls and r.cls[0].startswith("🔴"), f"rc={r.returncode}")

r = run_case("H16", L, LIBF, infofail=True, home_files={".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})
check("H16 explicit mode, `brew info` fails -> verdict still in-use, no suggestion, a note mentions brew info",
      r.returncode == 0 and TAB not in text(r) and r.cls and r.cls[0].startswith("🔴") and "brew info" in text(r), f"rc={r.returncode}")

# -- H06-H08: pre-commit / git hooks --
r = run_case("H06", "zzpython@3.99", ["bin/python3.99"], home_files={
    "Desktop/proj/.git/hooks/pre-commit": "#!/usr/bin/env bash\nINSTALL_PYTHON=/opt/homebrew/opt/zzpython@3.99/bin/python3.99\nexec \"$INSTALL_PYTHON\" -mpre_commit \"$@\"\n",
    "Desktop/proj/.git/hooks/pre-push.sample": "#!/bin/sh\n/opt/homebrew/opt/zzpython@3.99/bin/python3.99\n"})
check("H06 pre-commit hook in <project>/.git/hooks hard-codes INSTALL_PYTHON -> in-use with git-hook evidence",
      r.returncode == 0 and r.cls and r.cls[0].startswith("🔴") and any("git-hook" in l and "pre-commit" in l for l in lines(r)),
      f"rc={r.returncode} cls={r.cls[:1]}")

r = run_case("H06b", "zzpython@3.99", ["bin/python3.99"], home_files={
    "Desktop/proj/.git/hooks/pre-push.sample": "#!/bin/sh\n/opt/homebrew/opt/zzpython@3.99/bin/python3.99\n"})
check("H06b only a *.sample hook mentions it -> not counted (keep, because it has a command)",
      r.returncode == 0 and r.cls and r.cls[0].startswith("🟡"), f"cls={r.cls[:1]}")

r = run_case("H07", "zzpython@3.99", ["bin/python3.99"], home_files={
    ".cache/pre-commit/repo0abc/py_env-python3.99/pyvenv.cfg": "home = /opt/homebrew/opt/zzpython@3.99/bin\nversion = 3.99.0\n"})
check("H07 pre-commit environment under ~/.cache/pre-commit bound to it -> in-use with python-env evidence",
      r.returncode == 0 and r.cls and r.cls[0].startswith("🔴") and any("python-env" in l and "pre-commit" in l for l in lines(r)),
      f"cls={r.cls[:1]}")

r = run_case("H08", L, LIBF, prefix="FAKE", home_files={
    ".cache/pre-commit/repo0abc/py_env-python3.12/pyvenv.cfg": lambda P, h: f"home = {P}/opt/zzgone/bin\n"})
check("H08 pre-commit environment whose Homebrew Python is gone -> listed as a broken Python environment (unrelated to the verdict)",
      r.returncode == 0 and "broken Python environment" in text(r) and "zzgone" in text(r) and r.cls and r.cls[0].startswith("🟢"),
      f"cls={r.cls[:1]}")

r = run_case("H14", "zzpython@3.99", ["bin/python3.99"], home_files={
    ".gitconfig": "[core]\n\thooksPath = ~/githooks\n",
    "githooks/pre-commit": "#!/bin/sh\nexec /opt/homebrew/opt/zzpython@3.99/bin/python3.99 -m lint\n"})
check("H14 global core.hooksPath directory is scanned -> in-use with git-hook evidence",
      r.returncode == 0 and r.cls and r.cls[0].startswith("🔴") and any("git-hook" in l for l in lines(r)), f"cls={r.cls[:1]}")

# -- H09-H10: --json --
hf = {".local/pipx/venvs/t/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n", "Desktop/proj/run.sh": f"export X=/opt/homebrew/opt/{L}/lib\n"}
rt = run_case("H09 text", L, LIBF, mode="auto", home_files=hf)
rj = run_case("H09 json", L, LIBF, mode="auto", home_files=hf, flags=["--json"])
ok = False; detail = f"rc={rj.returncode}"
try:
    d = json.loads(rj.stdout)
    res = d["results"][0]
    kinds = [e["kind"] for e in res["evidence"]]
    m = re.search(r"in-use (\d+) / unverified (\d+) / keep (\d+) / removable (\d+) / not-installed (\d+) / cask (\d+)", rt.stdout)
    tcounts = [int(x) for x in m.groups()] if m else None
    jcounts = [d["summary"][k] for k in ("in-use", "unverified", "keep", "removable", "not-installed", "cask")]
    ok = (d["schema_version"] == 1 and d["tool"] == "brew-leftovers" and d["mode"] == "autoremove-list"
          and res["name"] == L and res["verdict"] == "in-use" and "python-env" in kinds and "project-file" in kinds
          and res["installed_on_request"] is False and d["suggestions"]["mark_wanted"] == f"{TAB} {L}"
          and tcounts == jcounts and isinstance(d["broken_python_envs"], list) and rj.returncode == 0)
    detail += f" kinds={kinds} text={tcounts} json={jcounts} mark_wanted={d['suggestions']['mark_wanted']!r}"
except Exception as e:
    detail += f" error={e!r} head={rj.stdout[:120]!r}"
check("H09 --json: valid JSON, schema_version 1, verdict/evidence kinds/suggestion present, counts equal the text run", ok, detail)

rj = run_case("H10", L, LIBF, flags=["--json"], extra_path=os.path.join(FIX, "pyfail"))
check("H10 --json with a broken python3 -> exit 2 and a message on stderr (no half JSON on stdout)",
      rj.returncode == 2 and rj.stdout.strip() == "" and "python3" in rj.stderr, f"rc={rj.returncode} stderr={rj.stderr.strip()[:80]!r}")

# -- H11: cask --
r = run_case("H11", "zzapp", [], installed=False, casks=["zzapp"])
check("H11 a cask name -> '⚠️ cask' line (kept), not 'not-installed'",
      r.returncode == 0 and r.cls and r.cls[0].startswith("⚠️ cask"), f"cls={r.cls[:1]}")
r = run_case("H11b", "zznothing", [], installed=False)
check("H11b unknown name -> '⚪ not-installed'", r.returncode == 0 and r.cls and r.cls[0].startswith("⚪ not-installed"), f"cls={r.cls[:1]}")

# -- H12-H13: guards --
r = run_case("H12a", L, LIBF, flags=["--version"], mode="auto")
check("H12a --version prints 'brew-leftovers <semver>' and exits 0",
      r.returncode == 0 and re.match(r"^brew-leftovers \d+\.\d+\.\d+\s*$", r.stdout), f"out={r.stdout.strip()!r}")
r = run_case("H12b", L, LIBF, flags=["--help"], mode="auto")
check("H12b --help exits 0 and mentions --json", r.returncode == 0 and "--json" in r.stdout, f"rc={r.returncode}")
r = run_case("H12c", L, LIBF, flags=["--bogus"], mode="auto")
check("H12c unknown flag -> exit 2", r.returncode == 2, f"rc={r.returncode}")
r = run_case("H12d", L, LIBF, mode="none")
check("H12d no arguments and an empty autoremove list -> one 'Nothing to check' line, exit 0",
      r.returncode == 0 and "Nothing to check" in r.stdout and not r.cls, f"out={r.stdout.strip()[:80]!r}")
r = run_case("H13", L, LIBF, extra_path=os.path.join(FIX, "linux"))
check("H13 not macOS (uname -s = Linux) -> exit 2 with a message mentioning macOS",
      r.returncode == 2 and "macOS" in r.stderr, f"rc={r.returncode} stderr={r.stderr.strip()[:80]!r}")

# -- H15: extra roots --
import tempfile, shutil
ex = tempfile.mkdtemp(prefix="bl-extra-")
try:
    open(os.path.join(ex, "deploy.sh"), "w").write(f"export DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n")
    r = run_case("H15", L, LIBF, extra_env={"BREW_LEFTOVERS_EXTRA_ROOTS": ex})
    check("H15 BREW_LEFTOVERS_EXTRA_ROOTS directory outside HOME is scanned -> in-use with config-file evidence",
          r.returncode == 0 and r.cls and r.cls[0].startswith("🔴") and any("config-file" in l and "deploy.sh" in l for l in lines(r)), f"cls={r.cls[:1]}")
finally:
    shutil.rmtree(ex, ignore_errors=True)

bad = results.count("FAIL")
print(f"RESULT holdout ran={len(results)} bad={bad} xfail=0")
sys.exit(1 if bad else 0)
