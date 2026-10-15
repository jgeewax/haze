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

**Sharing.** Now and My day end with a share panel: a thumbnail of the picture card beside a big Share picture button. On phones it opens the share menu with the picture attached (pick WhatsApp there); on computers it copies the picture, ready to paste into WhatsApp Web. The card is drawn as soon as a screen shows, so the share happens on the tap itself. Underneath: Send as text (a WhatsApp message with the link), Copy link and More. The share sheet offers WhatsApp, Telegram, copy link, copy text, the system share sheet where the browser has one, a QR code, and a 1080×1350 picture card drawn on a canvas. The card carries its own QR code, so a forwarded screenshot still leads back to the site. Shared links name a region, e.g. `https://haze.geewax.org/west/` (the older `#west` form still works). A first-time visitor adopts that region; a returning visitor sees it for that visit only and keeps their saved default. The QR codes come from [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 2.0.4 (MIT), kept in `vendor/` and bundled into the page at build time. `og.png` is the fixed link-preview image, used when live previews can't be made (see Deploying).

**Analytics.** [GoatCounter](https://geewaxhaze.goatcounter.com) counts visits and taps, without cookies, and only on haze.geewax.org; local copies and previews aren't counted. The page view records the landing path (`/` or `/west/` …). Events include:

- `arrived/shared-link/<region>`, `arrived/qr/<region>` and `arrived/picture-card/<region>`: how a visit came in. Share links carry `?at=<hour>`, the share-sheet QR code carries `?qr`, and the picture card's QR code carries `?card`; the page strips these from the address bar.
- `share/whatsapp-button`, `share/open/<where>`, `share/whatsapp`, `share/telegram`, `share/copy-link`, `share/copy-text`, `share/system-sheet` and `share/image`.
- `location/asked`, `location/found/<region>`, `location/denied` …; `tab/<name>`, `region/<name>`, `group/<name>`, `define/<number>`, `nea-wording/<section>` and `out/<site>`.

To leave your own visits out, run `localStorage.setItem('skipgc', 't')` in the browser console on the site.

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

- writes one page per region, at `/north/`, `/west/` and so on, whose preview title gives that region's numbers and their time, e.g. "West at 11am, Thu 15 Oct: PM2.5 161 (High), PSI 211 (Very Unhealthy)";
- renders a matching 1200×630 image from `src/og-live.html`, with the time in large type.

**Chat apps cache previews.** WhatsApp builds a preview on the sender's phone, sends it inside the message, and remembers previews per address; nothing on our side can make it refresh. So:

- the bare domain keeps the fixed `og.png`, which shows no numbers, because people type it by hand and a saved copy must never be wrong;
- share links add the reading's hour, e.g. `https://haze.geewax.org/west/?at=2026101511`, a new address every hour, so chat apps fetch a fresh preview. The page ignores `?at=` and tidies the address bar. QR codes use the plain address.

A preview saved in a chat is a dated snapshot; tapping it opens the live numbers. If NEA can't be reached during a build, region pages fall back to the fixed `og.png`.

`index.html` at the repository root is the same page without the region previews, kept for opening locally.

This is an unofficial project. It is not affiliated with NEA.
