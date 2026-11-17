#!/usr/bin/env python3
"""ポンチ絵の HTML（1280×720）を描画して、要素の位置・色・文字を読み取り、build.py 用のスライドの定義（JSON）の下書きを作る。

使い方:
  measure.py <slide.html> [<slide2.html> ...] -o <出力フォルダ>

出力:
  <出力フォルダ>/spec.json      スライドの定義の下書き（HTML 1枚＝スライド1枚）
  <出力フォルダ>/assets/*.png   アイコン・イラスト（背景を透明にした画像）

- 背景・枠のない入れ物（レイアウト用の div）は出さない。
- 文字は、ブラウザで実際に折り返された位置で改行を入れる（wrap: false）。
- 疑似要素（::before / ::after）で描いた矢印などは読み取れないので、"todo" に位置を書き出す。
  下書きを見直すときに、line（arrow 付き）や triangle で足す。
"""
import argparse
import json
import os
import pathlib

from playwright.sync_api import sync_playwright

JS = r'''
() => {
  const slide = document.querySelector('.slide') || document.body;
  const S = slide.getBoundingClientRect();
  const R = v => Math.round(v * 10) / 10;
  const hex = c => {
    if (!c) return null;
    let m = c.match(/^rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    let r, g, b, a = 1;
    if (m) { [r, g, b] = [m[1], m[2], m[3]].map(Number); if (m[4] !== undefined) a = Number(m[4]); }
    else {
      m = c.match(/^color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: \/ ([\d.]+))?\)/);
      if (!m) return null;
      [r, g, b] = [m[1], m[2], m[3]].map(v => Number(v) * 255);
      if (m[4] !== undefined) a = Number(m[4]);
    }
    if (a < 0.05) return null;
    if (a < 1) { r = r * a + 255 * (1 - a); g = g * a + 255 * (1 - a); b = b * a + 255 * (1 - a); }
    return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  };
  const box = r => ({x: R(r.left - S.left), y: R(r.top - S.top), w: R(r.width), h: R(r.height)});
  const items = [], todo = [], consumed = new Set();
  const isTextInline = el => {
    const cs = getComputedStyle(el);
    return el.tagName === 'BR' || (cs.display === 'inline' && cs.maskImage === 'none' && cs.webkitMaskImage === 'none' && !hex(cs.backgroundColor));
  };
  // 要素の中の文字を、実際の折り返し位置で区切った段落（runs の配列）にする
  const textOf = el => {
    const paras = [[]];
    let lastTop = null;
    const style = n => {
      const cs = getComputedStyle(n);
      return {s: R(parseFloat(cs.fontSize)), w: Number(cs.fontWeight), c: hex(cs.color) || '#000000'};
    };
    const push = (ch, st) => {
      const runs = paras[paras.length - 1];
      const last = runs[runs.length - 1];
      if (last && last.s === st.s && last.w === st.w && last.c === st.c) last.t += ch;
      else runs.push({t: ch, ...st});
    };
    let left = Infinity;
    textOf.top = null;
    const walk = n => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) {
          const st = style(n);
          const rg = document.createRange();
          for (let i = 0; i < c.length; i++) {
            rg.setStart(c, i); rg.setEnd(c, i + 1);
            const rs = rg.getClientRects();
            if (!rs.length || rs[0].width === 0) continue;
            // 大きさの違う文字が同じ行に並ぶこともあるので、行の判定は文字の下端で行う
            const bottom = rs[0].bottom;
            left = Math.min(left, rs[0].left);
            if (textOf.top === null) { textOf.top = rs[0].top; textOf.h = rs[0].height; }
            if (lastTop !== null && bottom > lastTop + st.s * 0.6) paras.push([]);
            if (lastTop === null || bottom > lastTop + st.s * 0.6) lastTop = bottom;
            const ch = c.data[i];
            if (/\s/.test(ch) && paras[paras.length - 1].length === 0) continue;
            push(/\s/.test(ch) ? ' ' : ch, st);
          }
        } else if (c.nodeType === 1 && isTextInline(c)) {
          consumed.add(c);
          walk(c);
        }
      }
    };
    const pre = getComputedStyle(el, '::before').content;
    textOf.pre = !!(pre && /^".+"$/.test(pre));
    if (textOf.pre) push(pre.slice(1, -1), style(el));
    walk(el);
    textOf.left = left;
    const out = paras.map(rs => { if (rs.length) rs[rs.length - 1].t = rs[rs.length - 1].t.replace(/\s+$/, ''); return rs.filter(r => r.t); }).filter(rs => rs.length);
    return out.length ? out : null;
  };
  const shapeOf = (el, cs, b) => {
    const cp = cs.clipPath;
    if (cp && cp.startsWith('polygon')) {
      const n = cp.split(',').length;
      const tip = (cp.match(/100% - ([\d.]+)px/) || [0, 18])[1];
      return {shape: n >= 6 && cp.includes(' 50%, 0') ? 'chevron' : 'pentagon', tip: Number(tip)};
    }
    const r = parseFloat(cs.borderTopLeftRadius) || 0;
    const m = Math.min(b.w, b.h);
    if (r >= m / 2 - 0.5 && Math.abs(b.w - b.h) < 1) return {shape: 'ellipse'};
    if (r > 0) return {shape: 'round', r: R(Math.min(r, m / 2))};
    return {shape: 'rect'};
  };
  for (const el of slide.querySelectorAll('*')) {
    if (consumed.has(el) || el.tagName === 'BR') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const rect = el.getBoundingClientRect();
    const b = box(rect);
    // 疑似要素は読み取れないので、位置を todo に残す（線の先の三角は、線の矢印にする）
    const pseudos = [];
    for (const pe of ['::before', '::after']) {
      const p = getComputedStyle(el, pe);
      if (p.content && p.content !== 'none' && p.content !== 'normal')
        pseudos.push({at: b, cls: String(el.className), pseudo: pe, color: hex(p.borderLeftColor) || hex(p.borderTopColor) || hex(p.borderBottomColor) || hex(p.backgroundColor)});
    }
    const mask = cs.webkitMaskImage !== 'none' ? cs.webkitMaskImage : cs.maskImage;
    if (mask && mask !== 'none') {
      const url = (mask.match(/url\("?([^")]+)"?\)/) || [])[1];
      items.push({type: 'icon', ...b, url, color: hex(cs.backgroundColor) || '#555555'});
      continue;
    }
    if (el.tagName === 'IMG' || el.tagName === 'svg') {
      items.push({type: 'img', ...b, src: el.currentSrc || el.src || null});
      continue;
    }
    if (parseFloat(cs.width) === 0 && parseFloat(cs.height) === 0) {
      // 枠線だけで描いた三角（width/height 0 の要素）。色の付いた辺の反対側を向く
      const sides = ['Left', 'Right', 'Top', 'Bottom'].map(s => [s, parseFloat(cs['border' + s + 'Width']), hex(cs['border' + s + 'Color'])]);
      const solid = sides.find(([, w, c]) => w > 0 && c);
      if (solid && b.w > 0 && b.h > 0) {
        const rot = {Bottom: 0, Left: 90, Top: 180, Right: 270}[solid[0]];
        const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
        const w = rot % 180 ? b.h : b.w, h = rot % 180 ? b.w : b.h;  // 回転前の大きさ
        items.push({type: 'box', shape: 'triangle', x: R(cx - w / 2), y: R(cy - h / 2), w: R(w), h: R(h), rot, fill: solid[2]});
      }
      continue;
    }
    const bwPre = ['Top', 'Right', 'Bottom', 'Left'].map(s => cs['border' + s + 'Style'] !== 'none' ? parseFloat(cs['border' + s + 'Width']) : 0);
    const partial = bwPre.some(v => v > 0) && !bwPre.every(v => v > 0);
    todo.push(...pseudos.filter(q => !(hex(cs.backgroundColor) && (b.h <= 3 || b.w <= 3)) && !partial && !/^".+"$/.test(getComputedStyle(el, q.pseudo).content)));
    if (b.w < 1 || b.h < 1) continue;
    const bg = hex(cs.backgroundColor);
    const bw = ['Top', 'Right', 'Bottom', 'Left'].map(s => cs['border' + s + 'Style'] !== 'none' ? parseFloat(cs['border' + s + 'Width']) : 0);
    const bc = ['Top', 'Right', 'Bottom', 'Left'].map((s, i) => bw[i] > 0 ? hex(cs['border' + s + 'Color']) : null).find(c => c);
    const ow = cs.outlineStyle !== 'none' ? parseFloat(cs.outlineWidth) : 0;
    const text = textOf(el);
    const it = {};
    // 細い帯（2〜3px）は線にする
    if (bg && !text && (b.h <= 3 || b.w <= 3)) {
      const horiz = b.w > b.h;
      const pts = horiz ? [[b.x, R(b.y + b.h / 2)], [R(b.x + b.w), R(b.y + b.h / 2)]] : [[R(b.x + b.w / 2), b.y], [R(b.x + b.w / 2), R(b.y + b.h)]];
      const ln = {type: 'line', pts, color: bg, lw: R(horiz ? b.h : b.w)};
      const after = pseudos.find(q => q.pseudo === '::after'), before = pseudos.find(q => q.pseudo === '::before');
      if (after || before) ln.arrow = after && before ? 'both' : after ? 'end' : 'start';
      items.push(ln);
      continue;
    }
    const allSides = bw.every(v => v > 0);
    const someSides = bw.some(v => v > 0) && !allSides;
    if (someSides && bc) {
      // 一部の辺だけの枠線は、線（折れ線）にする
      const [t, r, bo, l] = bw;
      const X1 = b.x + l / 2, X2 = b.x + b.w - r / 2, Y1 = b.y + t / 2, Y2 = b.y + b.h - bo / 2;
      const w = Math.max(...bw);
      // コの字の枠線に疑似要素の三角が付いていれば、始点側の矢印とみなす
      const arrow = pseudos.some(q => !/^".+"$/.test(getComputedStyle(el, q.pseudo).content)) ? {arrow: 'start'} : {};
      if (!t && l && bo && r) items.push({type: 'line', pts: [[R(X1), R(b.y)], [R(X1), R(Y2)], [R(X2), R(Y2)], [R(X2), R(b.y)]], color: bc, lw: w, ...arrow});
      else if (!bo && l && t && r) items.push({type: 'line', pts: [[R(X1), R(b.y + b.h)], [R(X1), R(Y1)], [R(X2), R(Y1)], [R(X2), R(b.y + b.h)]], color: bc, lw: w, ...arrow});
      else {
        if (t) items.push({type: 'line', pts: [[b.x, R(Y1)], [R(b.x + b.w), R(Y1)]], color: bc, lw: t, dash: cs.borderTopStyle === 'dashed'});
        if (bo) items.push({type: 'line', pts: [[b.x, R(Y2)], [R(b.x + b.w), R(Y2)]], color: bc, lw: bo, dash: cs.borderBottomStyle === 'dashed'});
        if (l) items.push({type: 'line', pts: [[R(X1), b.y], [R(X1), R(b.y + b.h)]], color: bc, lw: l, dash: cs.borderLeftStyle === 'dashed'});
        if (r) items.push({type: 'line', pts: [[R(X2), b.y], [R(X2), R(b.y + b.h)]], color: bc, lw: r, dash: cs.borderRightStyle === 'dashed'});
      }
    }
    const framed = (allSides && bc) || (ow && hex(cs.outlineColor));
    if (!bg && !framed && !text) continue;
    if (bg || framed) {
      Object.assign(it, {type: 'box', ...shapeOf(el, cs, b), ...b});
      if (bg) it.fill = bg;
      if (allSides && bc) { it.line = bc; it.lw = bw[0]; const d = bw[0] / 2; Object.assign(it, {x: R(b.x + d), y: R(b.y + d), w: R(b.w - 2 * d), h: R(b.h - 2 * d)}); if (cs.borderTopStyle === 'dashed') it.dash = true; }
      else if (ow) { it.line = hex(cs.outlineColor); it.lw = ow; const d = ow / 2; Object.assign(it, {x: R(b.x - d), y: R(b.y - d), w: R(b.w + 2 * d), h: R(b.h + 2 * d)}); }
    } else {
      Object.assign(it, {type: 'text', ...b});
    }
    if (text) {
      const fs = parseFloat(cs.fontSize);
      const lh = cs.lineHeight === 'normal' ? 1.5 : parseFloat(cs.lineHeight) / fs;
      const ta = cs.textAlign;
      const flex = cs.display.includes('flex');
      let align = ta === 'center' ? 'c' : (ta === 'right' || ta === 'end') ? 'r' : 'l';
      let valign = 't';
      if (flex) {
        const col = cs.flexDirection.startsWith('column');
        if (!col && cs.justifyContent === 'center') align = 'c';
        if (col && cs.alignItems === 'center') align = 'c';
        if ((!col && cs.alignItems === 'center') || (col && cs.justifyContent === 'center')) valign = 'm';
      }
      const pad = ['Left', 'Top', 'Right', 'Bottom'].map(s => R(parseFloat(cs['padding' + s]) + (it.type === 'box' && allSides ? 0 : parseFloat(cs['border' + s + 'Width']) || 0)));
      // アイコンなどと縦に並んだ文字は、上下中央ではなく実際の位置に置く
      const others = [...el.children].some(c => !consumed.has(c) && c.tagName !== 'BR');
      if (others && flex && cs.flexDirection.startsWith('column') && textOf.top !== null) {
        valign = 't';
        pad[1] = R(textOf.top - S.top - it.y - (lh * fs - textOf.h) / 2);
      }
      if (textOf.pre) pad[0] = 0;  // 「・」などの記号を文字の先頭に入れたので、左の余白はなくす
      else if (align === 'l' && isFinite(textOf.left)) pad[0] = R(Math.max(pad[0], textOf.left - S.left - it.x));
      Object.assign(it, {align, valign, pad, lh: R(lh), size: R(fs), paras: text});
    }
    items.push(it);
  }
  return {bg: hex(getComputedStyle(slide).backgroundColor) || hex(getComputedStyle(document.body).backgroundColor) || '#ffffff', items, todo};
}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html', nargs='+')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / 'assets').mkdir(parents=True, exist_ok=True)
    slides, n = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        tool = browser.new_page(device_scale_factor=4)
        for h in a.html:
            page.goto(pathlib.Path(h).resolve().as_uri(), wait_until='networkidle')
            data = page.evaluate(JS)
            items = []
            for it in data['items']:
                if it['type'] in ('icon', 'img'):
                    n += 1
                    name = f'assets/{pathlib.Path(h).stem}_{n:02d}.png'
                    if it['type'] == 'icon':
                        html = (f'<div id="e" style="width:{it["w"]}px;height:{it["h"]}px;background:{it["color"]};'
                                f'-webkit-mask:url({it["url"]}) center/contain no-repeat"></div>')
                    else:
                        html = f'<img id="e" src="{it["src"]}" style="width:{it["w"]}px;height:{it["h"]}px;display:block">'
                    tool.set_content(f'<html><body style="margin:0;background:transparent">{html}</body></html>', wait_until='networkidle')
                    tool.locator('#e').screenshot(path=str(out / name), omit_background=True)
                    items.append({'type': 'image', 'x': it['x'], 'y': it['y'], 'w': it['w'], 'h': it['h'], 'src': name})
                else:
                    items.append(it)
            slide = {'bg': data['bg'], 'items': items, 'source': str(pathlib.Path(h).resolve())}
            if data['todo']:
                slide['todo'] = data['todo']
            slides.append(slide)
        browser.close()
    spec = {'size': [1280, 720], 'slides': slides}
    with open(out / 'spec.json', 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    for i, s in enumerate(slides, 1):
        print(f'スライド{i}: 要素 {len(s["items"])}件、疑似要素の要確認 {len(s.get("todo", []))}件')
    print(out / 'spec.json')


if __name__ == '__main__':
    main()
