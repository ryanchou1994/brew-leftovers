#!/usr/bin/env python3
"""Round 2: 61 adversarial cases (fake HOME + mock brew; only mktemp directories are created).
Also exports run_case() for script_extra.py and the holdout suite."""
import os, subprocess, tempfile, shutil, sys, time, plistlib, re, json

R = os.path.dirname(os.path.abspath(__file__))
T = os.path.dirname(R)
SCRIPT = os.environ.get("BREW_LEFTOVERS_BIN", os.path.join(os.path.dirname(T), "brew-leftovers"))
MOCK = os.path.join(T, "mockbin")
FIX = os.path.join(T, "fixtures")
CLASS = re.compile(r"^(🔴|🟡|🟢|⚪|⚠️) (in-use|unverified|keep|removable|not-installed|cask)\s")

def macho(*strs):
    body = b"".join(s.encode() + b"\x00" for s in strs)
    return b"\xcf\xfa\xed\xfe\x0c\x00\x00\x01" + b"\x00" * 64 + body + b"\x00" * 32

def run_case(name, formula, files_rel, home_files=None, prefix=None, arg=None, extra_path=os.path.join(FIX, "lsofok"),
             extra_env=None, cellar_name=None, linked=(), expect=None, xfail=False, mode="args", flags=(),
             onrequest=False, notab=False, casks=(), infofail=False, installed=True, quiet=False):
    """Returns the CompletedProcess. Prints one PASS/FAIL/XFAIL/XPASS block per case when `expect` is given."""
    home = os.path.realpath(tempfile.mkdtemp(prefix="bl2-home-"))
    st = os.path.realpath(tempfile.mkdtemp(prefix="bl2-state-"))
    tmpp = None
    try:
        if prefix == "SPACE":
            tmpp = os.path.realpath(tempfile.mkdtemp(prefix="bl2-pfx-"))
            P = os.path.join(tmpp, "my brew 前綴")
        elif prefix == "FAKE":
            tmpp = os.path.realpath(tempfile.mkdtemp(prefix="bl2-pfx-"))
            P = os.path.join(tmpp, "hb")
        else:
            P = "/opt/homebrew"
        cn = cellar_name or formula.split("/")[-1]
        os.makedirs(os.path.join(home, ".local", "log"), exist_ok=True)
        os.makedirs(os.path.join(st, "files")); os.makedirs(os.path.join(st, "uses"))
        a = arg or formula
        key = a.replace("/", "__")
        if installed: open(os.path.join(st, "installed"), "w").write(a + "\n")
        open(os.path.join(st, "prefix"), "w").write(P + "\n")
        base = f"{P}/Cellar/{cn}/1.0"
        flist = [f"{base}/INSTALL_RECEIPT.json"] + [f"{base}/{x}" for x in files_rel]
        open(os.path.join(st, "files", key), "w").write("\n".join(flist) + "\n")
        open(os.path.join(st, "uses", key), "w").write("")
        if mode == "auto": open(os.path.join(st, "autoremove"), "w").write(a + "\n")
        if onrequest: open(os.path.join(st, "onrequest"), "w").write(a + "\n")
        if notab: open(os.path.join(st, "notab"), "w").write("1")
        if infofail: open(os.path.join(st, "infofail"), "w").write("1")
        if casks: open(os.path.join(st, "casks"), "w").write("\n".join(casks) + "\n")
        if tmpp:
            for rel in files_rel:  # real Cellar files + PREFIX links, like `brew link` does
                cp = os.path.join(base, rel); os.makedirs(os.path.dirname(cp), exist_ok=True); open(cp, "w").write("x")
            for rel in linked:
                lp = os.path.join(P, rel); os.makedirs(os.path.dirname(lp), exist_ok=True)
                os.symlink(os.path.join(base, rel), lp)
            os.makedirs(os.path.join(P, "opt"), exist_ok=True); os.symlink(f"../Cellar/{cn}/1.0", os.path.join(P, "opt", cn))
        for rel, spec in (home_files or {}).items():
            spec = spec(P, home) if callable(spec) else spec
            p = rel if rel.startswith("/") else os.path.join(home, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if isinstance(spec, tuple) and spec[0] == "symlink":
                os.symlink(spec[1].replace("$HOME", home), p)
            elif isinstance(spec, tuple) and spec[0] == "exec":
                open(p, "w").write(spec[1]); os.chmod(p, 0o755)
            elif isinstance(spec, bytes):
                open(p, "wb").write(spec)
            else:
                open(p, "w").write(spec)
        env = {"HOME": home, "PATH": (extra_path + ":" if extra_path else "") + MOCK + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
               "BREW_LEFTOVERS_BREW": os.path.join(MOCK, "brew"), "MOCK_STATE": st, "LANG": "en_US.UTF-8",
               "BREW_LEFTOVERS_SYSTEM_ROOTS": ""}
        if prefix: env["BREW_LEFTOVERS_PREFIX"] = P
        env.update(extra_env or {})
        t = time.time()
        argv = ["/bin/bash", SCRIPT] + list(flags) + ([a] if mode == "args" else [])
        r = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=300)
        dt = time.time() - t
        r.home, r.prefix, r.state = home, P, st
        r.executed_tab = os.path.exists(os.path.join(st, "executed_tab"))
        r.unexpected = open(os.path.join(st, "unexpected")).read() if os.path.exists(os.path.join(st, "unexpected")) else ""
        cls = [l for l in r.stdout.splitlines() if CLASS.match(l)]
        r.cls = cls
        if expect is not None:
            ok = bool(cls) and cls[0].startswith(expect)
            r.mark = ("XPASS" if ok else "XFAIL") if xfail else ("PASS" if ok else "FAIL")
            if not quiet:
                print(f"### {name}\n    [{r.mark}] expect={expect} rc={r.returncode} {dt:.1f}s -> {cls[0] if cls else '(no class line)'}")
                for l in r.stdout.splitlines():
                    if l.startswith("     · "): print("    " + l.strip().replace(home, "~").replace(tmpp or "\0", "$T"))
                if r.stderr.strip(): print("    stderr:", r.stderr.strip()[:400].replace(home, "~"))
                if r.unexpected: print("    UNEXPECTED brew calls:", r.unexpected.strip())
        return r
    finally:
        for d in (home, st, tmpp):
            if d: shutil.rmtree(d, ignore_errors=True)

