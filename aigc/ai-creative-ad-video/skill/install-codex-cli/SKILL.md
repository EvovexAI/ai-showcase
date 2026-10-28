---
name: install-codex-cli
description: 在这台 macOS（Apple Silicon，无 Homebrew，WorkBuddy 托管 Node）上安装 OpenAI Codex CLI 的可复现流程，含两个已踩实的大坑（WorkBuddy 沙箱 broker 拦 npm 的 bin 软链 rename；安装被中断后 npm 缓存留下截断二进制导致 codex 启动即 SIGKILL 137）。当用户说「装一个 codex」「装 OpenAI 的 codex」「codex cli 装一下」「codex 用不了/启动就退出」时使用。
agent_created: true
version: "1.0.0"
---

# 在 macOS(arm64) + WorkBuddy 环境安装 OpenAI Codex CLI

## 环境事实（本机，2026-09 实测）
| 项 | 值 |
|---|---|
| 系统 | macOS 26.1 / arm64，**无 Homebrew** |
| Node | v22.22.2（WorkBuddy 托管，**不在用户普通终端的 PATH 里**） |
| 用户 PATH | `~/.local/bin` 已在 PATH（`~/.zshrc` 有 `. "$HOME/.local/bin/env"`） |
| 安装落点 | `~/.local/bin/codex` ＋ `~/.local/lib/node_modules/@openai/` |

> ⚠️ **不要用 `npm install -g`（默认 prefix = WorkBuddy 托管 node 目录）**——那里不在用户终端 PATH，且会随 node 版本升级被清掉。
> 也**不要为了装 codex 去装 Homebrew**（要 sudo + 大下载）。就用 `--prefix "$HOME/.local"`。

## 一、安装
```bash
npm install -g @openai/codex --prefix "$HOME/.local" --no-bin-links --no-audit --no-fund --prefer-online
```
- `--no-bin-links` **必须加**：见「坑 1」。
- 下载约 300 MB（含所有平台包），**耗时 2–3 分钟 → 必须用 `run_in_background: true`**。
- 版本用 `npm view @openai/codex version` 现查，不要写死。

## 二、★坑 1：WorkBuddy 沙箱拦 npm 的 bin 软链
不加 `--no-bin-links` 时，npm reify 收尾会报：
```
npm error code CODEBUDDY_BROKER_DENY
npm error ENOENT: ... rename '~/.local/bin/codex' -> '~/.local/bin/.codex-xxxx'
  at createBrokerPolicyError (.../node-brokerd-fs-shim.cjs)
```
实测 `~/.local/bin` **本身可写**（`touch`/`rm`/`chmod` 都通），被拦的只是 npm 那个 rename 动作。
→ 加 `--no-bin-links` 跳过它，然后**自己写启动器**（见第三步）。

## 三、★自写启动器（绕开 node 依赖，最稳）
```sh
#!/bin/sh
CODEX_BIN="$HOME/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex"
[ -x "$CODEX_BIN" ] || { echo "codex: binary not found" >&2; exit 127; }
exec "$CODEX_BIN" "$@"
```
写到 `~/.local/bin/codex`，然后 `chmod +x`。
为什么不直接软链 `bin/codex.js`：那是 JS 启动器，shebang 是 `#!/usr/bin/env node`，而**用户终端的 PATH 里没有 node**。直接 exec 原生二进制零依赖。

## 四、★坑 2：安装被中断 → 截断二进制 → 启动即 SIGKILL 137
第一次安装如果在下载/解包中途被 kill，`node_modules` 里会留下**残缺解包**（实测只剩 7 个文件里的 1 个，连 `package.json` 都没有），二进制被截断。症状：
- 跑 `codex --version` → **rc=137（SIGKILL）且无任何输出**
- `codesign -dv` → `code object is not signed at all`
- `codesign --force --sign -` → `main executable failed strict validation`（签不了，别浪费时间）

**判断标准（记死）**：正常完整的 darwin-arm64 二进制是 **≈222 MB 且已由 OpenAI 签名**
（`codesign -dv` 显示 `Identifier=codex` / `flags=0x10000(runtime)` / 有 Timestamp）。
若是 128 MB / 无签名 → **就是坏包，不要试图修，直接重装**：
```bash
rm -rf "$HOME/.local/lib/node_modules/@openai"
# 再跑第一步的安装命令
```
> 平台包在 registry 里的真名是 **`@openai/codex@<ver>-darwin-arm64`**（npm 别名，`npm view @openai/codex-darwin-arm64` 会 404，别被误导）。
> 完整性参考：该平台包 `fileCount: 7`（README.md / package.json / vendor/…/bin/codex / codex-code-mode-host / codex-path/rg / codex-resources/zsh/bin/zsh / codex-package.json）。

## 五、验收（四步全过才算装好）
```bash
zsh -l -c 'command -v codex && codex --version'   # → ~/.local/bin/codex + codex-cli <ver>
zsh -l -c 'codex --help'                          # → 子命令列表
zsh -l -c 'codex doctor'                          # → runtime/install/search/git 全 ✓
find ~/.local/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64 -type f | wc -l   # → 7
```

## 六、codex doctor 的正常未完成项（不是安装问题）
| 项 | 含义 | 怎么办 |
|---|---|---|
| `✗ auth` | 还没登录 | 用户自行 `codex login`（ChatGPT 账号）或设 `OPENAI_API_KEY` |
| `✗ reachability` / `⚠ websocket` | 连不上 `chatgpt.com` / `api.openai.com` | **国内需自备代理**；codex 是 Rust 程序，认 `HTTPS_PROXY`/`HTTPS_PROXY` 环境变量 → `export HTTPS_PROXY=http://127.0.0.1:<port>` |

> WorkBuddy 会话内的 `HTTPS_PROXY` 指向沙箱代理（白名单），**用它测不出用户真实网络**，别据此下结论。

## 七、收尾
- 报告落点 + `codex --version` 实测输出 + 需要用户自己做的两步（登录 / 代理）。
- 卸载：`rm -rf ~/.local/lib/node_modules/@openai ~/.local/bin/codex ~/.codex`
