# SynchNeuro FAQ &amp; Troubleshooting site

Static help pages for the CardioMetabolic Advisor app's in-app **FAQ &amp; Troubleshooting**
feature. The app's `FaqConfig.kt` points at these pages, loaded in a native WebView.

Hosted on **GitHub Pages** (`wlutz/synchneuro-faq`, served from `main` / root):

| URL | Page |
| --- | --- |
| `https://wlutz.github.io/synchneuro-faq/stelo-cgm.html` | Stelo CGM |
| `https://wlutz.github.io/synchneuro-faq/polar-verity-sense.html` | Polar Verity Sense |
| `https://wlutz.github.io/synchneuro-faq/eeg-sensor.html` | EEG Sensor |
| `https://wlutz.github.io/synchneuro-faq/search.html` | Combined cross-sensor search (accepts `#q=<term>` deep links from the app's search field) |
| `https://wlutz.github.io/synchneuro-faq/index.html` | Index / links |

## Layout

- `Content/{Stelo_CGM,Polar_Verity_Sense,EEG_Sensor}/*.md` — **source** markdown (edit these).
- `generate.py` — converts the markdown into the self-contained `*.html` pages at the repo
  root (collapsible Q&amp;A accordion + in-page search, base64 images inlined, `#q=` deep-link
  bootstrap on every page, SynchNeuro blue `#003F7D`).
- `*.html` at the repo root — **generated output**, served by GitHub Pages. Do not hand-edit.

## Updating content

1. Edit the source markdown under `Content/`.
2. Regenerate: `python3 generate.py`
3. Sanity-check images render (raw `<img>`, not `&lt;img`) and the page opens; then commit &amp;
   push. Pages redeploys automatically.

The `search.html` page aggregates every sensor's Q&amp;A so the app's single search field can
search across all sensors at once.
