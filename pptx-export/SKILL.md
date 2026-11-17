---
name: pptx-export
description: スライドの画像（PNG・JPG）を、見た目に忠実で編集しやすいパワポ（.pptx）に作り直す。画像を貼るのではなく、図形・文字・線を1つずつ置いて、文字や色をそのまま直せるファイルにする。既定はパワポで、Mac で指定があれば Keynote（.key）でも出力する。画像がなく ponchi-e スキルがある場合は、内容からポンチ絵を作ってから書き出す。「この画像をパワポにして」「Keynote にして」「pptx で出力して」「ポンチ絵をパワポで作って」「スライドを編集できる形にして」と言われたときに使う。
---

# 画像からパワポ（Keynote）を作る

画像に描かれたスライドを、**図形・文字・線・画像を1つずつ置いた編集できるファイル**に作り直す。スライドの定義（JSON）を書き、`scripts/build.py` でパワポを作る。Keynote が必要なら、それを Keynote で開いて保存する。

## 出力の形式
- **既定はパワポ（.pptx）**。`build.py` の既定の出力。
- 「Keynote で」と言われたら、Mac で `--format key` を付ける（パワポを作り、Keynote で開いて .key で保存する）。Mac 以外や Keynote がない場合は、パワポで出してその旨を伝える。

## 進め方の分かれ道
1. **画像が渡された**
   - その画像を作った HTML（ponchi-e の `slide_01.png` と同じフォルダの `slide_01.html` など）があれば、**HTML から読み取る**（下の A）。位置・色・文字が正確に取れる。
   - HTML がなければ、**画像を見て定義を書く**（下の B）。
2. **画像がなく、内容（テーマ・伝えたいこと・データ）だけが渡された**
   - `~/.claude/skills/ponchi-e/SKILL.md` があれば、ponchi-e の手順でポンチ絵（HTML と PNG）を作り、その HTML から A で書き出す。
   - ponchi-e がなければ、元になる画像を渡してもらうよう伝える。

## A. HTML から読み取る（ponchi-e で作った画像）
```bash
python3 ~/.claude/skills/pptx-export/scripts/measure.py slide_01.html slide_02.html -o <作業フォルダ>
```
- `<作業フォルダ>/spec.json`（スライドの定義の下書き）と `assets/`（アイコン・イラストを透明の背景で書き出した PNG）ができる。HTML 1つがスライド1枚になる。
- 背景も枠もないレイアウト用の入れ物は出さない。文字はブラウザで実際に折り返された位置で改行してある。
- `todo` が出たスライドは、疑似要素（`::before` / `::after`）で描いた矢印などが読み取れていない。`todo` の位置を元の画像で確認し、`line`（矢印付き）や `triangle` を足してから `todo` を消す。
- 下書きを、下の「編集しやすくする」に沿って見直してから書き出す。

## B. 画像を見て定義を書く
1. 画像を Read ツールで開き、スライドを構成する部品（面・カード・見出し帯・矢印・文字・アイコンなど）を上から順に洗い出す。
2. 目盛りを重ねた画像で位置と大きさを読む。細かいところは範囲を拡大して読む。座標はすべて 1280×720 に換算した px。
   ```bash
   python3 ~/.claude/skills/pptx-export/scripts/inspect_image.py grid  元画像.png <作業フォルダ>/grid.png
   python3 ~/.claude/skills/pptx-export/scripts/inspect_image.py grid  元画像.png <作業フォルダ>/zoom.png --region 520 150 700 160
   python3 ~/.claude/skills/pptx-export/scripts/inspect_image.py color 元画像.png 900 160 700 320
   ```
   - 色は推測せず、`color` で面・文字・線の色を取る（文字の色は、太い線の中心を指定する）。
   - 文字の大きさは、拡大した画像で漢字1文字の高さ（≒ 文字の大きさの px）を読む。
3. 図形や文字で描けないもの（アイコン、イラスト、写真、ロゴ、複雑なグラフ）は、元の画像から切り出して `image` で置く。背景が単色なら透明にする。
   ```bash
   python3 ~/.claude/skills/pptx-export/scripts/inspect_image.py crop 元画像.png 1080 300 24 24 <作業フォルダ>/assets/icon_01.png --transparent '#ffffff'
   ```
4. `spec.json` を書く（下の「スライドの定義」）。棒グラフの棒・表の罫線・矢羽根のように図形で描けるものは図形にし、画像にしない。

## 編集しやすくする（A・B 共通）
- **1つの見た目に1つのオブジェクト。** 同じ位置に重なる面や、見えない入れ物を置かない。
- **面の上の文字は、その面（`box`）に文字を入れる。** 見出し帯・ラベル・ボタン・ピルのように、面と文字が1対1のものは、面と文字ボックスを別々に置かない。
- **1つの文・1つのまとまりは、1つの文字ボックスにする。** 「33.2」「%」「が増加」のように大きさや色だけ違う文字は、別のボックスに分けず、1つのボックスの中で `paras` の run を分ける。見出しと本文のように役割が違うものは分けてよい。
- **改行は元の画像の位置で入れる**（`wrap: false` ＋ 段落を分ける）。自動の折り返しに任せると、フォントの差で改行位置がずれる。
- 線と矢印は `line` で描く。矢印の先の三角を別の図形にしない。
- アイコン・イラストは `image` を1つずつ置き、元の大きさのまま並べる。
- 要素の重なり順は、配列の順（先に書いたものが下）。背景の面 → カード → 文字・線 → アイコンの順にする。
- 必要なら `name` に役割（「見出し：攻撃」など）を付ける。編集画面のオブジェクト一覧で探しやすくなる。

