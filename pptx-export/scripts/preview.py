#!/usr/bin/env python3
"""作ったパワポ・Keynote をスライドごとの画像に書き出し、元の画像と上下に並べた比較画像を作る。

使い方:
  preview.py <deck.pptx|deck.key> -o <出力フォルダ> [--ref 元画像1.png 元画像2.png ...]

出力:
  <出力フォルダ>/slide_01.png ...      書き出したスライドの画像
  <出力フォルダ>/compare_01.png ...    上が元の画像、下が書き出したスライド（--ref を渡したとき）

Mac は Keynote、Windows は PowerPoint で書き出す（どちらかがインストールされている必要がある）。
"""
import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

W, H = 1280, 720


def export_mac(deck, outdir):
    script = f'''
set src to POSIX file "{deck}"
set dst to POSIX file "{outdir}"
tell application "Keynote"
  set d to open src
  export d to dst as slide images with properties {{image format:PNG, skipped slides:false}}
  close d saving no
end tell'''
    subprocess.run(['osascript', '-e', script], check=True, capture_output=True, text=True)


def export_win(deck, outdir):
    ps = f'''
$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open("{deck}", $true, $false, $false)
$i = 1
foreach ($s in $p.Slides) {{ $s.Export((Join-Path "{outdir}" ("x{{0:D3}}.png" -f $i)), "PNG", 2560, 1440); $i++ }}
$p.Close(); $pp.Quit()'''
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('deck')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--ref', nargs='*', default=[])
    a = ap.parse_args()
    deck = os.path.abspath(a.deck)
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp()
    try:
        if platform.system() == 'Darwin':
            export_mac(deck, tmp)
        elif platform.system() == 'Windows':
            export_win(deck, tmp)
        else:
            sys.exit('Mac（Keynote）か Windows（PowerPoint）でのみ書き出せます')
        files = sorted(glob.glob(os.path.join(tmp, '**', '*.png'), recursive=True))
        for i, f in enumerate(files, 1):
            img = Image.open(f).convert('RGB').resize((W, H), Image.LANCZOS)
            img.save(os.path.join(a.out, f'slide_{i:02d}.png'))
            if i <= len(a.ref):
                ref = Image.open(a.ref[i - 1]).convert('RGB').resize((W, H), Image.LANCZOS)
                cmp = Image.new('RGB', (W, H * 2 + 8), '#ff00ff')
                cmp.paste(ref, (0, 0))
                cmp.paste(img, (0, H + 8))
                d = ImageDraw.Draw(cmp)
                d.text((6, 4), 'ORIGINAL', fill='#ff00ff')
                d.text((6, H + 12), 'EXPORTED', fill='#ff00ff')
                cmp.save(os.path.join(a.out, f'compare_{i:02d}.png'))
            print(os.path.join(a.out, f'slide_{i:02d}.png'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
