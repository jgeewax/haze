#!/usr/bin/env python3
"""Build the site from src/index.template.html.

    python3 build.py             writes index.html: the production page, which always loads live NEA data
    python3 build.py --preview   writes preview.html: an HTML fragment that falls back to src/snapshot/*.json
                                 when NEA can't be reached (used for sandboxed previews such as Claude artifacts)
    python3 build.py --og        renders src/og.html to og.png (the link-preview image) with headless Chrome
"""
import json
import pathlib
import subprocess
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
<link rel="canonical" href="https://haze.geewax.org/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Haze">
<meta property="og:title" content="Haze: Singapore air quality, by region">
<meta property="og:description" content="The 1-hr PM2.5 for what to do in the next hour, and NEA's 24-hr PSI forecast to plan ahead. Live, for your region.">
<meta property="og:url" content="https://haze.geewax.org/">
<meta property="og:image" content="https://haze.geewax.org/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Haze: the 1-hr PM2.5 band scale for right now and the 24-hr PSI scale for planning ahead.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 28 28'%3E%3Crect width='28' height='28' rx='7' fill='%23AFA796'/%3E%3Ccircle cx='14' cy='11' r='6' fill='%2317222B'/%3E%3Cpath d='M5 18h18M8 22h12' stroke='%2317222B' stroke-width='2.2' stroke-linecap='round'/%3E%3C/svg%3E">
"""


def js(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render_og():
    out = ROOT / "og.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,630",
                    "--virtual-time-budget=5000", f"--screenshot={out}", (SRC / "og.html").as_uri()],
                   check=True, capture_output=True)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")


def main():
    if "--og" in sys.argv[1:]:
        return render_og()
    preview = "--preview" in sys.argv[1:]
    page = (SRC / "index.template.html").read_text()
    # Bundle the QR code library into the page so the site has no third-party script dependency
    qr = (ROOT / "vendor" / "qrcode-generator-2.0.4.js").read_text()
    assert "</script" not in qr
    page = page.replace("/*VENDOR:qrcode*/", qr)
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
