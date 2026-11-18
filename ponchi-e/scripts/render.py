#!/usr/bin/env python3
"""Render a 1280x720 HTML slide to a 16:9 PNG (2x = 2560x1440).

  render.py <slide.html> <out.png>

After rendering, it checks the slide and prints warnings:
  - text smaller than the minimum size (16px; footer 13px)
  - panels (.soft / .soft-gray / .card) with a large empty area at the bottom
  - a large empty area below the content
  - text overflowing the slide
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

CHECK_JS = """
([MIN_TEXT, MIN_FOOTER, MAX_GAP]) => {
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
  // 2) パネル下部の空き
  const panels = document.querySelectorAll('.soft, .soft-gray, .card, [data-panel]');
  panels.forEach(p => {
    const r = p.getBoundingClientRect();
    if (r.height < 120) return;
    let bottom = r.top;
    p.querySelectorAll('*').forEach(c => {
      const cr = c.getBoundingClientRect();
      if (cr.width && cr.height) bottom = Math.max(bottom, cr.bottom);
    });
    if (bottom > r.bottom + 1) {
      out.push(`パネルからはみ出し（${Math.round(bottom - r.bottom)}px）：「${(p.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 16)}…」`);
      return;
    }
    const gap = r.bottom - bottom - parseFloat(getComputedStyle(p).paddingBottom);
    if (gap > MAX_GAP) {
      const label = (p.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 16);
      out.push(`パネルの下に${Math.round(gap)}pxの空き：「${label}…」 → 中身を大きくするか、パネルを詰める`);
    }
  });
  // 3) コンテンツ全体の下の空き
  const content = document.querySelector('.content');
  if (content) {
    const r = content.getBoundingClientRect(); let bottom = r.top;
    content.querySelectorAll('*').forEach(c => { const cr = c.getBoundingClientRect(); if (cr.height) bottom = Math.max(bottom, cr.bottom); });
    if (r.bottom - bottom > MAX_GAP) out.push(`コンテンツの下に${Math.round(r.bottom - bottom)}pxの空き → 図を大きくする`);
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
    warnings = page.evaluate(CHECK_JS, [MIN_TEXT, MIN_FOOTER, MAX_GAP])
    browser.close()
print(sys.argv[2])
for w in warnings:
    print("WARN:", w)
