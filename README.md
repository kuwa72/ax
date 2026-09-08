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
ax rm <agent> <id> [--yes] [--hard]   # セッション削除 (devin/codex のみ)
ax rename <agent> <id> --name "..."   # 表示名の変更 (ax ローカル)
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

## 削除・リネーム

- `ax rm` は対象セッションが一覧に存在するか確認した上で、確認プロンプト
  (または `--yes`) を必須とする。非対話 stdin ではプロンプトが EOF で中断される。
  - devin → `devin rm --force <id>` (完全削除)
  - codex → `codex archive <id>` (既定はアーカイブ、`codex unarchive` で復元可)
    / `--hard` で `codex delete --force <id>` (完全削除)
  - claude / agy / opencode は未対応: `not supported` で終了コード非0。
    プロバイダのストア (ファイル/SQLite) には一切書き込まない。
- `ax rename` はプロバイダのストアを変更せず、ax 側の表示名エイリアスを
  `~/.local/share/ax/titles.json` に保存する。`--name ""` で解除。
  全プロバイダで利用可。一覧の title 列のみに反映される。

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
