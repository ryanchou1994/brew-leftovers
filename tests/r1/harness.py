#!/usr/bin/env python3
"""Round 1: 30 adversarial cases. Fake HOME + mock brew/lsof; nothing touches the real Homebrew."""
import os, subprocess, tempfile, shutil, sys, time, plistlib, re

S = os.path.dirname(os.path.abspath(__file__))
T = os.path.dirname(S)
SCRIPT = os.environ.get("BREW_LEFTOVERS_BIN", os.path.join(os.path.dirname(T), "brew-leftovers"))
MOCKBIN = os.path.join(T, "mockbin")
P = "/opt/homebrew"
CLASS = re.compile(r"^(🔴|🟡|🟢|⚪|⚠️) (in-use|unverified|keep|removable|not-installed|cask)\s")

def lib_files(f, bins=()):
    base = f"{P}/Cellar/{f}/1.0"
    out = [f"{base}/INSTALL_RECEIPT.json", f"{base}/include/{f}.h", f"{base}/lib/lib{f}.dylib"]
    out += [f"{base}/bin/{b}" for b in bins]
    return out

def run_case(name, formula, expect, home_files=None, bins=(), lsof="", uses="", mode="args",
             listfail=False, usesfail=False, list_name=None, extra_env=None, xfail=False):
    home = os.path.realpath(tempfile.mkdtemp(prefix="bl1-home-"))
    st = tempfile.mkdtemp(prefix="bl1-state-")
    try:
        os.makedirs(os.path.join(home, ".local", "log"), exist_ok=True)
        os.makedirs(os.path.join(st, "files")); os.makedirs(os.path.join(st, "uses"))
        key = (list_name or formula).replace("/", "__")
        open(os.path.join(st, "installed"), "w").write((list_name or formula) + "\n")
        open(os.path.join(st, "files", key), "w").write("\n".join(lib_files(formula.split("/")[-1], bins)) + "\n")
        open(os.path.join(st, "uses", key), "w").write(uses)
        open(os.path.join(st, "lsof"), "w").write(lsof or "p1\nn/dev/null\n")
        if mode == "auto":
            open(os.path.join(st, "autoremove"), "w").write((list_name or formula) + "\n")
        if listfail: open(os.path.join(st, "listfail"), "w").write("1")
        if usesfail: open(os.path.join(st, "usesfail"), "w").write("1")
        for rel, spec in (home_files or {}).items():
            p = os.path.join(home, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if isinstance(spec, tuple) and spec[0] == "symlink":
                os.symlink(spec[1].replace("$HOME", home), p)
            elif isinstance(spec, bytes):
                open(p, "wb").write(spec)
            else:
                open(p, "w").write(spec)
        env = {"HOME": home, "PATH": MOCKBIN + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
               "BREW_LEFTOVERS_BREW": os.path.join(MOCKBIN, "brew"), "MOCK_STATE": st, "LANG": "en_US.UTF-8",
               "BREW_LEFTOVERS_SYSTEM_ROOTS": ""}  # never scan the real /Applications etc. (no case needs it)
        env.update(extra_env or {})
        args = ["/bin/bash", SCRIPT] + ([list_name or formula] if mode == "args" else [])
        t = time.time()
        r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=300)
        dt = time.time() - t
        cls = [l for l in r.stdout.splitlines() if CLASS.match(l)]
        ok = bool(cls) and cls[0].startswith(expect)
        mark = ("XPASS" if ok else "XFAIL") if xfail else ("PASS" if ok else "FAIL")
        unexpected = open(os.path.join(st, "unexpected")).read() if os.path.exists(os.path.join(st, "unexpected")) else ""
        print(f"### {name}\n    [{mark}] expect={expect} rc={r.returncode} {dt:.1f}s -> {cls[0] if cls else '(no class line)'}")
        for l in r.stdout.splitlines():
            if l.startswith("     · "): print("    " + l.strip().replace(home, "~"))
        if r.stderr.strip(): print("    stderr:", r.stderr.strip()[:300].replace(home, "~"))
        if unexpected: print("    UNEXPECTED brew calls:", unexpected.strip())
        return mark
    finally:
        shutil.rmtree(home, ignore_errors=True); shutil.rmtree(st, ignore_errors=True)

def macho_like(path_str):
    # Looks like a compiled binary: Mach-O magic, NUL bytes, and a load-command style path string.
    return b"\xcf\xfa\xed\xfe\x0c\x00\x00\x01" + b"\x00" * 64 + path_str.encode() + b"\x00" * 32

