# ax — 5エージェント横断セッションピッカー

[![CI](https://github.com/kuwa72/ax/actions/workflows/ci.yml/badge.svg)](https://github.com/kuwa72/ax/actions)

`claude` / `codex` / `agy` (antigravity-cli) / `opencode` / `devin` の
過去セッションを1つの fzf で一覧・プレビュー・resume する。

既存ツール (ccresume, ccsession, agf, cass, CCHV) はいずれも
5種すべて、特に `devin` をカバーしないため自作。stdlib のみ、fzf 0.44 で動作。

## 使い方

```sh
ax                         # fzf picker (enter=元のcwdでresume)
ax list [--json] [--agent NAME] [--limit N]
ax preview <agent> <id> [--json]
ax resume <agent> <id>
ax agents                  # 各ストアの検出状態
```

PATH に足す: `export PATH="$HOME/ghq/github.com/kuwa72/ax:$PATH"`

## resume 先

| agent | command |
|---|---|
| claude | `claude --resume <id>` |
| codex | `codex resume <id>` |
| agy | `agy --conversation <id>` |
| opencode | `opencode -s <id>` |
| devin | `devin -r <id>` |

## データ源 (ローカルのみ)

- claude: `~/.claude/projects/*/*.jsonl`
- codex: `~/.codex/sessions/**/*.jsonl`
- agy: `~/.gemini/antigravity-cli/conversations/*.db` + `history.jsonl` + `brain/*/transcript.jsonl`
- opencode: `~/.local/share/opencode/opencode.db` (read-only)
- devin: `~/.local/share/devin/cli/sessions.db` + `transcripts/*.json` (read-only)

## 制限 (MVP)

- 検索は fzf のファジーのみ (本文全文検索なし)
- devin preview はローカル transcript の user/agent メッセージのみ
- 1プロバイダ異常時は stderr 警告 + 他は継続
