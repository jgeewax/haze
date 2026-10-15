# Haze Status

A calmer view of Singapore's haze readings, at [haze.geewax.org](https://haze.geewax.org).

It is a single static page. The visitor's browser loads the data straight from the National Environment Agency, with no server involved:

| Data | Endpoint |
| --- | --- |
| 1-hr PM2.5 and PSI sub-indices, 24 hours, five regions | `https://www.haze.gov.sg/api/airquality/jsondata/{timestamp}` |
| 24-hr PSI forecast and NEA's statement | `https://www.nea.gov.sg/api/advisory/latesthazesituationupdate/{timestamp}` |

Both endpoints send `Access-Control-Allow-Origin: *`. The `{timestamp}` is only a cache-buster. The 24-hr PSI is the highest of the PM2.5, PM10, O3, CO and SO2 sub-indices. Advice text follows NEA's poster *How to plan your outdoor activities during haze* (June 2026).

Settings (region, group, start tab) are saved in the browser's `localStorage`.

**Location.** "Use my location" asks the browser for its position (this only works on https), then picks the nearest named neighbourhood in `AREAS` and uses that neighbourhood's NEA region.

**Sharing.** The share sheet offers WhatsApp, Telegram, copy link, copy text, the system share sheet where the browser has one, a QR code, and a 1080×1350 picture card drawn on a canvas. The card carries its own QR code, so a forwarded screenshot still leads back to the site. Shared links name a region, e.g. `https://haze.geewax.org/west/` (the older `#west` form still works). A first-time visitor adopts that region; a returning visitor sees it for that visit only and keeps their saved default. The QR codes come from [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 2.0.4 (MIT), kept in `vendor/` and bundled into the page at build time. `og.png` is the fixed link-preview image, used when live previews can't be made (see Deploying).

## Building

Edit `src/index.template.html`, then:

```sh
python3 build.py             # writes index.html, the page on its own, for opening locally
python3 build.py --preview   # writes preview.html, which falls back to src/snapshot/ when NEA is unreachable
python3 build.py --og        # re-renders og.png from src/og.html (needs Google Chrome)
python3 build.py --site      # writes _site/: the page at / and /north/ … /south/, with live link previews
```

## Deploying

GitHub Actions (`.github/workflows/pages.yml`) runs `build.py --site` and deploys `_site/` to GitHub Pages on every push to `main` and every 30 minutes. `CNAME` sets the custom domain.

**Link previews.** WhatsApp, Telegram and other apps read a page's preview tags without running its scripts, so previews can't come from the live page. Each 30-minute build therefore fetches NEA's latest readings and does two things:

- writes one page per region, at `/north/`, `/west/` and so on, whose preview title gives that region's numbers, e.g. "Haze in West: PM2.5 104 (Elevated), PSI 208 (Very Unhealthy)";
- renders a matching 1200×630 image from `src/og-live.html`, plus an island overview for the bare domain.

Share links point at these region pages. If NEA can't be reached during a build, the pages fall back to the fixed `og.png`. The page itself always loads its numbers live in the browser.

`index.html` at the repository root is the same page without the region previews, kept for opening locally.

This is an unofficial project. It is not affiliated with NEA.
