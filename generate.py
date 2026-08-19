#!/usr/bin/env python3
"""Convert the sensor FAQ markdown into self-contained, mobile-friendly HTML pages
(collapsible Q&A accordion + in-page search), images inlined. Output -> ./html/.

Classification rule:
  - a heading at or below that file's ITEM_LEVEL, or any heading ending '?'  -> QUESTION (accordion)
  - a standalone **bold** line (not a warning callout)                       -> QUESTION (accordion)
  - a shallower heading                                                      -> SECTION header

  The '?' test used to be the WHOLE rule, on the reasoning that heading levels are inconsistent
  between the three files. They are inconsistent BETWEEN files but consistent WITHIN each, and the
  '?' test silently mis-filed every item phrased as a statement — "The sensor snapped off the
  patch.", "I am getting a 'Signal Loss' alert", "Battery safety" — as section headers, which
  render permanently expanded. That is the bug participants reported as "some questions at the
  bottom have all their content showing" (2026-08-19). 17 items across the three pages.
  - a **bold** line containing the warning glyph                            -> warning callout (body)
  - everything else                                                         -> body (paragraph / bullet / image)
"""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, "Content")
# Output the generated pages at the repo root: GitHub Pages serves this repo (wlutz/synchneuro-faq)
# from main/root, so the live URLs are https://wlutz.github.io/synchneuro-faq/<page>.html.
OUT = HERE

# Heading depth at which a file's ACCORDION ITEMS start; anything shallower is a section header.
# Per file because the three documents nest differently and always have:
#   Stelo  "#" title, "##" sections, "###" items
#   Polar  "#" sections, "##"/"###" items
#   EEG    "#"/"##" sections, items are standalone **bold** lines (no heading at all) -> None
SENSORS = [
    # (markdown path,                              out file,                    page title,  item level)
    ("Stelo_CGM/Stelo_CGM.md",                     "stelo-cgm.html",            "Stelo CGM", 3),
    ("Polar_Verity_Sense/Polar_Verity_Sense.md",   "polar-verity-sense.html",   "Polar Verity Sense", 2),
    # "Brain Sensor" is the participant-facing name of the SN-EEG headband (renamed app-wide
    # 2026-08-05). The title now feeds only the browser <title> — the in-page blue header was
    # removed 2026-08-11 (designer: the app's own nav above the WebView already says
    # "BRAIN SENSOR FAQ", so it duplicated). The output filename and the app's FaqSensor.Eeg key
    # stay `eeg` — no participant sees either, and changing them would break the app's URL.
    ("EEG_Sensor/EEG_Sensor.md",                   "eeg-sensor.html",           "Brain Sensor", None),
]

