#!/usr/bin/env python3
"""Render a 1280x720 HTML slide to a 16:9 PNG (2x = 2560x1440).

  render.py <slide.html> <out.png>

After rendering, it checks the slide and prints warnings:
  - text smaller than the minimum size (16px; footer 13px)
  - panels (.soft / .soft-gray / .card) with a large empty area at the bottom
  - a large empty area below the content
  - text overflowing the slide
  - cards and panels with too little inner padding
  - numbers (.num) larger than 72px
  - too much or too little text in the content (over 500 / under 300 characters)
  - card panels packed too tightly (no room left for the standard card padding)
  - sparse cards (content fills less than half of the card height)
  - panel headings (.panel > .pill) smaller than 20px
  - any text larger than 72px, even outside .num
  - four or more numbers with the same unit but no chart (<svg>) or pictogram (.person)
  - no picture at all (no illustration and no icon badge) in the content
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

if len(sys.argv) != 3:
    sys.exit(__doc__)

MIN_TEXT = 16      # 本文・補足の最小サイズ
MIN_FOOTER = 13    # 出所・コピーライト
MAX_GAP = 48       # パネルの下に残してよい空き（px）
MAX_NUM = 72       # 数字（.num）の最大サイズ（px）
MAX_CHARS = 500    # コンテンツの文字数の上限
MIN_CHARS = 300    # コンテンツの文字数の下限（これ未満は情報が足りない）
MIN_SLACK = 0.0    # カードを並べたパネルで、カードの内側の余白（--pad-card）を確保したうえで残す空きの最小割合
MIN_FILL = 0.5     # カードの中身が占める高さの最小割合（これ未満は間延び）

CHECK_JS = """
([MIN_TEXT, MIN_FOOTER, MAX_GAP, MAX_NUM, MAX_CHARS, MIN_SLACK, MIN_FILL, MIN_CHARS]) => {
  const out = [];
  const isFooter = el => el.closest('.source, .page-info');
  // 1) 文字の大きさ
  const small = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode; const s = t.textContent.trim();
    if (!s) continue;
    const el = t.parentElement; const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const fs = parseFloat(cs.fontSize);
    const min = isFooter(el) ? MIN_FOOTER : MIN_TEXT;
    if (fs < min - 0.01) {
      // 単位の添え字（数字の直後の小さな文字）は除く
      if (el.closest('.num') && s.length <= 3) continue;
      const k = fs + 'px';
      if (!small.has(k)) small.set(k, []);
      if (small.get(k).length < 3) small.get(k).push(s.slice(0, 20));
    }
  }
  for (const [k, v] of small) out.push(`文字が小さい（${k} < ${MIN_TEXT}px）：${v.join(' / ')}`);
  // 要素の中身が占める上端・下端（子要素の箱。文字だけの要素は文字の行の範囲）
  const extent = el => {
    let top = Infinity, bot = -Infinity;
    const add = q => { if (q.width && q.height) { top = Math.min(top, q.top); bot = Math.max(bot, q.bottom); } };
    el.querySelectorAll('*').forEach(d => add(d.getBoundingClientRect()));
    if (!el.children.length) { const rg = document.createRange(); rg.selectNodeContents(el); for (const q of rg.getClientRects()) add(q); }
    return bot > top ? [top, bot] : null;
  };
  // 2) パネル下部の空き（中身が上に寄って、下に空きが固まっている）
  const panels = document.querySelectorAll('.soft, .soft-gray, [data-panel]');
  document.querySelectorAll('.soft, .soft-gray, .card, [data-panel]').forEach(p => {
    const r = p.getBoundingClientRect();
    if (r.height < 120) return;
    const e = extent(p); if (!e) return;
    const [top, bottom] = e;
    if (bottom > r.bottom + 1) {
      out.push(`パネルからはみ出し（${Math.round(bottom - r.bottom)}px）：「${(p.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 16)}…」`);
      return;
    }
    const pcs = getComputedStyle(p);
    const gap = r.bottom - bottom - parseFloat(pcs.paddingBottom);
    const topGap = top - r.top - parseFloat(pcs.paddingTop);
    if (gap - topGap > MAX_GAP) {
      const label = (p.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 16);
      out.push(`パネルの下に${Math.round(gap)}pxの空き：「${label}…」 → 中身を大きくするか、パネルを詰める`);
    }
  });
  // 2b) 詰まりすぎのパネル：カードを並べたパネルで、カードの中身と内側の余白、要素の間を除いた空きの割合を測る
  panels.forEach(p => {
    const kids = [...p.children];
    if (!kids.some(c => c.classList.contains('card'))) return;
    const cs = getComputedStyle(p);
    const inner = p.getBoundingClientRect().height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    let used = (kids.length - 1) * (parseFloat(cs.rowGap) || 0);
    kids.forEach(c => {
      const ccs = getComputedStyle(c);
      if (c.classList.contains('card') || parseFloat(ccs.flexGrow) > 0) {
        const e = extent(c);
        used += (e ? e[1] - e[0] : 0) + parseFloat(ccs.paddingTop) + parseFloat(ccs.paddingBottom);
      } else used += c.getBoundingClientRect().height;
    });
    const slack = (inner - used) / inner;
    if (inner > 200 && slack < MIN_SLACK) {
      const label = (p.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 16);
      out.push(`パネルが詰まりすぎ（カードの内側の余白を確保すると${Math.round(-slack * inner)}px足りない）：「${label}…」 → 文字やカードを減らす`);
    }
  });
  // 2d) 内側の余白が狭すぎるカード・パネル
  document.querySelectorAll('.card, .panel').forEach(el => {
    const cs = getComputedStyle(el);
    const v = Math.min(parseFloat(cs.paddingTop), parseFloat(cs.paddingBottom));
    const h = Math.min(parseFloat(cs.paddingLeft), parseFloat(cs.paddingRight));
    if (el.getBoundingClientRect().height > 60 && (v < 14 || h < 18))
      out.push(`内側の余白が狭い（上下${v}px・左右${h}px。カードは上下18px・左右24px、パネルは24px）：「${el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 16)}…」`);
  });
  // 2e) 間延びしたカード：中身がカードの高さの半分に満たない
  document.querySelectorAll('.card').forEach(c => {
    const r = c.getBoundingClientRect(); const cs = getComputedStyle(c);
    const inner = r.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    const e = extent(c); if (!e || inner < 60) return;
    const fill = (e[1] - e[0]) / inner;
    if (fill < MIN_FILL && inner - (e[1] - e[0]) > 40)
      out.push(`間延びしたカード（中身が高さの${Math.round(fill * 100)}%）：「${c.textContent.trim().replace(/\\s+/g, ' ').slice(0, 16)}…」 → イラストや数字を大きくする、説明を足す、カードを低くする`);
  });
  // 2f) 絵（アイコンの絵・イラスト）
  const content0 = document.querySelector('.content');
  if (content0) {
    const pics = [...content0.querySelectorAll('img, .badge, .icon, .person')].filter(i => i.getBoundingClientRect().height >= (i.matches('img, .badge') ? 48 : 28));
    if (!pics.length) out.push('絵がない → 主な要素に、その要素を表すイラストかアイコン（.badge）を添える');
    const ill = [...content0.querySelectorAll('img')].filter(i => i.getBoundingClientRect().height >= 80).length;
    if (ill > 3) out.push(`イラストが多い（${ill}点）→ 1〜3点にし、要素と対応しない飾りのイラストは外す`);
  }
  // 2g) パネルの見出し（.panel > .pill）が小さい
  document.querySelectorAll('.panel > .pill').forEach(pl => {
    const fs = parseFloat(getComputedStyle(pl).fontSize);
    if (fs < 20) out.push(`パネルの見出しが小さい（${fs}px < 20px）：「${pl.textContent.trim().slice(0, 16)}」`);
  });
  // 2c) 大きすぎる数字
  document.querySelectorAll('.num').forEach(n => {
    const fs = parseFloat(getComputedStyle(n).fontSize);
    if (fs > MAX_NUM) out.push(`数字が大きすぎる（${fs}px > ${MAX_NUM}px）：「${n.textContent.trim()}」`);
  });
  // .num を使っていない大きすぎる文字（約89%減 などを独自のスタイルで書いた場合）
  document.querySelectorAll('.content *').forEach(el => {
    if (el.closest('.num') || ![...el.childNodes].some(c => c.nodeType === 3 && c.textContent.trim())) return;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs > MAX_NUM) out.push(`文字が大きすぎる（${fs}px > ${MAX_NUM}px）：「${el.textContent.trim().slice(0, 12)}」 → .num を使い、前後の文字は <small> で半分にする`);
  });
  // 2h) 数字があるのにグラフ・図解がない
  const c2 = document.querySelector('.content');
  if (c2) {
    // 同じ単位の数字が4つ以上並んでいたら、グラフで見せるべき数字の列とみなす
    const units = {};
    for (const m of c2.innerText.matchAll(/\\d[\\d,.]*\\s*(?:万|億)?\\s*(名|人|%|％|件|社|円|倍|時間|pt)/g)) units[m[1]] = (units[m[1]] || 0) + 1;
    const [unit, n] = Object.entries(units).sort((a, b) => b[1] - a[1])[0] || ['', 0];
    const charts = [...c2.querySelectorAll('svg, .person')].filter(e => { const q = e.getBoundingClientRect(); return e.classList.contains('person') || (q.width >= 120 && q.height >= 60); });
    if (n >= 4 && !charts.length)
      out.push(`「${unit}」の数字が${n}個あるのにグラフ・図解がない → SKILL.md の「数字の見せ方」から図を選び、references/charts_*.html の <svg> を使う（人数なら人型 .person）`);
  }
  // 3) コンテンツ全体の下の空き
  const content = document.querySelector('.content');
  if (content) {
    const r = content.getBoundingClientRect(); let bottom = r.top;
    content.querySelectorAll('*').forEach(c => { const cr = c.getBoundingClientRect(); if (cr.height) bottom = Math.max(bottom, cr.bottom); });
    if (r.bottom - bottom > MAX_GAP) out.push(`コンテンツの下に${Math.round(r.bottom - bottom)}pxの空き → 図を大きくする`);
  }
  // 3b) 文字数
  if (content) {
    const n = content.innerText.replace(/\\s/g, '').length;
    if (n > MAX_CHARS) out.push(`文字が多い（${n}字 > ${MAX_CHARS}字。目安は350〜450字）→ 言い回しを短くする`);
    if (n < MIN_CHARS) out.push(`情報が少ない（${n}字 < ${MIN_CHARS}字。目安は350〜450字）→ 各要素に中身・具体例・補足・示唆を足す`);
  }
  // 4) フッター（出所）との重なり
  const src = document.querySelector('.source');
  if (content && src && src.textContent.trim()) {
    const st = src.getBoundingClientRect().top; let cb = 0;
    content.querySelectorAll('*').forEach(c => { const cr = c.getBoundingClientRect(); if (cr.height) cb = Math.max(cb, cr.bottom); });
    if (cb > st - 4) out.push(`コンテンツが出所に重なっている（${Math.round(cb - st + 4)}px）`);
  }
  // 5) スライドからのはみ出し
  document.querySelectorAll('.slide *').forEach(el => {
    const cr = el.getBoundingClientRect();
    if (cr.width && (cr.right > 1281 || cr.bottom > 721) && el.textContent.trim())
      out.push(`はみ出し：「${el.textContent.trim().slice(0, 16)}」`);
  });
  return [...new Set(out)].slice(0, 20);
}
"""

src = pathlib.Path(sys.argv[1]).resolve()
with sync_playwright() as p:
    # CHROMIUM_PATH があればそのブラウザを使う（Playwright のブラウザが別の場所にある環境向け）
    exe = os.environ.get("CHROMIUM_PATH")
    browser = p.chromium.launch(**({"executable_path": exe} if exe else {}))
    page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    page.goto(src.as_uri(), wait_until="networkidle")
    page.screenshot(path=sys.argv[2], clip={"x": 0, "y": 0, "width": 1280, "height": 720})
    warnings = page.evaluate(CHECK_JS, [MIN_TEXT, MIN_FOOTER, MAX_GAP, MAX_NUM, MAX_CHARS, MIN_SLACK, MIN_FILL, MIN_CHARS])
    browser.close()
print(sys.argv[2])
for w in warnings:
    print("WARN:", w)
