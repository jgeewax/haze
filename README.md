# Haze Status

A calmer view of Singapore's haze readings, at [haze.geewax.org](https://haze.geewax.org).

It is a single static page. The visitor's browser loads the data straight from the National Environment Agency, with no server involved:

| Data | Endpoint |
| --- | --- |
| 1-hr PM2.5 and PSI sub-indices, 24 hours, five regions | `https://www.haze.gov.sg/api/airquality/jsondata/{timestamp}` |
| 24-hr PSI forecast and NEA's statement | `https://www.nea.gov.sg/api/advisory/latesthazesituationupdate/{timestamp}` |
| 2-hour weather forecast for 47 neighbourhoods (only the sky uses it) | `https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast` |

All three endpoints send `Access-Control-Allow-Origin: *`. The `{timestamp}` is only a cache-buster. The 24-hr PSI is the highest of the PM2.5, PM10, O3, CO and SO2 sub-indices. Advice text follows NEA's poster *How to plan your outdoor activities during haze* (June 2026).

Settings (region, group, start tab) are saved in the browser's `localStorage`.

**Languages.** English, Chinese (Simplified), Malay and Tamil, on every screen, the share message and the picture card. All strings live in `src/i18n.js`, bundled into the page at build time; missing keys fall back to English. The first visit follows the browser's language; the choice is in Settings and under the Now screen. Dates use the browser's own formatting for each language (`Intl.DateTimeFormat`, Singapore time). Chinese and Tamil load Noto Sans from Google Fonts only when chosen. NEA's own statement is published in English, so it stays in English, with a note. Link previews stay in English. The translations were written by Claude and are worth a review by native speakers, especially the health advice.

**The sky.** The Now screen's sky follows Singapore's sun and moon, worked out in the browser from the time (low-precision almanac formulas: sunrise, sunset and the moon's phase come out within minutes of the published times). Its colours mix by the sun's height and by the 1-hr PM2.5: blue days, gold sunrises and sunsets and starry nights in clear air; in haze a flat beige light, an orange sun disc, beams through the murk and an orange glow over the city at night. The text on the sky switches between dark and light, and the sky is nudged until the text keeps at least 4.5:1 contrast at the top and 4:1 at the bottom. Weather comes from NEA's 2-hour forecast: each neighbourhood is given the region of its nearest place in `AREAS`, and the most common forecast in the region decides between fair, partly cloudy, cloudy, rain and thunderstorm. If the forecast can't be fetched the sky stays fair. With reduced motion the sky is still, repainted once a minute. The share picture and link previews keep a fixed daytime sky, so they look the same whenever they are sent.

**Location.** A first visit opens the region picker ("Where are you?"), so nobody takes Central, the default, for all of Singapore. It asks once; closing it keeps Central. A visit from a shared region link shows that region and asks on a later visit. "Use my location" asks the browser for its position (this only works on https), then picks the nearest named neighbourhood in `AREAS` and uses that neighbourhood's NEA region.

**Sharing.** Now and My day end with two buttons side by side: Share on WhatsApp and Share. Share on WhatsApp sends the picture card, never text. A web page can't hand a picture straight to WhatsApp (its links carry text only), so on phones it opens the share menu with the picture attached, where WhatsApp is one tap; on computers it copies the picture and opens WhatsApp Web to paste it into a chat, because the Mac share menu has no WhatsApp in it. The picture goes without text, because WhatsApp on iPhones drops a picture shared with text ([WebKit bug 251500](https://bugs.webkit.org/show_bug.cgi?id=251500)). The card is drawn as soon as a screen shows, so the share happens on the tap itself. Share opens the share sheet, which offers WhatsApp, Telegram, copy link, copy text, the system share sheet where the browser has one, a QR code, and a 1080×1350 picture card drawn on a canvas. The card carries its own QR code, so a forwarded screenshot still leads back to the site. Shared links name a region, e.g. `https://haze.geewax.org/west/` (the older `#west` form still works). A first-time visitor adopts that region; a returning visitor sees it for that visit only and keeps their saved default. The QR codes come from [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 2.0.4 (MIT), kept in `vendor/` and bundled into the page at build time. `og.png` is the fixed link-preview image, used when live previews can't be made (see Deploying).

**Install as an app.** `manifest.webmanifest` and the icons in `icons/` (drawn from `src/icon.html` by `build.py --icons`) make the site installable; it opens full screen like an app. On Chrome, Edge and Android the Install button uses the browser's own dialog; on iPhone, where Safari has no dialog, it shows the Share → Add to Home Screen steps. The Now screen offers it on phones from the second visit until it is used or dismissed. `sw.js` only makes the installed app open when offline (showing that NEA can't be reached); pages always come from the network first, and readings are never cached.

**Analytics.** [GoatCounter](https://geewaxhaze.goatcounter.com) counts visits and taps, without cookies, and only on haze.geewax.org; local copies and previews aren't counted. The page view records the landing path (`/` or `/west/` …). Events include:

- `arrived/shared-link/<region>`, `arrived/qr/<region>` and `arrived/picture-card/<region>`: how a visit came in. Share links carry `?at=<hour>`, the share-sheet QR code carries `?qr`, and the picture card's QR code carries `?card`; the page strips these from the address bar.
- `share/whatsapp-button/<where>`, then `share/whatsapp/shared`, `share/whatsapp/copied` or `share/whatsapp/shown`: the Share on WhatsApp button and how the picture went.
- `share/open/<where>`, `share/whatsapp`, `share/telegram`, `share/copy-link`, `share/copy-text`, `share/system-sheet` and `share/image`.
- `welcome/shown`: the first-visit region picker opened.
- `location/asked`, `location/found/<region>`, `location/denied` …; `tab/<name>`, `region/<name>`, `group/<name>`, `define/<number>`, `nea-wording/<section>` and `out/<site>`.

To leave your own visits out, run `localStorage.setItem('skipgc', 't')` in the browser console on the site.

## Building

Edit `src/index.template.html`, then:

```sh
python3 build.py             # writes index.html, the page on its own, for opening locally
python3 build.py --preview   # writes preview.html, which falls back to src/snapshot/ when NEA is unreachable,
                             # with the sky lab (src/sky-lab.js) for trying any time of day, haze level and weather
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
