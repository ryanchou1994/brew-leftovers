# brew-leftovers

刪 Homebrew 工具之前（或之後），查「**brew 以外**還有誰在用」這個 formula。只查不刪，永遠不會動你的任何東西。也不連網：工具本身不連線、不上傳任何東西，只讀這台 Mac 上的檔案、只跑本機的 `brew` 查詢。

`brew uninstall` 會順手把「只為了被刪工具而裝的附屬工具」一起刪掉。Homebrew 的依賴圖對 Homebrew 自己很準，但看不見 Mac 上其他的使用者：綁在 Homebrew Python 上的 pipx 工具與專案虛擬環境、launchd 排程、shell 與各種工具的設定檔、寫死 `/opt/homebrew/opt/...` 的腳本、連結到 Homebrew 程式庫的編譯好的 App、git hook。`brew uses --installed` 回答的是「哪些 *formula* 依賴它」；`brew-leftovers` 回答的是「*其他* 還有誰在用」。

這個工具來自兩次真實事故：刪一個命令列工具時 `python@3.12` 被連帶刪掉，一個 pipx 工具和兩個專案虛擬環境壞了七週才被發現；刪另一個工具時 `ripgrep` 被連帶刪掉，而有些 App 會在執行時直接呼叫 `rg`。

## 它做什麼

不帶參數＝查 `brew autoremove --dry-run` 會刪的全部；帶名字＝查指定的 formula，這正是 `brew uninstall 某工具` **之前**該做的事：

```
brew leftovers                      # 查所有遺留
brew leftovers python@3.14 ripgrep  # 刪之前先查這兩個
```

輸出範例（英文；用測試夾具實跑的逐字輸出，mock `brew`，假家目錄顯示為 `/Users/me`）：

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

### 六種判定

每一行開頭都是固定的英文標籤，`--json` 用同一組字串。

| 標籤 | 意思 | 怎麼做 |
|------|------|--------|
| `in-use` | 找到 Homebrew 以外的使用者，證據列在下面 | 保留 |
| `unverified` | 某項 brew 查詢或掃描失敗、逾時，沒人能替它擔保 | 保留 |
| `keep` | 掃描範圍內沒找到使用者，但它提供指令或資料檔（shell 外掛、補完、憑證、設定），程式可能執行當下才用 | 預設保留 |
| `removable` | 只有程式庫，掃描範圍內沒人用 | 可以考慮刪，由你確認 |
| `not-installed` | Homebrew 沒有這個名字 | 無 |
| `cask` | 這是 App，本工具只查命令列 formula | 保留 |

偏向保留是刻意的：「證明沒人用」做不到，所以所有疑點一律判保留。刪錯了，`brew install <名字>` 就裝回來。

### 它看哪裡

| 證據種類 | 位置 |
|----------|------|
| `brew-dependents` | `brew uses --installed` |
| `python-env` | pipx、`~/.virtualenvs`、poetry／uv 快取、pyenv、pre-commit 快取與專案資料夾裡的 `pyvenv.cfg`，其 `home` 指向該 formula |
| `config-file` | `~/.local/bin` 腳本、shell 啟動檔、`~/.config`、git／ssh／npm／pip／bundler／cargo／docker／colima／lima 設定、VS Code 系列設定、Claude Code 與 Codex 設定、`/etc/paths*` |
| `git-hook` | `<專案>/.git/hooks/*` 與全域 `core.hooksPath` 目錄（pre-commit 會把安裝時的 Python 絕對路徑寫死在 hook 裡） |
| `launchd` | `~/Library/LaunchAgents`、`/Library/LaunchAgents`、`/Library/LaunchDaemons`、Automator 工作流程；二進位 plist 先轉換再比對 |
| `crontab` | 你的 crontab |
| `symlink` | `~/.local`、`~/bin`、`~/.config`、LaunchAgents 與家目錄 dotfiles 底下指進 Homebrew 的捷徑 |
| `project-file` | 專案資料夾裡會被執行或被讀的檔案（`.sh`、`.py`、`Makefile`、`Dockerfile`、`CMakeLists.txt`、`package.json` scripts……），含沒有副檔名的腳本 |
| `binary` | 連結到該 formula 的 Mach-O 執行檔與程式庫：`/Applications`、`~/Applications`、`~/.local/bin`、`~/.cargo/bin`、`~/go/bin`、各語言環境管理工具（rbenv、pyenv、mise/asdf、nvm、volta、bun、gem）、虛擬環境的 site-packages、`@rpath` 參照 |
| `process`、`open-file` | 執行中的程序與 `lsof` |

專案資料夾預設是 `~/Desktop`、`~/Documents`、`~/Developer`、`~/Projects`、`~/code`、`~/src`（存在的才掃）。只印檔名，永遠不印檔案內容。

另外會列出**已經壞掉的 Python 環境**：綁的 Homebrew Python 已經不在的虛擬環境，正是這個工具要防的那種損害。

## 安裝

需要：macOS、Homebrew、macOS 命令列工具附的 `python3`（編譯產物掃描與 `--json` 用），以及提供 `gtimeout` 的 `coreutils`（`brew install coreutils`）。沒有 `timeout`／`gtimeout` 時掃描不會被中斷，而且工具會把「沒有逾時保護」當成警告：凡是沒被證明「有人在用」的 formula 都會變成「無法確認」，永遠不會出現「可刪」。

