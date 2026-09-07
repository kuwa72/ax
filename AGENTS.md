# AGENTS.md — ax の開発手順 (ゼロコンテキストのエージェント向け)

このリポジトリは issue 駆動で開発する。issue 番号だけ渡された状態から
テスト追加→PR→CI 確認→マージまで自律実行できるよう、手順を固定する。

## 0. 着手前

- トラッキング issue (#8) を見て着手順序を確認する。依存先 issue が OPEN なら着手しない (調査のみ可)。
- 自分の issue 本文の「実行前提」「受入条件」を読む。不明点は実装で埋めず、issue にコメントして確認する。

## 1. ブランチ

```sh
git checkout main && git pull
git checkout -b feat/issue-<番号>-<slug>
```

## 2. TDD

- 先に `tests/test_<対象>.py` を書く。fixture は `tests/fixtures/` の**合成データのみ** (実セッションデータの転載は禁止。個人情報・プロンプト内容が混入するため)。
- `python3 -m pytest` で失敗 (red) を確認してから実装する。

## 3. 実装

- 変更は原則 `ax` 単一ファイル。挙動変更があれば `README.md` も更新する。
- 制約: 標準ライブラリのみ / fzf 0.44 互換 (`transform` 等の新 action 不可) /
  SQLite は read-only URI / 1 プロバイダ異常時も他は継続 (stderr 警告のみ)。

## 4. 検証

```sh
python3 -m pytest
./ax list | awk -F'\t' 'NF!=7{print "BAD:", $0}'   # TSV列崩れ検出
./ax preview <agent> <id>   # 実データで目視 (opencode.db 3GB超・読むだけ)
```

## 5. PR

- push 後 `gh pr create --fill`。本文に `Closes #<番号>` を含める。
- CI (`.github/workflows/ci.yml`) の緑がマージ条件。赤なら修正して再 push。

## 6. マージ

- CI 緑を確認したら `gh pr merge --squash --delete-branch` でマージする。
- マージ後、トラッキング issue のチェックボックスを更新する。