IMG_DEF = re.compile(r"^\[(image\d+)\]:\s*<?(data:[^>\s]+)>?\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BOLD_ONLY = re.compile(r"^\*\*(.+)\*\*$")
BULLET = re.compile(r"^[-*]\s+(.*)$")
IMG_REF = re.compile(r"!\[\]\[(image\d+)\]")
WARN = "⚠"  # ⚠


def strip_bold(s):
    s = s.strip()
    m = BOLD_ONLY.match(s)
    return m.group(1).strip() if m else s


def inline(text, images):
    """Escape, then apply a minimal inline-markdown subset -> HTML."""
    text = html.escape(text, quote=False)
    # images: ![][imageN] -> <img>. Done AFTER escaping (the ref has no chars escaping
    # touches); doing it before would escape the <img> tag itself and render it as text.
    def img_sub(m):
        data = images.get(m.group(1))
        return f'<img loading="lazy" src="{data}" alt="">' if data else ""
    text = IMG_REF.sub(img_sub, text)
    # links [text](url)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def parse(md_lines, images, item_level=None):
    """Return list of sections: {title, intro:[html], items:[{q, body:[html]}]}."""
    sections = []
    cur_section = None
    cur_item = None
    pending_bullets = []
    started = False  # skip the doc's own leading title/subtitle until first section/question

    def ensure_section():
        nonlocal cur_section
        if cur_section is None:
            cur_section = {"title": None, "intro": [], "items": []}
            sections.append(cur_section)

    def target_body():
        ensure_section()
        return cur_item["body"] if cur_item is not None else cur_section["intro"]

    def flush_bullets():
        nonlocal pending_bullets
        if pending_bullets:
            lis = "".join(f"<li>{inline(b, images)}</li>" for b in pending_bullets)
            target_body().append(f"<ul>{lis}</ul>")
            pending_bullets = []

    for raw in md_lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            flush_bullets()
            continue

        h = HEADING.match(stripped)
        b = BOLD_ONLY.match(stripped)
        is_heading = h is not None
        text = strip_bold(h.group(2)) if is_heading else (b.group(1).strip() if b else stripped)

        is_warning = (b is not None) and (WARN in text)
        # A standalone bold line is always an item — these documents use bold-on-its-own as the
        # Q&A prompt, and many prompts are statements rather than questions. Warning callouts are
        # also bold-only, so they are excluded first.
        bold_item = b is not None and not is_warning
        heading_item = is_heading and (
            text.rstrip().endswith("?")
            or (item_level is not None and len(h.group(1)) >= item_level)
        )
        is_question = bold_item or heading_item
        is_section = is_heading and not is_question

        if is_question:
            flush_bullets()
            started = True
            ensure_section()
            cur_item = {"q": text, "body": []}
            cur_section["items"].append(cur_item)
        elif is_section:
            flush_bullets()
            started = True
            cur_section = {"title": text, "intro": [], "items": []}
            cur_item = None
            sections.append(cur_section)
        elif is_warning:
            if not started:
                continue
            flush_bullets()
            target_body().append(f'<div class="warn">{inline(text, images)}</div>')
        else:
            if not started:
                continue  # drop the doc's leading title/subtitle preamble
            bl = BULLET.match(stripped)
            if bl:
                pending_bullets.append(bl.group(1))
            else:
                flush_bullets()
                if IMG_REF.search(stripped):
                    target_body().append(f'<p class="img">{inline(stripped, images)}</p>')
                else:
                    target_body().append(f"<p>{inline(stripped, images)}</p>")
    flush_bullets()
    return sections


def render(title, sections):
    parts = []
    for s in sections:
        if s["title"]:
            parts.append(f'<h2 class="section">{html.escape(s["title"])}</h2>')
        for blk in s["intro"]:
            parts.append(f'<div class="intro">{blk}</div>')
        for item in s["items"]:
            q = html.escape(item["q"])
            body = "".join(item["body"])
            parts.append(
                '<div class="qa">'
                f'<button class="q" aria-expanded="false"><span>{q}</span><span class="chev">+</span></button>'
                f'<div class="a">{body}</div>'
                "</div>"
            )
    return "\n".join(parts)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__TITLE__ — FAQ &amp; Troubleshooting</title>
<style>
  :root { --blue:#003F7D; --ink:#1f2933; --muted:#6b7280; --line:#e5e7eb; --bg:#f7f9fc; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:#fff; line-height:1.55; -webkit-text-size-adjust:100%; }
  .wrap { max-width:760px; margin:0 auto; padding:0 16px 48px; }
  .searchbar { position:sticky; top:0; z-index:4; background:#fff; padding:12px 0 6px; }
  .searchbar input { width:100%; padding:12px 14px; font-size:16px; border:1px solid var(--line);
                     border-radius:12px; background:var(--bg); }
  .tools { display:flex; justify-content:flex-end; padding:4px 0 8px; }
  .tools button { background:none; border:none; color:var(--blue); font-size:13px; cursor:pointer; }
  h2.section { font-size:13px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted);
               margin:26px 0 8px; font-weight:700; }
  .qa { border-bottom:1px solid var(--line); }
  .qa .q { width:100%; text-align:left; background:none; border:none; padding:14px 0; cursor:pointer;
           font-size:16px; font-weight:600; color:var(--ink); display:flex; gap:12px;
           align-items:flex-start; justify-content:space-between; }
  .qa .chev { color:var(--blue); font-size:20px; line-height:1; flex:0 0 auto; }
  .qa.open .chev { transform:rotate(45deg); }
  .qa .a { display:none; padding:0 0 16px; }
  .qa.open .a { display:block; }
  .qa .a p { margin:0 0 12px; }
  .qa .a ul { margin:0 0 12px; padding-left:20px; }
  .qa .a li { margin:4px 0; }
  .qa .a img { max-width:100%; height:auto; border:1px solid var(--line); border-radius:8px; margin:6px 0; }
  .warn { background:#fff7ed; border-left:4px solid #f59e0b; padding:10px 12px; border-radius:6px; margin:10px 0; }
  .intro { color:var(--muted); margin:4px 0 8px; }
  .nores { color:var(--muted); padding:24px 0; display:none; }
</style>
</head>
<body>
<!-- No page header: the app draws its own nav ("BRAIN SENSOR FAQ" etc.) above this WebView, so
     the blue in-page title read as a duplicate. Removed at the designer's request, 2026-08-11. -->
<div class="wrap">
  <div class="searchbar"><input id="q" type="search" placeholder="Search help articles…" aria-label="Search"></div>
  <div class="tools"><button id="toggleAll" type="button">Expand all</button></div>
  <div id="content">
__CONTENT__
  </div>
  <p class="nores" id="nores">No results found.</p>
</div>
<script>
  var content = document.getElementById('content');
  var items = Array.prototype.slice.call(content.querySelectorAll('.qa'));
  var search = document.getElementById('q');
  var nores = document.getElementById('nores');
  var toggleAll = document.getElementById('toggleAll');

  content.addEventListener('click', function (e) {
    var btn = e.target.closest('.q'); if (!btn) return;
    var qa = btn.parentElement;
    var open = qa.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  toggleAll.addEventListener('click', function () {
    var anyClosed = items.some(function (i) { return !i.classList.contains('open') && i.style.display !== 'none'; });
    items.forEach(function (i) {
      if (i.style.display === 'none') return;
      i.classList.toggle('open', anyClosed);
      i.querySelector('.q').setAttribute('aria-expanded', anyClosed ? 'true' : 'false');
    });
    toggleAll.textContent = anyClosed ? 'Collapse all' : 'Expand all';
  });

  search.addEventListener('input', function () {
    var term = search.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function (i) {
      var match = !term || i.textContent.toLowerCase().indexOf(term) !== -1;
      i.style.display = match ? '' : 'none';
      if (match && term) { i.classList.add('open'); i.querySelector('.q').setAttribute('aria-expanded', 'true'); }
      if (match) shown++;
    });
    // hide section headers with no visible items
    Array.prototype.slice.call(content.querySelectorAll('h2.section')).forEach(function (h) {
      var any = false, n = h.nextElementSibling;
      while (n && !(n.tagName === 'H2')) { if (n.classList.contains('qa') && n.style.display !== 'none') any = true; n = n.nextElementSibling; }
      h.style.display = (term && !any) ? 'none' : '';
    });
    nores.style.display = (term && shown === 0) ? 'block' : 'none';
  });

  // Deep-link: a "#q=<term>" fragment (used by the in-app FAQ search field) pre-fills the
  // search box and filters on load.
  (function () {
    var m = location.hash.match(/[#&]q=([^&]*)/);
    if (m && m[1]) {
      search.value = decodeURIComponent(m[1].replace(/\\+/g, ' '));
      search.dispatchEvent(new Event('input'));
    }
  })();
</script>
</body>
</html>
"""


def render_qa(item):
    """Render a single Q&A item as an accordion block."""
    q = html.escape(item["q"])
    body = "".join(item["body"])
    return (
        '<div class="qa">'
        f'<button class="q" aria-expanded="false"><span>{q}</span><span class="chev">+</span></button>'
        f'<div class="a">{body}</div>'
        "</div>"
    )


def render_search(groups):
    """Combined cross-sensor search page: every sensor's Q&A under a sensor banner.

    Reuses the shared page's search box / accordion / "#q=" deep-link, so the in-app FAQ search
    field can open this page with a pre-applied query and the user sees matches across all sensors.
    """
    parts = []
    for title, items in groups:
        if not items:
            continue
        parts.append(f'<h2 class="section">{html.escape(title)}</h2>')
        parts.extend(render_qa(item) for item in items)
    return "\n".join(parts)


def main():
    os.makedirs(OUT, exist_ok=True)
    index_links = []
    search_groups = []  # (sensor_title, [all Q&A items]) for the combined search page
    for rel, outfile, title, item_level in SENSORS:
        with open(os.path.join(CONTENT, rel), encoding="utf-8") as f:
            lines = f.readlines()
        images = {}
        body_lines = []
        for ln in lines:
            m = IMG_DEF.match(ln.strip())
            if m:
                images[m.group(1)] = m.group(2)
            else:
                body_lines.append(ln)
        sections = parse(body_lines, images, item_level)
        content = render(title, sections)
        page = PAGE.replace("__TITLE__", html.escape(title)).replace("__CONTENT__", content)
        with open(os.path.join(OUT, outfile), "w", encoding="utf-8") as f:
            f.write(page)
        nq = sum(len(s["items"]) for s in sections)
        print(f"  {outfile}: {nq} Q&A, {len(images)} images, {len(page)} bytes")
        index_links.append(f'<li><a href="{outfile}">{html.escape(title)}</a></li>')
        search_groups.append((title, [it for s in sections for it in s["items"]]))

    # Combined cross-sensor search page (target of the in-app FAQ search field).
    search_content = render_search(search_groups)
    search_page = PAGE.replace("__TITLE__", "Search Help").replace("__CONTENT__", search_content)
    with open(os.path.join(OUT, "search.html"), "w", encoding="utf-8") as f:
        f.write(search_page)
    total_qa = sum(len(items) for _, items in search_groups)
    print(f"  search.html: {total_qa} Q&A across {len(search_groups)} sensors, {len(search_page)} bytes")

    idx = PAGE.replace("__TITLE__", "SynchNeuro Help").replace(
        "__CONTENT__", f'<ul class="index">{"".join(index_links)}</ul>')
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)
    print(f"Done -> {OUT}")


if __name__ == "__main__":
    main()