L = "zzfakelib"
LIBF = [f"lib/lib{L}.1.dylib", f"lib/lib{L}.dylib", f"include/{L}.h"]
OPTLIB = lambda P: f"{P}/opt/{L}/lib/lib{L}.1.dylib"

CASES = [
  # -- controls --
  ("R00 positive control: ~/.zshrc has the opt path -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".zshrc": lambda P, h: f'export DYLD_LIBRARY_PATH="{P}/opt/{L}/lib"\n'})),
  ("R00b negative control: library nobody uses -> removable", dict(formula=L, files_rel=LIBF, expect="🟢")),
  # -- command detection --
  ("R01a formula with only an sbin command (mtr/dnsmasq style), nobody references it -> keep", dict(formula="zzsbin",
      files_rel=["sbin/zzd"], prefix="FAKE", linked=["sbin/zzd"], expect="🟡")),
  ("R01b sbin command used by a LaunchAgent ProgramArguments PREFIX/sbin/zzd -> in-use", dict(formula="zzsbin",
      files_rel=["sbin/zzd"], prefix="FAKE", linked=["sbin/zzd"], expect="🔴",
      home_files={"Library/LaunchAgents/com.me.zzd.plist": lambda P, h: plistlib.dumps({"Label": "com.me.zzd",
          "ProgramArguments": [f"{P}/sbin/zzd", "--keep-in-foreground"], "RunAtLoad": True}).decode()})),
  ("R01c linked bin: LaunchAgent uses PREFIX/bin/zzc -> in-use", dict(formula="zzcmd",
      files_rel=["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], expect="🔴",
      home_files={"Library/LaunchAgents/com.me.zzc.plist": lambda P, h: plistlib.dumps({"Label": "com.me.zzc",
          "ProgramArguments": [f"{P}/bin/zzc", "serve"]}).decode()})),
  ("R01d linked bin: LaunchAgent only names the command zzc (via PATH) -> keep is acceptable", dict(formula="zzcmd",
      files_rel=["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], expect="🟡",
      home_files={"Library/LaunchAgents/com.me.zzc.plist": plistlib.dumps({"Label": "com.me.zzc",
          "ProgramArguments": ["zzc", "serve"], "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/bin"}}).decode()})),
  # -- brew link paths (PREFIX/share, etc, lib subdirs, .so) --
  ("R02 zsh plugin (share/ only, like zsh-autosuggestions): ~/.zshrc sources PREFIX/share/... -> in-use", dict(formula="zzplug",
      files_rel=["share/zzplug/zzplug.zsh"], expect="🔴",
      home_files={".zshrc": "source /opt/homebrew/share/zzplug/zzplug.zsh\n"})),
  ("R02b bash-completion style: ~/.bash_profile reads PREFIX/etc/profile.d/zzcomp.sh -> in-use", dict(formula="zzcomp",
      files_rel=["etc/profile.d/zzcomp.sh"], expect="🔴",
      home_files={".bash_profile": '[[ -r "/opt/homebrew/etc/profile.d/zzcomp.sh" ]] && . "/opt/homebrew/etc/profile.d/zzcomp.sh"\n'})),
  ("R03a ~/.zshrc uses $(brew --prefix)/opt/<f> -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".zshrc": f'export DYLD_LIBRARY_PATH="$(brew --prefix)/opt/{L}/lib"\n'})),
  ("R03b ~/.zshrc uses $HOMEBREW_PREFIX/opt/<f> -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".zshrc": f'export LIBRARY_PATH="$HOMEBREW_PREFIX/opt/{L}/lib"\n'})),
  ("R03c nvm style (no bin, only libexec and a root .sh): ~/.zshrc has $(brew --prefix zznvm)/nvm.sh -> in-use", dict(formula="zznvm",
      files_rel=["nvm.sh", "libexec/nvm-exec"], expect="🔴",
      home_files={".zshrc": 'export NVM_DIR="$HOME/.nvm"\n[ -s "$(brew --prefix zznvm)/nvm.sh" ] && . "$(brew --prefix zznvm)/nvm.sh"\n'})),
  ("R04 lib in a subdirectory (lib/engines-3/zz.dylib, OpenSSL engine style) referenced via link path from ~/.config -> in-use", dict(formula=L,
      files_rel=LIBF + ["lib/engines-3/zzpkcs11.dylib"], expect="🔴",
      home_files={".config/openssl/openssl.cnf": "[pkcs11]\ndynamic_path = /opt/homebrew/lib/engines-3/zzpkcs11.dylib\n"})),
  ("R04b .so in lib/ (PKCS11 module style) referenced via link path from ~/.config -> in-use", dict(formula=L,
      files_rel=LIBF + ["lib/zz-pkcs11.so"], expect="🔴",
      home_files={".config/zz/x.conf": "module: /opt/homebrew/lib/zz-pkcs11.so\n"})),
  ("R04c ca-certificates style (share/ data only): ~/.zshrc SSL_CERT_FILE=PREFIX/share/... -> in-use", dict(formula="zzca",
      files_rel=["share/zzca/cacert.pem"], expect="🔴",
      home_files={".zshrc": "export SSL_CERT_FILE=/opt/homebrew/share/zzca/cacert.pem\n"})),
  # -- config files that were once missed --
  ("R05 ~/.gitconfig has the opt path -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".gitconfig": f"[http]\n\tsslCAInfo = /opt/homebrew/opt/{L}/share/cacert.pem\n"})),
  ("R05b ~/.gitconfig core.pager = PREFIX/bin/zzc (linked bin) -> in-use", dict(formula="zzcmd",
      files_rel=["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], expect="🔴",
      home_files={".gitconfig": lambda P, h: f"[core]\n\tpager = {P}/bin/zzc\n"})),
  ("R06 ~/.ssh/config PKCS11Provider points at the opt dylib -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".ssh/config": f"Host x\n  PKCS11Provider /opt/homebrew/opt/{L}/lib/lib{L}.dylib\n"})),
  ("R06b ~/.ssh/config ProxyCommand PREFIX/bin/zzc (cloudflared style) -> in-use", dict(formula="zzcmd",
      files_rel=["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], expect="🔴",
      home_files={".ssh/config": lambda P, h: f"Host t\n  ProxyCommand {P}/bin/zzc access ssh --hostname %h\n"})),
  ("R07 ~/.npmrc cafile points at opt -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".npmrc": f"cafile=/opt/homebrew/opt/{L}/share/cacert.pem\n"})),
  ("R07b ~/Library/Application Support/pip/pip.conf points at opt -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Library/Application Support/pip/pip.conf": f"[global]\ncert = /opt/homebrew/opt/{L}/share/cacert.pem\n"})),
  ("R07c ~/.pip/pip.conf points at opt -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".pip/pip.conf": f"[global]\ncert = /opt/homebrew/opt/{L}/share/cacert.pem\n"})),
  ("R07d ~/.bundle/config (Ruby gem build flags) points at opt -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".bundle/config": f'---\nBUNDLE_BUILD__PSYCH: "--with-libyaml-dir=/opt/homebrew/opt/{L}"\n'})),
  ("R08 Cursor settings.json has an opt include path -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Library/Application Support/Cursor/User/settings.json": '{"C_Cpp.default.includePath":["' + f"/opt/homebrew/opt/{L}/include" + '"]}\n'})),
  ("R08b VS Code profile settings (User/profiles/<id>/settings.json) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Library/Application Support/Code/User/profiles/abc/settings.json": '{"x":"' + f"/opt/homebrew/opt/{L}/lib" + '"}\n'})),
  ("R09 Colima/Lima VM config (~/.colima, ~/.lima) points at opt -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".lima/default/lima.yaml": f"env:\n  X: /opt/homebrew/opt/{L}/lib\n"})),
  ("R10 Automator quick action ~/Library/Services/x.workflow/Contents/document.wflow -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Library/Services/x.workflow/Contents/document.wflow": plistlib.dumps({"actions": [{"COMMAND_STRING": f"/opt/homebrew/opt/{L}/libexec/x \"$@\""}]}).decode()})),
  ("R11 LaunchAgent binary plist whose sh -c string contains non-ASCII (stored as UTF-16) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Library/LaunchAgents/com.me.x.plist": plistlib.dumps({"Label": "com.me.x",
          "ProgramArguments": ["/bin/sh", "-c", f"/opt/homebrew/opt/{L}/libexec/x >> ~/日誌/x.log 2>&1"]}, fmt=plistlib.FMT_BINARY)})),
  ("R12 ~/.zshrc is a symlink (dotfiles manager) to ~/dotfiles/zshrc -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"dotfiles/zshrc": f'export DYLD_LIBRARY_PATH="/opt/homebrew/opt/{L}/lib"\n', ".zshrc": ("symlink", "$HOME/dotfiles/zshrc")})),
  ("R12b plist in ~/Library/LaunchAgents is a symlink -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"dotfiles/com.me.x.plist": plistlib.dumps({"Label": "com.me.x", "ProgramArguments": [f"/opt/homebrew/opt/{L}/libexec/x"]}).decode(),
                  "Library/LaunchAgents/com.me.x.plist": ("symlink", "$HOME/dotfiles/com.me.x.plist")})),
  ("R12c ~/.config itself is a symlink -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"dotfiles/config/zz/a.conf": f"p=/opt/homebrew/opt/{L}/lib\n", ".config": ("symlink", "$HOME/dotfiles/config")})),
  # -- project folders --
  ("R13 project script without extension (~/Desktop/proj/bin/deploy) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/bin/deploy": f"#!/bin/bash\nexport DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n"})),
  ("R13b project .vscode/settings.json -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/.vscode/settings.json": '{"x":"' + f"/opt/homebrew/opt/{L}/include" + '"}\n'})),
  ("R13c project package.json scripts -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/package.json": '{"scripts":{"build":"CFLAGS=-I' + f"/opt/homebrew/opt/{L}/include" + ' node-gyp rebuild"}}\n'})),
  ("R13d project CMakeLists.txt (build.rs / .cargo/config.toml / cgo comments are the same family) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/CMakeLists.txt": f"link_directories(/opt/homebrew/opt/{L}/lib)\n"})),
  ("R13e project .claude/settings.json hook command -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/.claude/settings.json": '{"hooks":{"x":"' + f"/opt/homebrew/opt/{L}/libexec/x" + '"}}\n'})),
  ("R13f project under ~/Developer (Apple convention) instead of Desktop/Documents -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Developer/proj/run.sh": f"export DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n"})),
  ("R14 path with spaces and non-ASCII: ~/Desktop/我的 專案/run.sh -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/我的 專案/run.sh": f"export DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n"})),
  ("R14b path with spaces and non-ASCII: ~/Documents/新 專案/.venv/pyvenv.cfg bound to it -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Documents/新 專案/.venv/pyvenv.cfg": f"home = /opt/homebrew/opt/{L}/bin\n"})),
  ("R14c path with spaces and non-ASCII: ~/Desktop/新 專案/ext.so (Mach-O) links it -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/新 專案/ext.so": lambda P, h: macho(OPTLIB(P))})),
  # -- language runtimes / other compiled artefacts --
  ("R15 rbenv-built Ruby native extension (~/.rbenv/versions/.../psych.bundle) links it -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".rbenv/versions/3.3.0/lib/ruby/3.3.0/arm64-darwin24/psych.bundle": lambda P, h: macho(OPTLIB(P))})),
  ("R15b pyenv-built Python (~/.pyenv/.../readline.cpython-311-darwin.so) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".pyenv/versions/3.11.9/lib/python3.11/lib-dynload/readline.cpython-311-darwin.so": lambda P, h: macho(OPTLIB(P))})),
  ("R15c mise/asdf runtime (~/.local/share/mise/installs/...) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".local/share/mise/installs/ruby/3.3/lib/ruby/3.3.0/arm64-darwin24/openssl.bundle": lambda P, h: macho(OPTLIB(P))})),
  ("R15d nvm global npm native module (~/.nvm/.../canvas.node) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".nvm/versions/node/v20.0.0/lib/node_modules/canvas/build/Release/canvas.node": lambda P, h: macho(OPTLIB(P))})),
  ("R15e gem native extension under ~/.gem -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".gem/ruby/3.3.0/extensions/arm64-darwin-24/3.3.0/nokogiri-1.16/nokogiri.bundle": lambda P, h: macho(OPTLIB(P))})),
  ("R15f npm global native module inside the brew prefix (PREFIX/lib/node_modules/.../x.node) -> in-use", dict(formula=L, files_rel=LIBF,
      prefix="FAKE", expect="🔴", home_files={"__P__": None})),
  ("R15g pip package inside brew python (PREFIX/lib/python3.14/site-packages/x.so) -> in-use", dict(formula=L, files_rel=LIBF,
      prefix="FAKE", expect="🔴", home_files={"__P2__": None})),
  ("R16 Mach-O using @rpath + LC_RPATH=PREFIX/lib (no absolute opt path) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/app": macho("/opt/homebrew/lib", f"@rpath/lib{L}.1.dylib")})),
  ("R17 >1MB Mach-O in ~/.local/bin with a dotted version in its name (mytool-1.2) links it -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={".local/bin/mytool-1.2": lambda P, h: macho(OPTLIB(P)) + b"\x00" * (2 * 1024 * 1024)})),
  ("R17b project executable with a dotted version in its name (Desktop/proj/tool-v2.1) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/tool-v2.1": lambda P, h: macho(OPTLIB(P))})),
  # -- argument name vs real name --
  ("R18 queried by alias/old name: argument zzalias, Cellar is zzreal, pipx bound to opt/zzreal -> in-use", dict(formula="zzalias",
      cellar_name="zzreal", files_rel=["lib/libzzreal.dylib"], expect="🔴",
      home_files={".local/pipx/venvs/t/pyvenv.cfg": "home = /opt/homebrew/opt/zzreal/bin\n"})),
  # -- failure paths --
  ("R19 python3 for the binary scan is broken (exit 1, e.g. no CLT) + a .so links it -> unverified or in-use, never removable", dict(formula=L, files_rel=LIBF, expect="⚠",
      extra_path=os.path.join(FIX, "pyfail"),
      home_files={"Desktop/proj/ext.so": lambda P, h: macho(OPTLIB(P))})),
  ("R20 config-file text scan times out (slow grep -r -o; TIMEOUT=3, lsof fine) + ~/.zshrc references it -> unverified, never removable", dict(formula=L, files_rel=LIBF, expect="⚠",
      extra_path=os.path.join(FIX, "slowgrep_text"), extra_env={"BREW_LEFTOVERS_SCAN_TIMEOUT": "3"},
      home_files={".zshrc": f'export DYLD_LIBRARY_PATH="/opt/homebrew/opt/{L}/lib"\n'})),
  ("R20b project-folder scan times out (slow grep -r -I; TIMEOUT=3, lsof fine) + ~/Desktop/proj/run.sh references it -> unverified, never removable", dict(formula=L, files_rel=LIBF, expect="⚠",
      extra_path=os.path.join(FIX, "slowgrep_proj"), extra_env={"BREW_LEFTOVERS_SCAN_TIMEOUT": "3"},
      home_files={"Desktop/proj/run.sh": f"export DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n"})),
  ("R20c control: same as R20b without the timeout -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/run.sh": f"export DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n"})),
  ("R13g project script without extension but executable -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
      home_files={"Desktop/proj/bin/run": ("exec", f"#!/bin/bash\nexport DYLD_LIBRARY_PATH=/opt/homebrew/opt/{L}/lib\n")})),
  ("R21 lsof fails (exit 1, no output) -> unverified (at least a warning)", dict(formula=L, files_rel=LIBF, expect="⚠",
      extra_path=os.path.join(FIX, "lsoffail"))),
  # -- PREFIX with spaces --
  ("R22a PREFIX with spaces and non-ASCII: pipx cfg bound to it -> in-use", dict(formula=L, files_rel=LIBF, prefix="SPACE", expect="🔴",
      home_files={".local/pipx/venvs/t/pyvenv.cfg": lambda P, h: f"home = {P}/opt/{L}/bin\n"})),
  ("R22b PREFIX with spaces and non-ASCII: ~/.local/bin symlink into Cellar -> in-use", dict(formula=L, files_rel=LIBF, prefix="SPACE", expect="🔴",
      home_files={".local/bin/zz": lambda P, h: ("symlink", f"{P}/Cellar/{L}/1.0/lib/lib{L}.dylib")})),
  ("R22c PREFIX with spaces and non-ASCII: ~/.cargo/bin Mach-O links it -> in-use", dict(formula=L, files_rel=LIBF, prefix="SPACE", expect="🔴",
      home_files={".cargo/bin/rt": lambda P, h: macho(OPTLIB(P))})),
  ("R22d PREFIX with spaces and non-ASCII: linked bin, ~/.zshrc uses PREFIX/bin/zzc -> in-use", dict(formula="zzcmd", files_rel=["bin/zzc"],
      prefix="SPACE", linked=["bin/zzc"], expect="🔴",
      home_files={".zshrc": lambda P, h: f'alias z="{P}/bin/zzc"\n'})),
  ("R22e PREFIX with spaces: negative control -> removable", dict(formula=L, files_rel=LIBF, prefix="SPACE", expect="🟢")),
]

