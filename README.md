# claude-skills

Claude Code で使う自作スキル集。

### スキル一覧

| スキル | 概要 |
|---|---|
| [ponchi-e](ponchi-e/SKILL.md) | 戦略コンサルが作成したような洗練されたポンチ絵を 16:9 の画像（PNG）で作成する |
| [biz-research](biz-research/SKILL.md) | 企業・業界のビジネスモデル図、組織図（企業のみ）、KPIツリー、直近のニュースを調べ、ポンチ絵と HTML レポートにまとめる |
| [x-post](x-post/SKILL.md) | テーマの参考記事（または貼った URL の記事）を読み、過去の投稿と同じ言い回しで X の投稿文を作る（280ウェイト以内） |

### セットアップ

```bash
git clone git@github.com:hikarut/claude-skills.git ~/github/claude-skills
ln -s ~/github/claude-skills/ponchi-e ~/.claude/skills/ponchi-e
ln -s ~/github/claude-skills/biz-research ~/.claude/skills/biz-research
ln -s ~/github/claude-skills/x-post ~/.claude/skills/x-post
pip install playwright && playwright install chromium
```

`~/.claude/skills/` にシンボリックリンクを置くので、リポジトリ側でスキルを修正すると Claude Code にもそのまま反映される。最新版への更新は `git pull` で行う。

# ponchi-e

戦略コンサルタントが時間をかけて作ったような、洗練されたポンチ絵（1枚で概念や全体像を伝える図解スライド）を、16:9 の PNG 画像として作成するスキル。1枚に1つの図を大きく置き、余白とコントラストで伝える。

「スライドを作って」「ポンチ絵にして」「1枚にまとめて」と頼むか、`/ponchi-e` で呼び出す。

### スライドの構成
1. **スライドタイトル**：左寄せの大きな太字。章ラベルは付けない
2. **キーメッセージ**：そのページの結論を1〜2行の文で書く（太字にしない）
3. **コンテンツ**：内容に合った図を1つ置く（お手本の放射図・流れ図・レベル図・タイムライン・比較表・事例カード・3つの理由は仕上がりの目安で、形はこれらに限らない）
4. **フッター**：右下にコピーライト（ページ番号は付けない）、数値を載せた場合は左下に出所

