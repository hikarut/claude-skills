#!/usr/bin/env python3
"""unDraw illustration search / download (recolored to the slide main color).

  undraw.py search <keyword>          # list title and URL of matches (English keywords)
  undraw.py get <url> <out.svg> [--color #RRGGBB]
  undraw.py recolor <in.svg> <out.svg> [--color #RRGGBB]   # recolor a saved illustration (e.g. examples/il_*.svg)

--color defaults to the main color in theme.css.
"""
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

UNDRAW_DEFAULT = "#6c63ff"  # unDraw default accent color
EXAMPLE_COLOR = "#a100ff"   # color of the saved example illustrations
THEME = pathlib.Path(__file__).resolve().parent.parent / "theme.css"
MAIN_COLOR = re.search(r"--main:\s*(#[0-9a-fA-F]{3,8})", THEME.read_text(encoding="utf-8")).group(1)


def fetch(url):
    # curl uses the system certificate store (python.org builds may lack one)
    return subprocess.run(["curl", "-sfL", "--max-time", "30", url],
                          capture_output=True, text=True, check=True).stdout


def search(keyword):
    data = json.loads(fetch("https://undraw.co/api/search?q=" + urllib.parse.quote(keyword)))
    for item in data.get("results", []):
        print(f"{item['title']}\t{item['media']}")


def save(svg, out, color):
    svg = re.sub(f"{UNDRAW_DEFAULT}|{EXAMPLE_COLOR}", color, svg, flags=re.IGNORECASE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "search":
        search(" ".join(args[1:]))
    elif len(args) >= 3 and args[0] in ("get", "recolor"):
        color = args[args.index("--color") + 1] if "--color" in args else MAIN_COLOR
        svg = fetch(args[1]) if args[0] == "get" else pathlib.Path(args[1]).read_text(encoding="utf-8")
        save(svg, args[2], color)
    else:
        sys.exit(__doc__)
