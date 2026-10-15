#!/usr/bin/env python3
"""Build the site from src/index.template.html.

    python3 build.py             writes index.html: the production page, which always loads live NEA data
    python3 build.py --preview   writes preview.html: an HTML fragment that falls back to src/snapshot/*.json
                                 when NEA can't be reached (used for sandboxed previews such as Claude artifacts)
    python3 build.py --og        renders src/og.html to og.png (the fixed link-preview image) with headless Chrome
    python3 build.py --icons     renders src/icon.html to the app icons in icons/ (Chrome, plus macOS `sips` to resize)
    python3 build.py --site      writes _site/, what GitHub Pages serves: the page at / and at /north/, /west/ ...,
                                 region pages with link-preview tags and a dated image of NEA's latest readings.
                                 GitHub Actions runs this every 30 minutes (.github/workflows/pages.yml).

The page itself always fetches its data in the visitor's browser. Only the link previews are made ahead of time,
because WhatsApp, Telegram and the rest read a page's preview tags without running its scripts.
"""
import datetime as dt
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
SITE_URL = "https://haze.geewax.org/"
NEA_READINGS = "https://www.haze.gov.sg/api/airquality/jsondata/{ts}"
NEA_ADVISORY = "https://www.nea.gov.sg/api/advisory/latesthazesituationupdate/{ts}"

REGIONS = ["north", "west", "central", "east", "south"]
RNAME = {"north": "North", "south": "South", "east": "East", "west": "West", "central": "Central"}
SUBS = ["ChartPM25", "ChartPM10", "ChartO3", "ChartCO", "ChartSO2"]
# (upper limit, name, band number, colour slot), as in the page
PM_BANDS = [(55, "Normal", 1, 0), (150, "Elevated", 2, 2), (250, "High", 3, 3), (float("inf"), "Very High", 4, 4)]
PSI_BANDS = [(50, "Good", 0), (100, "Moderate", 1), (200, "Unhealthy", 2), (300, "Very Unhealthy", 3), (float("inf"), "Hazardous", 4)]
PSI_START = [0, 51, 101, 201, 301]

DEFAULT_META = {
    "title": "Haze Status: Singapore air quality, by region",
    "description": "The 1-hr PM2.5 for what to do in the next hour, and NEA's 24-hr PSI forecast to plan ahead. Live, for your region.",
    "url": SITE_URL,
    "image": SITE_URL + "og.png",
    "alt": "Haze Status: the 1-hr PM2.5 band scale for right now and the 24-hr PSI scale for planning ahead.",
}
FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient id='b' x1='0' y1='0' x2='0' y2='1'%3E%3Cstop offset='0' stop-color='%23A9A493'/%3E%3Cstop offset='1' stop-color='%23E6DCC6'/%3E%3C/linearGradient%3E%3ClinearGradient id='s' x1='0' y1='0' x2='0' y2='1'%3E%3Cstop offset='.15' stop-color='%23F2742B'/%3E%3Cstop offset='1' stop-color='%23F2742B' stop-opacity='.15'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='8' fill='url(%23b)'/%3E%3Ccircle cx='16' cy='16' r='10' fill='url(%23s)'/%3E%3C/svg%3E"


