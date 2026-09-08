---
name: ax
description: "Find, summarize, preview, and resume cross-agent sessions (claude / codex / agy / opencode / devin) using the ax CLI. Use when the user wants to search past sessions, pick a session to continue, or switch context across agents."
---

# ax — マルチエージェント横断セッションピッカー

`ax` は claude / codex / agy (antigravity-cli) / opencode / devin の過去セッションを1つの fzf/JSON インターフェースで扱う。

## インストール

```bash
# 1. ax 実行ファイルを PATH に置く
export PATH="$HOME/ghq/github.com/kuwa72/ax:$PATH"
# または任意のパスに ax をコピーして PATH を通す

# 2. Skill を全エージェントに導入
npx skills add kuwa72/ax --skill ax -g
```

## いつ使うか

- 過去の作業セッションを探したい
- どのエージェントで何をやったか横断検索したい
- ユーザーに再開候補を提示して承認を得たい
- 他のエージェントで始めた作業を現在のエージェントから再開したい

## Read-first ワークフロー（必ず守る）

1. `ax list --json` で最新候補を取得する
2. 候補を `agent` / `title` / `cwd` / `epoch` などで要約し、ユーザーに提示する
3. ユーザーが気になる候補があれば `ax preview --json <agent> <id>` で本文を確認する
4. ユーザーが「このセッションで再開」と明確に承認したらのみ `ax resume <agent> <id>` を実行する

`ax resume` は承認後のみ実行する。候補を要約せずに自動で resume してはいけない。

## JSON スキーマ

### `ax list --json`

各行は以下のキーを持つ JSON オブジェクトの配列となる。

| key | type | meaning |
| --- | --- | --- |
| `agent` | string | `claude`, `codex`, `agy`, `opencode`, `devin` のいずれか |
| `id` | string | セッション ID |
| `epoch` | int | 最終更新時刻 (Unix epoch seconds) |
| `cwd` | string | 作業ディレクトリ (`?` の場合あり) |
| `title` | string | セッション表示名 (rename エイリアスを含む) |

### `ax list --json --grep <query>`

`--grep` 使用時、各行は上記に加えて `match` キーを持つ。

| key | type | meaning |
| --- | --- | --- |
| `match` | string | 本文中の検索ヒット箇所 (snippet) |

`match` に含まれる文字列に `\t` や `\n` は含まれない。

### `ax preview --json <agent> <id>`

単一の JSON オブジェクトを返す。

| key | type | meaning |
| --- | --- | --- |
| `agent` | string | 指定した agent |
| `id` | string | 指定した session id |
| `preview` | string | 人間が読めるトークン形式の本文プレビュー |

## 使用例

```bash
# 最新 10 件を JSON で取得
ax list --json --limit 10

# 本文に "migration" を含むセッションを横断検索
ax list --json --grep migration

# claude の特定セッション本文をプレビュー
ax preview --json claude sess-c1a2b3

# ユーザー承認後に再開
ax resume claude sess-c1a2b3
```

## 制約

- ax / fzf 0.44 互換
- 標準ライブラリのみ
- SQLite は read-only URI
- 1 プロバイダ異常時も他は継続し、stderr に警告を出す
