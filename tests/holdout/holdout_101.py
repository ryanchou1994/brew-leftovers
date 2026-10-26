#!/usr/bin/env python3
"""Holdout for 1.0.1 (unreadable files must give unverified, readable oddities must not): written by a reviewer who saw only a
one-paragraph description of the rule, never the code. Unlike holdout.py these were written after the fix, so they guard against
over-fitting, not against reading the spec wrong. Kept verbatim; a failure means the rule is fixed, never a special case."""
import sys, os, plistlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "r2"))
from script_harness import run_all, LIBF, L

C = [
 ("U1 a folder under ~/.config cannot be entered (mode 000) -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={".zshrc": 'export PATH="$HOME/bin:$PATH"\n', ".config/fish/conf.d/x.fish": "# nothing\n"},
     chmods=[(".config/fish/conf.d", 0)])),
 ("U2 a LaunchAgent plist is unreadable -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Library/LaunchAgents/com.zz.agent.plist": plistlib.dumps({"Label": "com.zz.agent", "ProgramArguments": ["/usr/bin/true"]}).decode()},
     chmods=[("Library/LaunchAgents/com.zz.agent.plist", 0)])),
 ("U3 a project .venv/pyvenv.cfg is found but unreadable -> unverified", dict(formula=L, files_rel=LIBF, expect="⚠️",
     home_files={"Desktop/proj/.venv/pyvenv.cfg": "home = /usr/bin\n"}, chmods=[("Desktop/proj/.venv/pyvenv.cfg", 0)])),
 ("R1 dangling symlink in a project (not a permission problem) -> removable", dict(formula=L, files_rel=LIBF, expect="🟢",
     home_files={"Desktop/proj/link_broken": ("symlink", "../nonexistent/target.sh"), "Desktop/proj/real.sh": ("exec", "#!/bin/sh\necho hi\n")})),
 ("R2 empty folders, spaces / CJK / punctuation in names, a 0-byte script -> removable", dict(formula=L, files_rel=LIBF, expect="🟢",
     home_files={"Documents/empty_dir/": None, "Documents/dir with spaces & 中文/備忘 (copy) #1.txt": "hello\n",
                 "Documents/empty.sh": "", ".config/empty/": None})),
 ("R3 non-Mach-O binary, truncated header, empty app bundle, self-referencing symlink -> removable", dict(formula=L, files_rel=LIBF, expect="🟢",
     home_files={".local/bin/tool.bin": b"\x7fELF" + bytes(range(64)), ".local/bin/tiny": b"\xca\xfe\xba",
                 "Applications/Foo.app/Contents/MacOS/": None, "Library/LaunchAgents/loop": ("symlink", ".")},
     chmods=[(".local/bin/tool.bin", 0o755), (".local/bin/tiny", 0o755)])),
]
if __name__ == "__main__":
    sys.exit(1 if run_all(C, "holdout101", sys.argv[1:]) else 0)
