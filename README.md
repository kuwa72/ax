# ax — 5エージェント横断セッションピッカー

[![CI](https://github.com/kuwa72/ax/actions/workflows/ci.yml/badge.svg)](https://github.com/kuwa72/ax/actions)

`claude` / `codex` / `agy` (antigravity-cli) / `opencode` / `devin` の
過去セッションを1つの fzf で一覧・プレビュー・resume する。

既存ツール (ccresume, ccsession, agf, cass, CCHV) はいずれも
5種すべて、特に `devin` をカバーしないため自作。stdlib のみ、fzf 0.44 で動作。

## 使い方

```sh
ax                         # fzf picker (enter=resume ctrl-g=本文検索)
ax list [--json] [--agent NAME] [--limit N] [--no-cache] [--grep QUERY]
ax grep <query>            # 5エージェント本文横断検索 -> fzf -> resume
ax preview <agent> <id> [--json]
ax resume <agent> <id>
ax agents                  # 各ストアの検出状態・サイズ・件数
```

`--grep` は会話本文のみを部分一致 (ASCII 大小文字無視) で検索し、
ヒット行を `title` 列に `▸ <snippet>` として付記する。picker 内では
`ctrl-g` で本文検索に切替、検索結果画面では `ctrl-g` で再検索・
`ctrl-a` で全一覧に戻る (fzf 0.44 互換の `become` 使用)。

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
- opencode: `~/.local/share/opencode/opencode.db` (read-only, list cache in `~/.cache/ax/`)
- devin: `~/.local/share/devin/cli/sessions.db` + `transcripts/*.json` (read-only)

## 制限 (MVP)

- 本文検索は部分一致のみ (セマンティック検索・常駐インデックスはスコープ外)。
  JSONL は mmap で事前判定、opencode.db は `LIKE … LIMIT` で SQLite 側スキャン
- devin preview はローカル transcript の user/agent メッセージのみ
- 1プロバイダ異常時は stderr 警告 + 他は継続