def fix_prefix_cases(kw):
    # R15f/R15g place files inside the fake PREFIX itself (not HOME)
    hf = kw.get("home_files") or {}
    absf = None
    if "__P__" in hf:
        absf = lambda P: {f"{P}/lib/node_modules/canvas/build/Release/canvas.node": macho(OPTLIB(P))}
    if "__P2__" in hf:
        absf = lambda P: {f"{P}/lib/python3.14/site-packages/lxml/etree.cpython-314-darwin.so": macho(OPTLIB(P))}
    if absf:
        def mk(P, h, absf=absf):
            for p, data in absf(P).items():
                os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
            return "placeholder\n"
        kw["home_files"] = {".r2-placeholder": mk}
    return kw

def run_all(cases, label, sel=()):
    ran = bad = xf = 0
    for n, kw in cases:
        if sel and not any(n.startswith(s + " ") for s in sel): continue
        r = run_case(n, **fix_prefix_cases(dict(kw))); ran += 1
        if r.mark == "FAIL": bad += 1
        if r.mark in ("XFAIL", "XPASS"): xf += 1
    print(f"RESULT {label} ran={ran} bad={bad} xfail={xf}")
    return bad

if __name__ == "__main__":
    sys.exit(1 if run_all(CASES, "r2", sys.argv[1:]) else 0)
