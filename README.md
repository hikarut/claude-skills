# claude-skills

Claude Code で使う自作スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [consulting-slide](consulting-slide/SKILL.md) | 戦略コンサルが作成したようなポンチ絵を 16:9 の画像（PNG）で作成する |

## consulting-slide

戦略コンサルタントが時間をかけて作ったようなポンチ絵（1枚に全体像をまとめた図解スライド）を、16:9 の PNG 画像として作成するスキル。

「スライドを作って」「ポンチ絵にして」「1枚にまとめて」と頼むか、`/consulting-slide` で呼び出す。

### スライドの構成
1. **スライドタイトル**：左寄せの大きな太字。章ラベルは付けない
2. **キーメッセージ**：そのページの結論を1行の文で書く（太字にしない）
3. **コンテンツ**：ラベル帯付きのブロック（プロセス、As-Is/To-Be 比較表、工程対応、KPI、ロードマップなど）を組み合わせる
4. **核心メッセージの帯**（任意）：最下段に一番伝えたいことを1行で
5. **フッター**：左下に出所、右下にページ番号

### デザインの特徴
- `#a100ff` の濃淡とグレーだけで配色する。核心となる要素は紫の太枠とリボンで強調する
- ステップごとに [unDraw](https://undraw.co/illustrations) のイラストを `#a100ff` に色を変えて添え、[Lucide](https://lucide.dev/icons) のアイコンを紫で使う
- グラデーション、影、絵文字など、AI生成っぽく見える表現は使わない

### ファイル構成
```
consulting-slide/
├── SKILL.md              # 構成・部品の使い方・デザインルール・手順
├── templates/base.html   # スライドの雛形と部品の CSS（1280×720）
└── scripts/
    ├── render.py         # HTML を PNG（2560×1440）に書き出す
    └── undraw.py         # unDraw イラストの検索・取得と色の置き換え
```

### 必要な環境
- Python 3 と Playwright（Chromium）
- curl（unDraw からのイラスト取得に使用）
- インターネット接続（Lucide のアイコンを CDN から読み込む）
- 日本語フォント：ヒラギノ角ゴシック（macOS 標準）

## セットアップ

```bash
git clone git@github.com:hikarut/claude-skills.git ~/github/claude-skills
ln -s ~/github/claude-skills/consulting-slide ~/.claude/skills/consulting-slide
pip install playwright && playwright install chromium
```

`~/.claude/skills/` にシンボリックリンクを置くので、リポジトリ側でスキルを修正すると Claude Code にもそのまま反映される。最新版への更新は `git pull` で行う。
