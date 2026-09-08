# ax — 5エージェント横断セッションピッカー

[![CI](https://github.com/kuwa72/ax/actions/workflows/ci.yml/badge.svg)](https://github.com/kuwa72/ax/actions)

[English version](README.md)

`claude` / `codex` / `agy` (antigravity-cli) / `opencode` / `devin` の
過去セッションを1つの fzf/JSON インターフェースで一覧・プレビュー・resume する。

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

## 設定ファイル (optional)

`~/.config/ax/config.toml` (または `$XDG_CONFIG_HOME/ax/config.toml`) に
TOML 形式で書く。存在しない場合は既定値が使われる。

```toml
[limits]
max_sessions = 300
preview_lines = 30

[limits.max_sessions]
claude = 100
agy = 50

[limits.preview_lines]
devin = 20

[providers]
disabled = ["agy"]

[fzf]
extra_args = ["--bind", "ctrl-a:toggle-preview"]
```

- `limits.max_sessions`: 一覧で読み込む最大セッション数。`--limit` で上書き可。
- `[limits.max_sessions]`: プロバイダ別の最大数。指定がないプロバイダはグローバル値を使う。
- `limits.preview_lines` / `[limits.preview_lines]`: `preview` で表示する直近ターン数。
- `providers.disabled`: 一覧・picker から除外するプロバイダ。`ax agents` では `disabled (config)` と表示される。
- `fzf.extra_args`: picker / grep の fzf 引数に追加するオプション (fzf 0.44 互換のみ)。

無効な値は stderr に警告を出し、既定値で続行する。設定ファイルの読み込み失敗時も同様。

## preview 形式

`ax preview` は `--- <agent> <id> (<n> msgs)` ヘッダに続き、チャット形式で
ターンを表示する。

- user / ai どちらも左寄せで読みやすい
- 各ターンは role 色のヘッダー + 左枠線 (`│`) で視覚的に区切る
- 各ロールヘッダにはタイムスタンプを表示
- 本文は単語区切りで端末幅 (最大 80 桁) に折り返され、元の改行は保持
- `[tool: exec]` / `[tools: name]` のような tool 行は非情報とみなし非表示
- role 色は環境・tty に応じて自動 ON (`AX_PREVIEW_COLOR=1` / `NO_COLOR=1`)
- 幅は `AX_PREVIEW_WIDTH` で固定可能

`--json` は機械用に `{agent, id, preview}` を返す（ANSI コードなし）。

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

## エージェントから使う (Agent Skill)

`ax` はエージェント自身から呼び出せる。Claude / Codex / OpenCode 等で Skill として導入するには：

```bash
# ax 実行ファイルを PATH に置く
export PATH="$HOME/ghq/github.com/kuwa72/ax:$PATH"

# Skill を全エージェントに導入
npx skills add kuwa72/ax --skill ax -g
```

エージェントの read-first ワークフロー：

1. `ax list --json` で候補を取得
2. `agent` / `title` / `cwd` / `epoch` を要約してユーザーに提示
3. 必要があれば `ax preview --json <agent> <id>` で本文確認
4. ユーザー承認後にのみ `ax resume <agent> <id>` を実行

JSON スキーマ詳細は `.agents/skills/ax/SKILL.md` を参照。

## データ源 (ローカルのみ)

- claude: `~/.claude/projects/*/*.jsonl`
- codex: `~/.codex/sessions/**/*.jsonl`
- agy: `~/.gemini/antigravity-cli/conversations/*.db` + `history.jsonl` + `brain/*/transcript.jsonl`
- opencode: `~/.local/share/opencode/opencode.db` (read-only, list cache in `~/.cache/ax/`)
- devin: `~/.local/share/devin/cli/sessions.db` + `transcripts/*.json` (read-only)
  - transcript が無い/薄い場合は `devin -r <id> --export` による取得を試行
  - ネットワーク失敗・`devin` 不在時は `sessions.db` の `message_nodes` 経由でローカル履歴を再構成し、最終的にタイトルでフォールバック

## 制限

- 本文検索は部分一致のみ (セマンティック検索・常駐インデックスはスコープ外)。
  JSONL は mmap で事前判定、opencode.db は `LIKE … LIMIT` で SQLite 側スキャン
- 1プロバイダ異常時は stderr 警告 + 他は継続
