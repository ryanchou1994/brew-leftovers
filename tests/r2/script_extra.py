#!/usr/bin/env python3
"""Round 2 extras (R23-R29). R23 is a known, accepted over-match (errs towards keeping) and is marked xfail.
R27-R29 (1.0.1): unreadable files and timed-out searches must end in unverified, never removable."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_harness import run_all, LIBF, L, macho, OPTLIB, FIX
C = [
 ("R23 command-name prefix collision: only ~/.zshrc mentions PREFIX/bin/zzc-helper (a different tool) -> ideally keep, not in-use (known over-match, accepted)",
     dict(formula="zzcmd", files_rel=["bin/zzc"], prefix="FAKE", linked=["bin/zzc"], expect="🟡", xfail=True,
          home_files={".zshrc": lambda P, h: f'alias zh="{P}/bin/zzc-helper"\n'})),
 ("R24 project symlink to a Cellar dylib (vendor/lib/libzz.dylib -> Cellar) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
     home_files={"Desktop/proj/vendor/libzz.dylib": ("symlink", f"/opt/homebrew/Cellar/{L}/1.0/lib/lib{L}.1.dylib")})),
 ("R25 ~/.local/bin symlink to the PREFIX/lib link path (not opt/Cellar) -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
     home_files={".local/bin/libzz.dylib": ("symlink", f"/opt/homebrew/lib/lib{L}.1.dylib")})),
 ("R26 ~/.local/bin symlink to a zsh plugin under PREFIX/share -> in-use", dict(formula="zzplug", files_rel=["share/zzplug/zzplug.zsh"], expect="🔴",
     home_files={".local/bin/zzplug.zsh": ("symlink", "/opt/homebrew/share/zzplug/zzplug.zsh")})),
 # -- 1.0.1: a scan that could not read something must not end in "removable" (each pair = readable control + unreadable/timed-out variant) --
 ("R27a control: readable ~/.config/tool/settings.conf names the opt path -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
     home_files={".config/tool/settings.conf": lambda P, h: f"lib = {OPTLIB(P)}\n"})),
 ("R27b same config file unreadable (grep error, not a timeout) -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={".config/tool/settings.conf": lambda P, h: f"lib = {OPTLIB(P)}\n"}, chmods=[(".config/tool/settings.conf", 0)])),
 ("R27c project script unreadable (project-folder grep error) -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Desktop/proj/run.sh": lambda P, h: f"export DYLD_LIBRARY_PATH={P}/opt/{L}/lib\n"}, chmods=[("Desktop/proj/run.sh", 0)])),
 ("R28a control: readable Mach-O in ~/Applications links the library -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
     home_files={"Applications/Fake.app/Contents/MacOS/Fake": lambda P, h: macho(OPTLIB(P))})),
 ("R28b same Mach-O unreadable (open() fails) -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Applications/Fake.app/Contents/MacOS/Fake": lambda P, h: macho(OPTLIB(P))},
     chmods=[("Applications/Fake.app/Contents/MacOS/Fake", 0)])),
 ("R28c folder holding the Mach-O unreadable (directory walk fails) -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Applications/Fake.app/Contents/MacOS/Fake": lambda P, h: macho(OPTLIB(P))},
     chmods=[("Applications/Fake.app/Contents/MacOS", 0)])),
 ("R29a control: extension-less ~/Desktop/proj/bin/deploy names the opt path -> in-use", dict(formula=L, files_rel=LIBF, expect="🔴",
     home_files={"Desktop/proj/bin/deploy": lambda P, h: f"#!/bin/sh\nexec {OPTLIB(P)}\n"})),
 ("R29b extension-less file search times out -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Desktop/proj/bin/deploy": lambda P, h: f"#!/bin/sh\nexec {OPTLIB(P)}\n"},
     extra_path=os.path.join(FIX, "slowfind_noext"), extra_env={"BREW_LEFTOVERS_SCAN_TIMEOUT": "3"})),
 ("R29c grep over extension-less files times out -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Desktop/proj/bin/deploy": lambda P, h: f"#!/bin/sh\nexec {OPTLIB(P)}\n"},
     extra_path=os.path.join(FIX, "slowgrep_noext"), extra_env={"BREW_LEFTOVERS_SCAN_TIMEOUT": "3"})),
 ("R29d extension-less script unreadable -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Desktop/proj/bin/deploy": lambda P, h: f"#!/bin/sh\nexec {OPTLIB(P)}\n"}, chmods=[("Desktop/proj/bin/deploy", 0)])),
]
if __name__ == "__main__":
    sys.exit(1 if run_all(C, "extra", sys.argv[1:]) else 0)
