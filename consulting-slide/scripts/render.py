#!/usr/bin/env python3
"""Render a 1280x720 HTML slide to a 16:9 PNG (2x = 2560x1440).

  render.py <slide.html> <out.png>
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

if len(sys.argv) != 3:
    sys.exit(__doc__)

src = pathlib.Path(sys.argv[1]).resolve()
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    page.goto(src.as_uri(), wait_until="networkidle")
    page.screenshot(path=sys.argv[2], clip={"x": 0, "y": 0, "width": 1280, "height": 720})
    browser.close()
print(sys.argv[2])