```
git clone https://github.com/ryanchou1994/brew-leftovers.git
ln -s "$PWD/brew-leftovers/brew-leftovers" ~/.local/bin/brew-leftovers   # 任何在 PATH 上的目錄都行
brew leftovers --version
```

Homebrew 會把 `PATH` 上任何叫 `brew-<名字>` 的可執行檔當成 `brew <名字>` 來跑，所以放上 PATH 之後 `brew leftovers` 和 `brew-leftovers` 都能用；`brew help leftovers` 會印簡短說明。

## 把迴圈關起來：登記「我要留」

判了 `in-use` 不會改變 Homebrew 自己的帳本：在 brew 眼裡它仍是「附屬安裝」，下次 `brew autoremove` 照樣列它，在沒設 `HOMEBREW_NO_AUTOREMOVE=1` 的機器上手動 `brew autoremove` 也照樣刪它。Homebrew 的正門是：

```
brew tab --installed-on-request <formula>
```

`brew-leftovers` 會把這行命令填好印出來——`in-use` 的一行，`keep` 的另外一行（明確標示「如果你決定保留」）。它只印、不執行。（`brew tab` 自 Homebrew 4.3.6 起才有；舊版就不印這兩行。）

建議搭配的設定，讓 `brew uninstall`、`brew upgrade`、`brew cleanup` 不再自己連帶刪附屬工具：

```
echo 'HOMEBREW_NO_AUTOREMOVE=1' >> "$(brew --prefix)/etc/homebrew/brew.env"
```

這個檔是 `brew` 自己讀的，launchd 排程和非互動 shell 也吃得到。注意手動下 `brew autoremove` 時這個設定不生效——那正是 `brew leftovers` 的用途。

## 機器可讀輸出

```
brew leftovers --json [<formula> ...]
```

印一個 JSON 物件（`schema_version` 1）。加欄位不升版；改語意或刪欄位才升版。欄位說明與範例見英文版 [README.md](README.md) 的「Machine-readable output」節。證據清單的上限與文字輸出相同：多數種類最多六筆，`symlink` 四筆、`process` 三筆；`python-env`、`launchd`、`brew-dependents` 不設上限（`crontab` 與 `open-file` 固定只有一筆）。退出碼：跑完就是 0（不論判定），跑不起來才是 2（找不到 brew、參數錯、不是 macOS、`--json` 沒有 python3）。

## 搭配 AI 寫程式助手

助手很會 `brew uninstall`，很不會注意到還有什麼一起不見了。兩個做法有效：

1. 叫助手在任何 `brew uninstall <名字>` 之前先跑 `brew leftovers <名字>`、之後跑 `brew leftovers --json`，而且 `removable` 以外的一律當「保留」。固定的英文標籤與 `--json` 就是為了讓它不用讀 emoji。
2. 用 Claude Code 的話，可以加一個對 `Bash` 的 `PreToolUse` hook 提醒它；最小範例見英文版 [README.md](README.md)。

## 限制

- **只支援 macOS。** 它依賴 `plutil`、BSD `stat`、`lsof` 與 Mach-O 判讀；Linuxbrew 需要另寫 ELF 判讀和不同的目錄配置，目前沒有計畫。
- **它永遠不刪東西。** 輸出裡那行 `brew uninstall` 是給你決定之後自己貼的。
- **「沒找到使用者」只代表「掃描範圍內沒有」。** 其他使用者帳號、外接碟、專案根目錄以外的雲端同步資料夾、別台機器都不在範圍內；而且執行時靠名字呼叫指令的程式在任何檔案裡都看不到痕跡。這就是為什麼有指令的 formula 判 `keep` 而不是 `removable`。
- **偏向保留。** 指令名是另一個工具名字的前綴（`zzc` 與 `zzc-helper`）會誤判成 `in-use`，這是接受的：往安全的方向錯。
- **掃描要時間。** 通常幾分鐘，專案資料夾大的話會更久；每組掃描有逾時（`BREW_LEFTOVERS_SCAN_TIMEOUT`，預設 240 秒），逾時會把判定變成 `unverified`，絕不會變成 `removable`。

環境變數：`BREW_LEFTOVERS_PROJECT_ROOTS`（冒號分隔的專案資料夾）、`BREW_LEFTOVERS_SYSTEM_ROOTS`（預設 `/Applications:/Library/LaunchAgents:/Library/LaunchDaemons`；空字串＝不掃）、`BREW_LEFTOVERS_EXTRA_ROOTS`（額外要掃的資料夾，文字與編譯產物都掃）、`BREW_LEFTOVERS_SCAN_TIMEOUT`。

## 測試

```
bash tests/run.sh
```

116 個案例全部在假的 `HOME` 裡用 mock `brew` 與 mock `lsof` 跑，不會碰你的 Homebrew。內容包括本腳本私有版本時期的兩輪對抗測試（設定檔藏在奇怪的地方、捷徑化的 dotfiles、含非 ASCII 字串的二進位 plist、含空白的 prefix、壞掉的 `python3`、逾時的掃描），加上為 1.0.0 新功能依規格盲出的 holdout 題。有兩題是預期失敗（`XFAIL`）：一個已知的往保留方向誤判，一個測試夾具的限制（另一題已涵蓋）。測試同樣需要 `coreutils`：沒有 `gtimeout` 時兩題逾時測試會失敗，其餘大多數判定也會變成「無法確認」。

## 授權

[MIT](LICENSE)。
