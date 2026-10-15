#!/usr/bin/env python3
"""Build the site from src/index.template.html.

    python3 build.py             writes index.html: the production page, which always loads live NEA data
    python3 build.py --preview   writes preview.html: an HTML fragment that falls back to src/snapshot/*.json
                                 when NEA can't be reached (used for sandboxed previews such as Claude artifacts)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="Singapore haze, clearly: the 1-hr PM2.5 for what to do now and the 24-hr PSI forecast for planning ahead, from NEA data.">
<meta name="theme-color" content="#AFA796">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 28 28'%3E%3Crect width='28' height='28' rx='7' fill='%23AFA796'/%3E%3Ccircle cx='14' cy='11' r='6' fill='%2317222B'/%3E%3Cpath d='M5 18h18M8 22h12' stroke='%2317222B' stroke-width='2.2' stroke-linecap='round'/%3E%3C/svg%3E">
"""


def js(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


def main():
    preview = "--preview" in sys.argv[1:]
    page = (SRC / "index.template.html").read_text()
    if preview:
        aq = json.loads((SRC / "snapshot" / "aq.json").read_text())
        adv = json.loads((SRC / "snapshot" / "adv.json").read_text())
        page = page.replace("/*AQ*/null", js(aq)).replace("/*ADV*/null", js(adv))
        out = ROOT / "preview.html"
    else:
        head, body = page.split("</style>", 1)
        page = f"{HEAD}{head}</style>\n</head>\n<body>{body}</body>\n</html>\n"
        out = ROOT / "index.html"
    out.write_text(page)
    print(f"wrote {out.relative_to(ROOT)} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