if __name__ == "__main__":
    sel = sys.argv[1:]
    F = "zzfakelib"
    cases = [
      ("C0 negative control: library nobody uses -> removable", dict(formula=F, expect="🟢")),
      ("C0b positive control: pipx venv bound to it -> in-use", dict(formula=F, expect="🔴", home_files={
          ".local/pipx/venvs/tool/pyvenv.cfg": f"home = {P}/opt/{F}/bin\n"})),
      ("C0c positive control: ~/.local/bin script writes its opt path -> in-use", dict(formula=F, expect="🔴", home_files={
          ".local/bin/run.sh": f"#!/bin/sh\nexport DYLD_LIBRARY_PATH={P}/opt/{F}/lib\n"})),
      ("C1a project venv (~/Desktop/proj/.venv) bound to zzpython@3.99 (has bin)", dict(formula="zzpython@3.99", bins=("python3.99",), expect="🔴", home_files={
          "Desktop/proj/.venv/pyvenv.cfg": f"home = {P}/opt/zzpython@3.99/bin\n"})),
      ("C1b project venv C extension .so links the library (no process running)", dict(formula=F, expect="🔴", home_files={
          "Desktop/proj/.venv/lib/python3.14/site-packages/ext.cpython-314-darwin.so": macho_like(f"{P}/opt/{F}/lib/lib{F}.1.dylib")})),
      ("C1c uv/poetry venv (~/Library/Caches/pypoetry) bound to it", dict(formula="zzpython@3.99", bins=("python3.99",), expect="🔴", home_files={
          "Library/Caches/pypoetry/virtualenvs/app-xyz-py3.99/pyvenv.cfg": f"home = {P}/opt/zzpython@3.99/bin\n"})),
      ("C2 ~/Library/LaunchAgents binary plist uses it", dict(formula=F, expect="🔴", home_files={
          "Library/LaunchAgents/com.x.agent.plist": plistlib.dumps({"Label": "com.x.agent", "ProgramArguments": ["/usr/bin/true"],
              "EnvironmentVariables": {"DYLD_LIBRARY_PATH": f"{P}/opt/{F}/lib"}}, fmt=plistlib.FMT_BINARY)})),
      ("C2b same content as XML plist", dict(formula=F, expect="🔴", home_files={
          "Library/LaunchAgents/com.x.agent.plist": plistlib.dumps({"Label": "com.x.agent", "ProgramArguments": ["/usr/bin/true"],
              "EnvironmentVariables": {"DYLD_LIBRARY_PATH": f"{P}/opt/{F}/lib"}}).decode()})),
      ("C3a ~/Applications/Fake.app main binary links opt/<f>/lib (not running)", dict(formula=F, expect="🔴", home_files={
          "Applications/Fake.app/Contents/MacOS/Fake": macho_like(f"{P}/opt/{F}/lib/lib{F}.1.dylib")})),
      ("C3b compiled executable in ~/.local/bin (Mach-O) links it", dict(formula=F, expect="🔴", home_files={
          ".local/bin/mytool": macho_like(f"{P}/opt/{F}/lib/lib{F}.1.dylib")})),
      ("C3c compiled executable in ~/.cargo/bin links it", dict(formula=F, expect="🔴", home_files={
          ".cargo/bin/rtool": macho_like(f"{P}/opt/{F}/lib/lib{F}.1.dylib")})),
      ("C4a ~/.zshrc PATH uses keg-only opt/<f>/bin", dict(formula="zzkeg", bins=("zzk",), expect="🔴", home_files={
          ".zshrc": f'export PATH="{P}/opt/zzkeg/bin:$PATH"\n'})),
      ("C4b ~/.zprofile exports the library's opt path (DYLD/CPATH style)", dict(formula=F, expect="🔴", home_files={
          ".zprofile": f'export LIBRARY_PATH="{P}/opt/{F}/lib"\n'})),
      ("C5 VS Code settings.json has its include path", dict(formula=F, expect="🔴", home_files={
          "Library/Application Support/Code/User/settings.json": '{"C_Cpp.default.includePath": ["' + f"{P}/opt/{F}/include" + '"]}\n'})),
      ("C5b ~/.claude.json MCP server command uses the opt path", dict(formula=F, expect="🔴", home_files={
          ".claude.json": '{"mcpServers":{"x":{"command":"' + f"{P}/opt/{F}/libexec/x" + '"}}}\n'})),
      ("C6a special characters zz+x.y@1.2: pipx cfg", dict(formula="zz+x.y@1.2", expect="🔴", home_files={
          ".local/pipx/venvs/t/pyvenv.cfg": f"home = {P}/opt/zz+x.y@1.2/bin\n"})),
      ("C6b special characters zz+x.y@1.2: ~/.local/bin symlink", dict(formula="zz+x.y@1.2", expect="🔴", home_files={
          ".local/bin/zzx": ("symlink", f"{P}/Cellar/zz+x.y@1.2/1.0/lib/libzz.dylib")})),
      ("C6c special characters, near miss: cfg says zz+x.y@1.20, checking zz+x.y@1.2 -> removable", dict(formula="zz+x.y@1.2", expect="🟢", home_files={
          ".local/pipx/venvs/t/pyvenv.cfg": f"home = {P}/opt/zz+x.y@1.20/bin\n"})),
      ("C7 keg-only: has Cellar/bin but not linked into PATH -> keep", dict(formula="zzkeg", bins=("zzk",), expect="🟡")),
      ("C8a tap formula (autoremove lists owner/tap/zzfakelib) bound by pipx cfg", dict(formula=F, list_name=f"owner/tap/{F}", mode="auto", expect="🔴", home_files={
          ".local/pipx/venvs/tool/pyvenv.cfg": f"home = {P}/opt/{F}/bin\n"})),
      ("C8b tap formula referenced by a ~/.local/bin script", dict(formula=F, list_name=f"owner/tap/{F}", mode="auto", expect="🔴", home_files={
          ".local/bin/run.sh": f"#!/bin/sh\nexport DYLD_LIBRARY_PATH={P}/opt/{F}/lib\n"})),
      ("C9 ~/.local/bin symlink to a script elsewhere (script has the opt path)", dict(formula=F, expect="🔴", home_files={
          "Desktop/proj/tool.sh": f"#!/bin/sh\nexec {P}/opt/{F}/libexec/tool \"$@\"\n",
          ".local/bin/tool": ("symlink", "$HOME/Desktop/proj/tool.sh")})),
      ("C10 only lsof sees it (opt path, not Cellar)", dict(formula=F, expect="🔴", lsof=f"p123\nn{P}/opt/{F}/lib/lib{F}.1.dylib\n")),
      ("C11 referenced via brew link path /opt/homebrew/lib/lib<f>.1.dylib (fixture only lists lib<f>.dylib; covered by extra R25)", dict(formula=F, expect="🔴", xfail=True, home_files={
          ".local/bin/run.sh": f"#!/bin/sh\nexport DYLD_INSERT_LIBRARIES={P}/lib/lib{F}.1.dylib\n"})),
      ("C12 brew uses fails (rc=1) -> unverified", dict(formula=F, usesfail=True, uses="", expect="⚠")),
      ("C13 brew list fails (no file list) although it has a bin -> unverified", dict(formula="zzbin", bins=("zzb",), listfail=True, expect="⚠")),
      ("C14 hit inside a directory whose name contains .backup (the *.bak* filter must not drop it)", dict(formula=F, expect="🔴", home_files={
          ".claude/hooks/lib.backup-helpers/run.sh": f"#!/bin/sh\n{P}/opt/{F}/libexec/x\n"})),
      ("C15 autoremove mode positive control (plain name) + pipx cfg", dict(formula=F, mode="auto", expect="🔴", home_files={
          ".local/pipx/venvs/tool/pyvenv.cfg": f"home = {P}/opt/{F}/bin\n"})),
      ("C16 PIPX_HOME under ~/Library/Application Support/pipx", dict(formula="zzpython@3.99", bins=("python3.99",), expect="🔴", home_files={
          "Library/Application Support/pipx/venvs/tool/pyvenv.cfg": f"home = {P}/opt/zzpython@3.99/bin\n"})),
      ("C17 venv created via the brew link path: pyvenv.cfg home=/opt/homebrew/bin (not opt) -> keep", dict(formula="zzpython@3.99", bins=("python3.99",), expect="🟡", home_files={
          ".local/pipx/venvs/tool/pyvenv.cfg": f"home = {P}/bin\nexecutable = {P}/bin/python3.99\n"})),
    ]
    ran = bad = xf = 0
    for n, kw in cases:
        if sel and not any(n.startswith(s + " ") for s in sel): continue
        m = run_case(n, **kw); ran += 1
        if m == "FAIL": bad += 1
        if m in ("XFAIL", "XPASS"): xf += 1
    print(f"RESULT r1 ran={ran} bad={bad} xfail={xf}")
    sys.exit(1 if bad else 0)
