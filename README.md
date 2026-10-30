# claude-skills

Claude Code で使う自作スキル集。

## スキル一覧

| スキル | 概要 |
|---|---|
| [consulting-slide](consulting-slide/SKILL.md) | 戦略コンサルが作成したような資料スライドを 16:9 の画像（PNG）で作成する |

## consulting-slide

戦略コンサルタントが時間をかけて作ったような資料スライドを、16:9 の PNG 画像として作成するスキル。経済産業省の委託調査報告書（令和3年度）のスライドを見た目の手本にしている。

「スライドを作って」「資料を画像で」「1枚にまとめて」と頼むか、`/consulting-slide` で呼び出す。

### スライドの構成
1. **スライドタイトル**：大きな太字。下線や帯、章ラベルは付けない
2. **キーメッセージ**：そのページの結論を1〜2行の文で書く（太字にしない）
3. **コンテンツ**：見出しの下に細い黒線を引いたパネルで構成（1〜2カラム）
4. **フッター**：左下に出所、右下にページ番号

### デザインの特徴
- メインカラーは `#a100ff`。濃・中・淡の3段階を、強調・塗り・ハイライトに使い分ける
- グラフは補助線なし。凡例の代わりに系列名を直接書き、数値ラベルを付ける
- グラデーション、影、角丸カード、絵文字など、AI生成っぽく見える表現は使わない
- 必要に応じて [unDraw](https://undraw.co/illustrations) のイラストを `#a100ff` に色を変えて添える

### ファイル構成
```
consulting-slide/
├── SKILL.md              # 構成・デザインルール・手順
├── templates/base.html   # スライドの雛形（1280×720）
└── scripts/
    ├── render.py         # HTML を PNG（2560×1440）に書き出す
    └── undraw.py         # unDraw イラストの検索・取得と色の置き換え
```

### 必要な環境
- Python 3 と Playwright（Chromium）
- curl（unDraw からのイラスト取得に使用）
- 日本語フォント：ヒラギノ角ゴシック（macOS 標準）

## セットアップ

```bash
git clone git@github.com:hikarut/claude-skills.git ~/github/claude-skills
ln -s ~/github/claude-skills/consulting-slide ~/.claude/skills/consulting-slide
pip install playwright && playwright install chromium
```

`~/.claude/skills/` にシンボリックリンクを置くので、リポジトリ側でスキルを修正すると Claude Code にもそのまま反映される。最新版への更新は `git pull` で行う。
