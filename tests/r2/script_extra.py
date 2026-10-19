#!/usr/bin/env python3
"""Round 2 extras (R23-R26). R23 is a known, accepted over-match (errs towards keeping) and is marked xfail."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script_harness import run_all, LIBF, L, macho, OPTLIB
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
]
if __name__ == "__main__":
    sys.exit(1 if run_all(C, "extra", sys.argv[1:]) else 0)