def head(meta):
    a = {k: html.escape(v, quote=True) for k, v in meta.items()}
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{a['description']}">
<meta name="theme-color" content="#AFA796">
<link rel="canonical" href="{a['url']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Haze Status">
<meta property="og:title" content="{a['title']}">
<meta property="og:description" content="{a['description']}">
<meta property="og:url" content="{a['url']}">
<meta property="og:image" content="{a['image']}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{a['alt']}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-title" content="Haze">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
"""


def js(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


def app_source():
    page = (SRC / "index.template.html").read_text()
    # Bundle the QR code library into the page so the site has no third-party script dependency
    qr = (ROOT / "vendor" / "qrcode-generator-2.0.4.js").read_text()
    assert "</script" not in qr
    page = page.replace("/*VENDOR:qrcode*/", qr)
    # Translations (English, Chinese, Malay, Tamil), kept in their own file so they are easy to review
    i18n = (SRC / "i18n.js").read_text()
    assert "</script" not in i18n
    return page.replace("/*I18N*/", i18n)


def full_page(meta):
    top, body = app_source().split("</style>", 1)
    return f"{head(meta)}{top}</style>\n</head>\n<body>{body}</body>\n</html>\n"


# ---------- headless Chrome ----------

def chrome_path():
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return os.environ.get("CHROME") or (mac if os.path.exists(mac) else shutil.which("google-chrome") or shutil.which("chromium"))


def screenshot(src_uri, out, size="1200,630"):
    args = [chrome_path(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={size}",
            "--virtual-time-budget=6000", f"--screenshot={out}", src_uri]
    if os.environ.get("CI"):
        args.insert(1, "--no-sandbox")
    subprocess.run(args, check=True, capture_output=True, timeout=120)


def render_icons():
    out = ROOT / "icons"
    out.mkdir(exist_ok=True)
    src = (SRC / "icon.html").as_uri()
    screenshot(src, out / "icon-512.png", "512,512")
    screenshot(src + "#maskable", out / "maskable-512.png", "512,512")
    # headless Chrome won't lay out a window narrower than about 500px, so draw at 512 and scale down
    for name, px in [("icon-192.png", 192), ("apple-touch-icon.png", 180)]:
        subprocess.run(["sips", "-z", str(px), str(px), str(out / "icon-512.png"), "--out", str(out / name)], check=True, capture_output=True)
    for f in sorted(out.iterdir()):
        print(f"wrote {f.relative_to(ROOT)} ({f.stat().st_size:,} bytes)")


def render_og():
    out = ROOT / "og.png"
    screenshot((SRC / "og.html").as_uri(), out)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")


# ---------- NEA readings, worked out the same way as the page ----------

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "haze.geewax.org link previews (+https://github.com/jgeewax/haze)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


MON = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def parse_nea(s):  # "15 Oct 2026 09AM", Singapore time
    d, mon, y, hm = s.split()
    return dt.datetime(int(y), MON[mon], int(d), int(hm[:-2]) % 12 + (12 if hm.endswith("PM") else 0))


def hour(t):
    return f"{t.hour % 12 or 12}{'am' if t.hour < 12 else 'pm'}"


def day(d):
    return f"{d:%a} {d.day} {d:%b}"


def readings(aq, adv):
    def val(chart, r, i):
        try:
            v = aq[chart][RNAME[r]]["Data"][i]["value"]
        except (KeyError, IndexError, TypeError):
            return None
        return v if v and v > 0 else None

    def psi(r, i):
        vs = [v for v in (val(c, r, i) for c in SUBS) if v]
        return max(vs) if vs else None

    li = len(aq["Chart1HRPM25"]["North"]["Data"]) - 1
    while li > 0 and any(val("Chart1HRPM25", r, li) is None or psi(r, li) is None for r in REGIONS):
        li -= 1
    asof = parse_nea(aq["Chart1HRPM25"]["North"]["Data"][li]["dateTime"])
    regions = {}
    for r in REGIONS:
        pm, ps = round(val("Chart1HRPM25", r, li)), round(psi(r, li))
        b = next(x for x in PM_BANDS if pm <= x[0])
        k = next(i for i, x in enumerate(PSI_BANDS) if ps <= x[0])
        regions[r] = {"name": RNAME[r], "pm": pm, "psi": ps, "pmBand": {"name": b[1], "n": b[2], "c": b[3]},
                      "psiBand": {"name": PSI_BANDS[k][1], "c": PSI_BANDS[k][2], "k": k}}
    fc = None
    text = re.sub(r"^[^:]*:\s*", "", (adv or {}).get("AirQualityBlurb") or "").strip()
    # NEA sometimes qualifies a band, e.g. "Unhealthy to Low Very Unhealthy"; the band is what follows the qualifier
    parts = [re.sub(r"^(low|lower|mid|middle|high|higher|upper)\s+", "", p.strip(), flags=re.I) for p in re.split(r"\s+to\s+", text, flags=re.I)]
    idx = [i for part in parts for i, b in enumerate(PSI_BANDS) if b[1].lower() == part.lower()]
    issued = (adv or {}).get("DateOfArticle")
    if idx and issued:
        issued = dt.datetime.fromisoformat(issued).replace(tzinfo=None)  # NEA gives +08:00
        fdate = issued.date() + dt.timedelta(days=1 if issued.hour >= 12 else 0)   # an evening forecast is for the next day
        rel = (fdate - asof.date()).days
        lo, hi = min(idx), max(idx)
        if rel >= 0:
            fc = {"lo": lo, "hi": hi, "hiC": PSI_BANDS[hi][2], "day": day(fdate),
                  "name": PSI_BANDS[lo][1] if lo == hi else f"{PSI_BANDS[lo][1]} to {PSI_BANDS[hi][1]}",
                  "range": f"{PSI_START[lo]}+" if hi == 4 else f"{PSI_START[lo]}–{int(PSI_BANDS[hi][0])}",
                  "when": "today" if rel == 0 else "tomorrow" if rel == 1 else day(fdate)}
    return {"asOf": f"{hour(asof)}, {day(asof)}", "day": day(asof), "stamp": f"{asof:%Y%m%d%H}", "regions": regions, "fc": fc}


def mix(a, b, t):
    pa, pb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def sky(pm):  # the page's light-theme sky
    t = min(1, pm / 260)
    clear, hazy, thick = ("#5BA6E6", "#D4EAF9"), ("#AFA796", "#E6DFD1"), ("#8E7258", "#D9BE9C")
    pick = lambda i: mix(clear[i], hazy[i], t * 2) if t < .5 else mix(hazy[i], thick[i], (t - .5) * 2)
    return {"top": pick(0), "bot": pick(1), "ink": "#17222B", "t": t}


def preview_text(R, target):
    f, r = R["fc"], R["regions"][target]
    outlook = f"Forecast {f['when']}: {f['name']} (PSI {f['range']})" if f else "No PSI forecast issued"
    title = f"{r['name']} at {R['asOf']}: PM2.5 {r['pm']} ({r['pmBand']['name']}), PSI {r['psi']} ({r['psiBand']['name']})"
    desc = f"{outlook}. A snapshot from NEA readings; tap for the live numbers."
    alt = f"{r['name']} at {R['asOf']}: 1-hr PM2.5 {r['pm']} µg/m³, {r['pmBand']['name']}; 24-hr PSI {r['psi']}, {r['psiBand']['name']}. {outlook}."
    return title, desc, alt


def build_site():
    out = ROOT / "_site"
    shutil.rmtree(out, ignore_errors=True)
    (out / "og").mkdir(parents=True)
    ts = int(dt.datetime.now().timestamp() * 1000)
    R = None
    try:
        aq = fetch(NEA_READINGS.format(ts=ts))
        try:
            adv = fetch(NEA_ADVISORY.format(ts=ts))
        except Exception as e:
            print(f"NEA advisory unavailable ({e}); previews will show no forecast")
            adv = None
        R = readings(aq, adv)
        print(f"NEA readings at {R['asOf']}")
    except Exception as e:
        print(f"NEA readings unavailable ({e}); using the fixed preview image")
    tpl = (SRC / "og-live.html").read_text()
    # The bare domain keeps the fixed preview (og.png, no numbers): people type it by hand, so chat apps reuse whatever
    # preview they saved first, and a saved copy must never show stale readings. Region pages get a dated live preview;
    # share links add ?at=<hour>, so chat apps fetch a fresh one each hour.
    for target in [None] + REGIONS:
        meta = dict(DEFAULT_META, url=SITE_URL + (f"{target}/" if target else ""))
        if R and target:
            with tempfile.TemporaryDirectory() as d:
                card = pathlib.Path(d) / "card.html"
                card.write_text(tpl.replace("/*DATA*/null", js({**R, "target": target, "sky": sky(R["regions"][target]["pm"])})))
                screenshot(card.as_uri(), out / "og" / f"{target}.png")
            title, desc, alt = preview_text(R, target)
            # chat apps also cache images by address, so the address changes whenever the image does
            v = hashlib.sha1((out / "og" / f"{target}.png").read_bytes()).hexdigest()[:10]
            meta.update(title=title, description=desc, alt=alt, image=f"{SITE_URL}og/{target}.png?v={v}")
        dest = out / target / "index.html" if target else out / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(full_page(meta))
        print(f"wrote {dest.relative_to(ROOT)}: {meta['title']}")
    for f in ["og.png", "CNAME", "manifest.webmanifest", "sw.js"]:
        shutil.copy(ROOT / f, out / f)
    shutil.copytree(ROOT / "icons", out / "icons")


def main():
    flags = sys.argv[1:]
    if "--og" in flags:
        return render_og()
    if "--icons" in flags:
        return render_icons()
    if "--site" in flags:
        return build_site()
    if "--preview" in flags:
        page = app_source()
        aq = json.loads((SRC / "snapshot" / "aq.json").read_text())
        adv = json.loads((SRC / "snapshot" / "adv.json").read_text())
        page = page.replace("/*AQ*/null", js(aq)).replace("/*ADV*/null", js(adv))
        out = ROOT / "preview.html"
    else:
        page = full_page(DEFAULT_META)
        out = ROOT / "index.html"
    out.write_text(page)
    print(f"wrote {out.relative_to(ROOT)} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
