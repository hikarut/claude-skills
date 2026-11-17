#!/usr/bin/env python3
"""スライドの定義（JSON）から、編集できるパワポ（.pptx）か Keynote（.key）を作る。

使い方:
  build.py <spec.json> -o <出力先（拡張子なしでよい）> [--format pptx|key]

既定はパワポ（pptx）。--format key は Mac のみで、いったんパワポを作り、Keynote で開いて .key で保存する。

座標・大きさ・文字の大きさは、すべて 1280×720 のキャンバスの px で書く。
定義の書き方は SKILL.md の「スライドの定義（JSON）」を参照。
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

PX = 9525  # 1px = 9525 EMU（1280px = 13.333in）
SHAPES = {
    'rect': MSO_SHAPE.RECTANGLE,
    'round': MSO_SHAPE.ROUNDED_RECTANGLE,
    'ellipse': MSO_SHAPE.OVAL,
    'pentagon': MSO_SHAPE.PENTAGON,      # 右端がとがった矢羽根（ホームベース）
    'chevron': MSO_SHAPE.CHEVRON,        # 左端に切り欠きのある矢羽根
    'triangle': MSO_SHAPE.ISOSCELES_TRIANGLE,
}
ALIGN = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}
VALIGN = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}


def default_font():
    return 'Hiragino Sans' if platform.system() == 'Darwin' else 'Yu Gothic'


# ヒラギノは太さごとの名前で指定する（太字の指定だけでは、英数字が太くならない）
HIRAGINO_W = [(350, 3), (450, 4), (550, 5), (650, 6), (750, 7), (850, 8), (1000, 9)]


def font_for(name, weight):
    """(フォント名, 太字か) を返す。weight は CSS の太さ（400＝標準、700＝太字）。"""
    if name == 'Hiragino Sans':
        n = next(w for limit, w in HIRAGINO_W if weight <= limit)
        return f'HiraginoSans-W{n}', False
    return name, weight >= 600


def px(v):
    return Emu(int(round(v * PX)))


def rgb(h):
    h = h.lstrip('#')
    return RGBColor.from_string(h[:6].upper())


def set_line(line, color=None, lw=None, dash=False):
    if not color:
        line.fill.background()
        return
    line.color.rgb = rgb(color)
    line.width = px(lw or 1)
    if dash:
        line.dash_style = MSO_LINE.DASH


def add_arrow(line, arrow, size='med'):
    if not arrow:
        return
    ln = line._get_or_add_ln()
    for tag, on in (('a:headEnd', arrow in ('start', 'both')), ('a:tailEnd', arrow in ('end', 'both'))):
        if on:
            e = etree.SubElement(ln, qn(tag))
            e.set('type', 'triangle')
            e.set('w', size)
            e.set('len', size)


def paras_of(it):
    if 'paras' in it:
        return it['paras']
    if 'text' in it:
        return [[{'t': line}] for line in str(it['text']).split('\n')]
    return None


def fill_text(tf, it, font):
    paras = paras_of(it)
    if paras is None:
        return
    pad = it.get('pad', [0, 0, 0, 0])
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (px(v) for v in pad)
    tf.word_wrap = bool(it.get('wrap', False))
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = VALIGN[it.get('valign', 't')]
    size = it.get('size', 16)
    for i, runs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = ALIGN[it.get('align', 'l')]
        if it.get('lh'):
            p.line_spacing = Pt(it['lh'] * size * 0.75)
        for r in runs:
            run = p.add_run()
            run.text = r['t']
            f = run.font
            s = r.get('s', size)
            f.size = Pt(s * 0.75)
            weight = r.get('w', it.get('weight', 700 if r.get('b', it.get('bold', False)) else 400))
            name, bold = font_for(r.get('font', it.get('font', font)), weight)
            f.bold = bold
            f.color.rgb = rgb(r.get('c', it.get('color', '#333333')))
            f.name = name
            rpr = run._r.get_or_add_rPr()
            ea = rpr.find(qn('a:ea'))
            if ea is None:
                ea = etree.SubElement(rpr, qn('a:ea'))
            ea.set('typeface', name)


def add_item(slide, it, font, base):
    t = it['type']
    if t == 'line':
        pts = it['pts']
        if len(pts) == 2:
            (x1, y1), (x2, y2) = pts
            shp = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, px(x1), px(y1), px(x2), px(y2))
        else:
            fb = slide.shapes.build_freeform(px(pts[0][0]), px(pts[0][1]), scale=1.0)
            fb.add_line_segments([(px(x), px(y)) for x, y in pts[1:]], close=False)
            shp = fb.convert_to_shape()
            shp.fill.background()
        set_line(shp.line, it.get('color', '#999999'), it.get('lw', 2), it.get('dash', False))
        add_arrow(shp.line, it.get('arrow'), it.get('head', 'med'))
    elif t == 'image':
        src = os.path.join(base, it['src'])
        shp = slide.shapes.add_picture(src, px(it['x']), px(it['y']), px(it['w']), px(it['h']))
    elif t == 'text':
        shp = slide.shapes.add_textbox(px(it['x']), px(it['y']), px(it['w']), px(it['h']))
        fill_text(shp.text_frame, it, font)
    elif t == 'box':
        kind = it.get('shape', 'rect')
        shp = slide.shapes.add_shape(SHAPES[kind], px(it['x']), px(it['y']), px(it['w']), px(it['h']))
        m = min(it['w'], it['h'])
        if kind == 'round':
            shp.adjustments[0] = min(0.5, it.get('r', 8) / m)
        elif kind in ('pentagon', 'chevron'):
            shp.adjustments[0] = it.get('tip', 18) / m
        if it.get('rot'):
            shp.rotation = it['rot']
        if it.get('fill'):
            shp.fill.solid()
            shp.fill.fore_color.rgb = rgb(it['fill'])
        else:
            shp.fill.background()
        set_line(shp.line, it.get('line'), it.get('lw', 1), it.get('dash', False))
        shp.shadow.inherit = False
        tf = shp.text_frame
        if paras_of(it) is not None:
            fill_text(tf, it, font)
        else:
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    else:
        sys.exit(f'未対応の type: {t}')
    # テーマの線・塗り・影を引き継がないようにする（色はすべて明示する）
    style = shp._element.find(qn('p:style'))
    if style is not None:
        shp._element.remove(style)
    if it.get('name'):
        shp.name = it['name']


def build_pptx(spec, base, out):
    font = spec.get('font') or default_font()
    w, h = spec.get('size', [1280, 720])
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(w), px(h)
    for s in spec['slides']:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        if s.get('bg'):
            slide.background.fill.solid()
            slide.background.fill.fore_color.rgb = rgb(s['bg'])
        for it in s.get('items', []):
            add_item(slide, it, font, base)
        if s.get('notes'):
            slide.notes_slide.notes_text_frame.text = s['notes']
    prs.save(out)


def to_keynote(pptx_path, key_path):
    script = f'''
set src to POSIX file "{pptx_path}"
set dst to POSIX file "{key_path}"
tell application "Keynote"
  set d to open src
  save d in dst
  close d saving no
end tell'''
    subprocess.run(['osascript', '-e', script], check=True, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--format', choices=['pptx', 'key'], default='pptx')
    a = ap.parse_args()

    fmt = a.format
    if fmt == 'key' and (platform.system() != 'Darwin' or not os.path.exists('/Applications/Keynote.app')):
        print('Keynote が使えないため、パワポ（.pptx）で出力します', file=sys.stderr)
        fmt = 'pptx'

    spec = json.load(open(a.spec, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(a.spec))
    out = os.path.abspath(os.path.splitext(a.out)[0] + '.' + fmt)

    if fmt == 'pptx':
        build_pptx(spec, base, out)
    else:
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, 'deck.pptx')
            build_pptx(spec, base, p)
            if os.path.exists(out):
                shutil.rmtree(out) if os.path.isdir(out) else os.remove(out)
            to_keynote(p, out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(out)


if __name__ == '__main__':
    main()