### デザインの特徴
- メインカラー（既定は `#3b5af4`）は主役だけに使い、それ以外はチャコール・グレー・メインカラーの淡色で描いて強弱をつける
- 主役の図は1つに絞り、各要素の短い説明や下段の補足（データ・活用シーン・効果・成果物など）で具体性を出す
- 余白を活かし、主要な説明は16〜18px、補足は14〜15pxで大きさに差をつける
- [Lucide](https://lucide.dev/icons) のアイコンをグレーの細線で使い、必要なときだけ [unDraw](https://undraw.co/illustrations) のイラストをメインカラーに色を変えて添える
- 情報の詰め込み、グラデーション、影、絵文字など、野暮ったく見える表現は使わない

### ファイル構成
```
ponchi-e/
├── SKILL.md              # 構成・パターン・デザインルール・手順
├── theme.css             # メインカラーの指定（ここだけ変えれば色が変わる）
├── templates/base.html   # スライドの雛形と部品の CSS（1280×720）
├── examples/             # 仕上がりの目安となるお手本（HTML と完成画像）
│   ├── hub.*             #   放射図
│   ├── flow.*            #   流れ図
│   ├── levels.*          #   レベル図
│   ├── phases.*          #   タイムライン
│   ├── compare.*         #   比較表
│   ├── cases.*           #   事例カード
│   └── reasons.*         #   3つの理由
└── scripts/
    ├── render.py         # HTML を PNG（2560×1440）に書き出す
    └── undraw.py         # unDraw イラストの検索・取得と色の置き換え（recolor で保存済みの SVG も置き換え）
```

### 必要な環境
- Python 3 と Playwright（Chromium）
- curl（unDraw からのイラスト取得に使用）
- インターネット接続（Lucide のアイコンを CDN から読み込む）
- 日本語フォント：ヒラギノ角ゴシック（macOS 標準）

### メインカラーの変え方
- **依頼ごとに変える**：「メインカラーは #0a7d5a で」のように頼む。出力先にコピーされた `theme.css` だけが書き換わり、スキル本体はそのまま
- **既定の色を変える**：`ponchi-e/theme.css` の `--main` を書き換える。淡い面や強調用の濃い色は、メインカラーから自動で作られる

# biz-research

指定した企業や業界のビジネスモデルを調査し、次の項目をポンチ絵（PNG）にして、1つの HTML レポート（`report.html`）にまとめるスキル。

- **ビジネスモデル図**：[図解総研のビズグラム](https://note.com/bizgram/n/n5bde4d5402d1)のルール（3×3のマス目、主体・矢印・補足、モノ・情報・カネ・行為・包含の5種類の矢印）で描く
- **組織図**：企業の場合のみ。ガバナンス・経営陣・事業部門・主な子会社の体制を、担当事業や人数とあわせて描く
- **KPIツリー**：売上（業界なら市場規模）を頂点に、具体的な数値付きでできるだけ深く分解する。推計値は計算式をレポートに書く
- **直近のニュース**：直近3か月を中心に、日付・出所・示唆を付けてまとめる

「〇〇社のビジネスモデルを調べて」「〇〇業界を調査して」と頼むか、`/biz-research` で呼び出す。ポンチ絵は ponchi-e スキルで作る（ponchi-e がなければ、図をレポートの中に HTML で直接描く）。

### ファイル構成
```
biz-research/
├── SKILL.md               # 調査の進め方・図のルール・レポートの構成・手順
├── templates/report.html  # まとめの HTML レポートの雛形
└── examples/              # 仕上がりの目安となるお手本（ponchi-e の base.html に入れて使う HTML と完成画像）
    ├── bizgram.*          #   ビジネスモデル図（ビズグラム）
    └── kpi-tree.*         #   KPIツリー
```

# x-post

テーマを指定すると、参考記事を探して中身を読み、過去の自分の投稿と同じ言い回しで X の投稿文を作るスキル。選んだ投稿文は、投稿を管理しているスプレッドシートの C 列に追加する。

- **過去の投稿を踏まえる**：過去の投稿と反応のデータから、言い回し・投稿の型・伸びる記事の種類を踏まえて書く
- **参考記事**：過去に伸びた出所や切り口に近い記事を探し、中身を読んでから書く。紹介済みの記事は除く
- **文字数**：X の 280ウェイト（半角1・全角2・URL 23）以内で、目安は 230〜280。`scripts/count.py` で数える
- **スプレッドシートへの追加**：選んだ投稿文を、Google Sheets API で C 列の次の空き行に追加する

「〇〇でXの投稿文を考えて」と頼むか、`/x-post` で呼び出す。記事の URL を貼ると、その記事を読んで投稿文を作る。

### ファイル構成
```
x-post/
├── SKILL.md                 # 手順・文字数の制限・出力の形・データの更新
├── references/style.md      # 過去の投稿の分析（言い回し・投稿の型・反応の傾向・お手本）
├── data/posts.csv           # 過去の投稿と反応（git には入れない）
├── config.example.json      # スプレッドシートの設定の雛形（config.json にコピーして使う。config.json は git に入れない）
└── scripts/
    ├── count.py             # 投稿文のウェイトを数える
    ├── append_sheet.py      # 投稿文をスプレッドシートの C 列に追加する
    └── update_posts.py      # 過去の投稿データを、スプレッドシートから作り直す
```

### 過去の投稿データの更新
`data/posts.csv` は git に入れていないので、次を実行して作る。スプレッドシートの「ツイートリスト_」で始まるシートをすべて Google Sheets API で読み、毎回作り直す（下の「スプレッドシートの設定」が必要）。
```bash
python3 ~/.claude/skills/x-post/scripts/update_posts.py
```

### スプレッドシートの設定（追加・データの更新に使う）
1. Google Cloud でプロジェクトを作り、Google Sheets API を有効にする
2. サービスアカウントを作り、鍵（JSON）を作成して `~/.config/x-post/service_account.json` に保存する
3. スプレッドシートを、サービスアカウントのメールアドレス（`〜@〜.iam.gserviceaccount.com`）に「編集者」として共有する
4. `config.example.json` を `config.json` にコピーし、スプレッドシートの ID と追加先のシートの gid を書く
5. ライブラリを入れる：`pip install google-auth requests`
6. 書き込まずに確認する：`echo test | python3 ~/.claude/skills/x-post/scripts/append_sheet.py --dry-run`
