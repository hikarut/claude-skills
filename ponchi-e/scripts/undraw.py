#!/usr/bin/env python3
"""unDraw illustration search / download (recolored to the slide main color).

  undraw.py search <keyword>          # list title and URL of matches (English keywords)
  undraw.py get <url> <out.svg> [--color #a100ff]
"""
import json
import re
import subprocess
import sys
import urllib.parse

UNDRAW_DEFAULT = "#6c63ff"  # unDraw default accent color
MAIN_COLOR = "#a100ff"


def fetch(url):
    # curl uses the system certificate store (python.org builds may lack one)
    return subprocess.run(["curl", "-sfL", "--max-time", "30", url],
                          capture_output=True, text=True, check=True).stdout


def search(keyword):
    data = json.loads(fetch("https://undraw.co/api/search?q=" + urllib.parse.quote(keyword)))
    for item in data.get("results", []):
        print(f"{item['title']}\t{item['media']}")


def get(url, out, color=MAIN_COLOR):
    svg = re.sub(UNDRAW_DEFAULT, color, fetch(url), flags=re.IGNORECASE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "search":
        search(" ".join(args[1:]))
    elif len(args) >= 3 and args[0] == "get":
        color = args[args.index("--color") + 1] if "--color" in args else MAIN_COLOR
        get(args[1], args[2], color)
    else:
        sys.exit(__doc__)