## スライドの定義（JSON）
```json
{
  "size": [1280, 720],
  "font": "Hiragino Sans",
  "slides": [
    {"bg": "#ffffff", "notes": "発表者ノート（任意）", "items": [
      {"type": "box", "shape": "round", "x": 48, "y": 190, "w": 1184, "h": 145, "r": 16, "fill": "#f0f0f0"},
      {"type": "box", "shape": "round", "x": 261, "y": 145, "w": 140, "h": 34, "r": 8, "fill": "#3a3a3a",
       "text": "何が変わるか", "size": 16, "weight": 700, "color": "#ffffff", "align": "c", "valign": "m"},
      {"type": "text", "x": 64, "y": 88, "w": 1152, "h": 29, "size": 20, "lh": 1.45, "paras": [[
        {"t": "ボトルネックは発見から"}, {"t": "検証と修正", "w": 700, "c": "#3b5af4"}, {"t": "に移っている"}]]},
      {"type": "line", "pts": [[510, 263], [538, 263]], "color": "#9a9a9a", "lw": 2, "arrow": "end"},
      {"type": "image", "x": 90, "y": 232, "w": 28, "h": 28, "src": "assets/icon_01.png"}
    ]}
  ]
}
```
- **共通**：`x` `y` `w` `h`（px）、`name`（任意）。
- **box**（図形）：`shape` は `rect` / `round`（角丸。`r` に半径 px）/ `ellipse` / `pentagon`（右がとがった矢羽根）/ `chevron`（左に切り欠きのある矢羽根）/ `triangle`。`tip` は矢羽根の先の長さ（px）、`rot` は回転（度）。`fill`（塗り。省略で塗りなし）、`line`（枠線の色）・`lw`（枠線の太さ px）・`dash`（点線）。文字を入れる場合は下の文字の項目も書く。
- **text**（文字ボックス）：塗りも枠もない文字。
- **文字の項目**（box・text 共通）：
  - `text`（`\n` で段落を分ける）か `paras`（段落の配列。段落は run の配列で、run は `t` 文字、`s` 大きさ px、`w` 太さ（400 標準・700 太字・800 極太）、`c` 色）
  - `size`（px）、`weight`、`color`：run で省略したときの既定
  - `align`（`l` / `c` / `r`）、`valign`（`t` / `m` / `b`）、`pad`（左・上・右・下の余白 px）、`lh`（行の高さ。文字の大きさの倍率。CSS の line-height と同じ）、`wrap`（自動で折り返すか。既定は false）
- **line**（線・矢印）：`pts`（2点なら直線、3点以上なら折れ線）、`color`、`lw`、`dash`、`arrow`（`end` / `start` / `both`）、`head`（矢印の大きさ `sm` / `med` / `lg`）。
- **image**：`src`（spec.json からの相対パス）。
- 文字の大きさの px は、書き出し時に pt（× 0.75）に換算される。フォントは `font` で指定し、省略すると Mac は Hiragino Sans、それ以外は Yu Gothic。Hiragino Sans は太さ（`w` / `weight`）に合わせて W3〜W9 の書体を使い分ける。

## 書き出しと確認
1. 書き出す（出力先の拡張子は自動で付く）：
   ```bash
   python3 ~/.claude/skills/pptx-export/scripts/build.py <作業フォルダ>/spec.json -o <出力先>/slides [--format key]
   ```
2. 書き出したファイルを画像にして、元の画像と上下に並べた比較画像を作る（Mac は Keynote、Windows は PowerPoint で描画する）：
   ```bash
   python3 ~/.claude/skills/pptx-export/scripts/preview.py <出力先>/slides.pptx -o <作業フォルダ>/preview --ref 元画像1.png 元画像2.png
   ```
3. `compare_01.png` などを Read ツールで開き、上（元の画像）と下（書き出したもの）を比べる。確認項目：
   - 文字の改行位置・はみ出し・重なり（とくに大きさの違う文字が並ぶところ、アイコンの横の文字）
   - 図形の位置・大きさ・角丸・色、矢印の向き
   - 抜けている要素（矢印の先、箇条書きの記号、アイコン）
   - 余計な要素（重なった面、見えない箱）
4. ずれがあれば `spec.json` を直して 1〜3 をくり返す。
5. 出力したファイルのパスと、元の画像と違うところ（画像で置いた要素、フォントの違いなど）を伝える。作業フォルダ（spec.json・assets・preview）は、ユーザーの出力先とは分け、指定がなければ一時フォルダに置く。

## 必要な環境
- Python 3、`python-pptx`、`Pillow`（`pip install python-pptx pillow`）
- A（HTML から読み取る）には Playwright（Chromium）
- Keynote への変換と確認用の書き出しは Mac の Keynote、Windows での確認用の書き出しは PowerPoint。初回は、ターミナルから Keynote を操作する許可を求められることがある
