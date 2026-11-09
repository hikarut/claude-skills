#!/usr/bin/env python3
"""X（旧Twitter）の投稿文のウェイト（文字数）を数える。

使い方:
  python3 count.py "投稿文"          # 引数で渡す
  python3 count.py < post.txt         # 標準入力で渡す（複数行の投稿はこちら）
  python3 count.py -f post.txt        # ファイルで渡す

数え方（X の twitter-text の規則）:
  - 半角英数字・記号など（U+0000〜U+10FF、一般句読点の一部）は 1
  - 日本語・全角文字・絵文字などは 2
  - URL は長さにかかわらず 1本 23
  - 改行も 1 文字（1）として数える
  - 上限は 280
絵文字の結合文字（肌の色・ZWJ など）は多めに数えるので、実際より少し大きめの値になる（安全側）。
"""
import re
import sys
import unicodedata

LIMIT = 280
URL_WEIGHT = 23
# ウェイト 1 の範囲（twitter-text v3 の設定）
LIGHT = [(0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037)]
URL_RE = re.compile(r'https?://[^\s　-〿぀-ヿ一-鿿＀-￯]+')


def weight(text: str):
    text = unicodedata.normalize('NFC', text)
    urls = URL_RE.findall(text)
    rest = URL_RE.sub('', text)
    w = 0
    for ch in rest:
        cp = ord(ch)
        w += 1 if any(lo <= cp <= hi for lo, hi in LIGHT) else 2
    return w + URL_WEIGHT * len(urls), urls


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '-f':
        text = open(sys.argv[2], encoding='utf-8').read()
    elif len(sys.argv) >= 2:
        text = ' '.join(sys.argv[1:])
    else:
        text = sys.stdin.read()
    text = text.strip('\n')
    w, urls = weight(text)
    status = 'OK' if w <= LIMIT else f'NG（{w - LIMIT} 超過）'
    print(f'ウェイト: {w} / {LIMIT}  {status}')
    print(f'残り: {LIMIT - w}')
    print(f'URL: {len(urls)}本（{URL_WEIGHT * len(urls)}）')
    sys.exit(0 if w <= LIMIT else 1)


if __name__ == '__main__':
    main()
