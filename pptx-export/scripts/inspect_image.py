#!/usr/bin/env python3
"""画像からスライドの定義を書くための補助。座標はすべて 1280×720 に換算した px で指定・表示する。

使い方:
  inspect_image.py grid  <画像> <出力.png> [--region x y w h]
      画像に目盛り（10px ごとの細線、50px ごとの線、100px ごとの数字）を重ねる。
      --region を付けると、その範囲を拡大して目盛りを重ねる（細かい位置や文字の大きさを読むとき）。
  inspect_image.py color <画像> x y [x y ...]
      指定した点の色を #RRGGBB で表示する。
  inspect_image.py crop  <画像> x y w h <出力.png> [--transparent #RRGGBB]
      範囲を元の解像度のまま切り出す（アイコン・イラスト・写真・複雑なグラフ用）。
      --transparent を付けると、その色（背景）を透明にする。
"""
import sys

from PIL import Image, ImageDraw

W, H = 1280, 720


def load(path):
    im = Image.open(path).convert('RGB')
    return im, im.width / W


def grid(path, out, region=None):
    im, k = load(path)
    x0, y0, rw, rh = region or (0, 0, W, H)
    crop = im.crop((round(x0 * k), round(y0 * k), round((x0 + rw) * k), round((y0 + rh) * k)))
    z = max(1.0, min(2560 / rw, 1440 / rh))  # 拡大率（1px あたりの画素数）
    crop = crop.resize((round(rw * z), round(rh * z)), Image.LANCZOS)
    d = ImageDraw.Draw(crop, 'RGBA')
    for v in range(int(x0 // 10 * 10), int(x0 + rw) + 1, 10):
        X = (v - x0) * z
        d.line([(X, 0), (X, crop.height)], fill=(255, 0, 255, 150 if v % 50 == 0 else 40), width=1)
        if v % (100 if z < 3 else 50) == 0:
            d.text((X + 2, 2), str(v), fill=(255, 0, 255, 255))
    for v in range(int(y0 // 10 * 10), int(y0 + rh) + 1, 10):
        Y = (v - y0) * z
        d.line([(0, Y), (crop.width, Y)], fill=(255, 0, 255, 150 if v % 50 == 0 else 40), width=1)
        if v % (100 if z < 3 else 50) == 0:
            d.text((2, Y + 2), str(v), fill=(255, 0, 255, 255))
    crop.save(out)
    print(out)


def color(path, pts):
    im, k = load(path)
    for x, y in pts:
        r, g, b = im.getpixel((min(im.width - 1, round(x * k)), min(im.height - 1, round(y * k))))
        print(f'{x},{y}: #{r:02x}{g:02x}{b:02x}')


def crop(path, x, y, w, h, out, transparent=None):
    im, k = load(path)
    c = im.crop((round(x * k), round(y * k), round((x + w) * k), round((y + h) * k))).convert('RGBA')
    if transparent:
        t = tuple(int(transparent.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        px = c.load()
        for j in range(c.height):
            for i in range(c.width):
                r, g, b, _ = px[i, j]
                # 背景色との差が小さいほど透明にする（縁のなめらかさを残す）
                dist = max(abs(r - t[0]), abs(g - t[1]), abs(b - t[2]))
                if dist < 96:
                    a = round(255 * dist / 96)
                    if a < 255 and dist:
                        f = 255 / max(a, 1)
                        r, g, b = (min(255, max(0, round(t[n] + (v - t[n]) * f))) for n, v in enumerate((r, g, b)))
                    px[i, j] = (r, g, b, a)
    c.save(out)
    print(out)


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == 'grid':
        region = None
        if '--region' in a:
            i = a.index('--region')
            region = tuple(float(v) for v in a[i + 1:i + 5])
            a = a[:i] + a[i + 5:]
        grid(a[1], a[2], region)
    elif cmd == 'color':
        nums = [float(v) for v in a[2:]]
        color(a[1], list(zip(nums[::2], nums[1::2])))
    elif cmd == 'crop':
        t = None
        if '--transparent' in a:
            i = a.index('--transparent')
            t = a[i + 1]
            a = a[:i] + a[i + 2:]
        crop(a[1], *(float(v) for v in a[2:6]), a[6], t)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
