#!/usr/bin/env python3
"""
Build the site.

Pages are assembled here rather than written by hand, so the nav, the footer,
the head and the structured data cannot drift apart between them:

    dist/index.html                     the landing page
    dist/courses/<slug>/index.html      one per course that has a slug
    dist/404.html
    dist/robots.txt  sitemap.xml  llms.txt
    dist/og.png                          social card, drawn from the real lap
    dist/artifact.html                   the landing page without the document
                                         wrapper, for publishing as an Artifact

Everything is inlined — CSS, JS, the lap data — because the whole site is three
documents and inlining removes a request, a failure mode, and any question of
whether a strict CSP will allow the fetch.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..")
DIST = os.path.join(SITE, "dist")
PUBLIC = os.path.join(SITE, "public")

ORIGIN = "https://telemetrylab.atlas.motionapplied.com"
SITE_NAME = "ATLAS Telemetry Lab"
PUBLISHER = "Motion Applied"
LAB_REPO = "https://github.com/motionapplied/atlas-telemetry-lab"

DOCUMENT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#1F292E">
<meta name="color-scheme" content="dark">

<meta property="og:site_name" content="{site_name}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{origin}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A lap of a simulated circuit, drawn from real telemetry and coloured by speed.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{origin}/og.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%231F292E'/><path d='M3 22 L11 22 L16 9 L21 26 L26 18 L29 18' stroke='%23FA6914' stroke-width='2.5' fill='none' stroke-linejoin='round' stroke-linecap='round'/></svg>">

<style>
{css}
</style>

<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
{nav}
{body}
{footer}
<script>
{js}
</script>
</body>
</html>
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# Motion Applied brand guidelines, February 2026. MA Orange and MA Grey plus
# their sanctioned tints, white, and the extended palette. Nothing else.
BRAND_COLOURS = {
    "#FA6914", "#FB8743", "#FCA572", "#FDC3A1",          # MA Orange + tints
    "#1F292E", "#2C363B", "#3A4347", "#4C5458",          # MA Grey + tints
    "#797F82", "#A5A9AB",
    "#FFFFFF", "#000000",
    "#DEE2D9", "#38E9FC", "#028091",                     # extended
}
BRAND_RGB = {(250, 105, 20), (31, 41, 46)}


def audit_colours(css: str) -> list[str]:
    """Fail the build on any colour outside the brand palette.

    An earlier pass converted every hex to the brand palette but left four
    rgba(10,13,15,…) literals behind — the old near-black — painting the nav,
    the readout and the hero scrim a different colour from the page. It shipped,
    and was only caught by looking at the rendered site. Scanning rgb()/rgba()
    as well as hex is the check that would have caught it.
    """
    import re
    bad = []
    for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", css):
        if m.group(0).upper() not in BRAND_COLOURS:
            bad.append(m.group(0))
    for m in re.finditer(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", css):
        rgb = tuple(int(g) for g in m.groups())
        if rgb not in BRAND_RGB and rgb != (255, 255, 255) and rgb != (0, 0, 0):
            bad.append(f"rgb{rgb}")
    return sorted(set(bad))


def word_count(body: str) -> int:
    import re
    t = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S)
    return len(re.sub(r"<[^>]+>", " ", t).split())


# --- the catalogue ----------------------------------------------------------


def render_catalogue(courses: list[dict], only_open: bool = False) -> str:
    """Render the course list from courses.toml.

    Two states only — a course is open or it is not. An open course gets a real
    channel in its lane; anything else gets a flat one, which is what an
    unconnected channel looks like on an instrument.

    On the landing page `only_open` drops the unbuilt courses entirely. Rendered,
    three empty NO SIGNAL lanes read as broken rather than as a device, and they
    cost about 600px to say nothing. The honest note goes in the markup instead.
    """
    out = []
    for c in courses:
        if only_open and c.get("status") != "open":
            continue
        open_ = c.get("status") == "open"
        lane = (
            f'<div class="lane" data-channel="{esc(c.get("channel", ""))}"></div>'
            if open_ else
            '<div class="lane" data-nosignal="1"></div>'
        )
        name = esc(c["name"])
        if c.get("slug"):
            name = f'<a href="courses/{esc(c["slug"])}/">{name}</a>'

        out.append(f"""      <article class="{'course' if open_ else 'course dark'}" id="{esc(c['id'])}">
        <div class="course-row">
          <div class="course-id">
            <span class="course-no">{esc(c['number'])}</span>
            <span class="status {'open' if open_ else 'dark'}">{esc(c['status_label'])}</span>
            <h3 class="course-name">{name}</h3>
            <p class="course-summary">{esc(c['summary'])}</p>
            {f'<p class="course-meta">{esc(c["meta"])}</p>' if c.get("meta") else ""}
          </div>
          {lane}
        </div>""")

        modules = c.get("modules") or []
        if modules:
            items = "\n".join(
                f"""          <li>
            <span class="n">{esc(m['label'])}</span>
            <span class="t">{esc(m['title'])}</span>
            <p class="d">{esc(m['summary'])}</p>
            <p class="g">{esc(m['graded'])}</p>
          </li>""" for m in modules
            )
            out.append(f'        <ul class="modules">\n{items}\n        </ul>')
        out.append("      </article>")
    return "\n".join(out)


def render_steps(modules: list[dict]) -> str:
    return "\n".join(
        f"""      <li>
        <span class="n">{esc(m['label'])}</span>
        <div>
          <h3>{esc(m['title'])}</h3>
          <p>{esc(m['summary'])}</p>
          <p class="g">{esc(m['graded'])}</p>
        </div>
      </li>""" for m in modules
    )


# --- structured data --------------------------------------------------------
#
# Course, ItemList and FAQPage are the three types that actually describe what
# this site is. They are what lets a search engine or an assistant answer "is
# there a free course on telemetry streaming" with this page rather than with a
# guess about it.


def org() -> dict:
    return {
        "@type": "Organization",
        "@id": f"{ORIGIN}/#org",
        "name": PUBLISHER,
        "url": "https://www.motionapplied.com",
    }


def course_jsonld(c: dict) -> dict:
    d = {
        "@type": "Course",
        "@id": f"{ORIGIN}/courses/{c['slug']}/#course",
        "name": c["name"],
        "description": c.get("description", c["summary"]),
        "url": f"{ORIGIN}/courses/{c['slug']}/",
        "provider": org(),
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "teaches": [m["title"] for m in c.get("modules", [])],
        "educationalLevel": "Intermediate",
        "learningResourceType": "Course",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "category": "Free",
        },
        "hasCourseInstance": {
            "@type": "CourseInstance",
            "courseMode": "online",
        },
    }
    return d


def faq_jsonld(body: str) -> dict | None:
    """Build FAQPage entries from the page's own <details> blocks.

    Generated from the rendered markup rather than a second copy of the
    questions, so the structured data cannot claim something the page does not
    say — which is the usual way FAQ schema goes wrong.
    """
    import re
    qs = re.findall(
        r"<summary>(.*?)</summary>\s*<p class=\"a\">(.*?)</p>", body, re.S
    )
    if not qs:
        return None
    clean = lambda t: " ".join(re.sub(r"<[^>]+>", "", t).split())
    return {
        "@type": "FAQPage",
        "@id": f"{ORIGIN}/#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": clean(q),
                "acceptedAnswer": {"@type": "Answer", "text": clean(a)},
            }
            for q, a in qs
        ],
    }


# --- page assembly ----------------------------------------------------------


def read(*parts: str) -> str:
    with open(os.path.join(SITE, *parts), encoding="utf-8") as f:
        return f.read()


def write(rel: str, content: str) -> None:
    path = os.path.join(DIST, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main() -> int:
    lap_path = os.path.join(PUBLIC, "lap.json")
    if not os.path.exists(lap_path):
        print("public/lap.json is missing. Run build/refresh_lap.py.", file=sys.stderr)
        return 1

    css = read("styles.css")
    off_brand = audit_colours(css)
    if off_brand:
        print("Off-brand colours in styles.css: " + ", ".join(off_brand), file=sys.stderr)
        return 1
    js = read("app.js").replace("__LAP_DATA__", read("public", "lap.json").strip())
    nav_t = read("partials", "nav.html")
    foot_t = read("partials", "footer.html")
    courses = tomllib.load(open(os.path.join(SITE, "courses.toml"), "rb"))["courses"]

    os.makedirs(DIST, exist_ok=True)
    pages: list[tuple[str, str]] = []      # (url path, changefreq) for the sitemap

    def page(rel: str, *, body: str, title: str, description: str, path: str,
             jsonld: list, og_title: str | None = None, robots: str = "index,follow",
             depth: int = 0) -> None:
        root = "../" * depth if depth else ""
        doc = DOCUMENT.format(
            title=esc(title),
            og_title=esc(og_title or title),
            description=esc(description),
            canonical=f"{ORIGIN}{path}",
            origin=ORIGIN,
            site_name=SITE_NAME,
            robots=robots,
            css=css,
            js=js,
            nav=nav_t.replace("{root}", root or "/"),
            footer=foot_t.replace("{root}", root or "/"),
            body=body,
            jsonld=json.dumps(
                {"@context": "https://schema.org", "@graph": jsonld},
                indent=2, ensure_ascii=False,
            ),
        )
        write(rel, doc)
        words = word_count(body)
        # A regression ceiling, not a target. The landing page was 1,702 words
        # of prose and read as an essay; it is ~1,150 now, of which the FAQ is
        # collapsed <details> that cost the reader nothing until opened. If this
        # trips, prose has crept back in.
        budget = " (over ceiling)" if rel == "index.html" and words > 1250 else ""
        print(f"  {rel:<52} {words:>5} words{budget}")
        if robots.startswith("index"):
            pages.append((path, "weekly" if path == "/" else "monthly"))

    # --- landing page -------------------------------------------------------
    home_body = read("index.template.html").replace(
        "__CATALOGUE__", render_catalogue(courses, only_open=True)
    )
    home_graph = [
        org(),
        {
            "@type": "WebSite",
            "@id": f"{ORIGIN}/#site",
            "name": SITE_NAME,
            "url": f"{ORIGIN}/",
            "publisher": org(),
            "inLanguage": "en",
        },
        {
            "@type": "ItemList",
            "@id": f"{ORIGIN}/#catalogue",
            "name": "Course catalogue",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": c["name"],
                    **({"url": f"{ORIGIN}/courses/{c['slug']}/"} if c.get("slug") else {}),
                }
                for i, c in enumerate(courses)
            ],
        },
    ]
    fq = faq_jsonld(home_body)
    if fq:
        home_graph.append(fq)
    home_graph += [course_jsonld(c) for c in courses if c.get("slug")]

    page(
        "index.html",
        body=home_body,
        title="ATLAS Telemetry Lab",
        og_title="ATLAS Telemetry Lab",
        description=(
            "Free courses in real-time telemetry engineering. Run a broker, a "
            "streaming API and a synthetic race car in a browser tab, write code "
            "against them, and have a bot grade your work. No licence, nothing to install."
        ),
        path="/",
        jsonld=home_graph,
    )

    # --- one page per course that has a slug --------------------------------
    course_t = read("course.template.html")
    for c in courses:
        if not c.get("slug"):
            continue
        modules = c.get("modules") or []
        body = (course_t
                .replace("{number}", esc(c["number"]))
                .replace("{name}", esc(c["name"]))
                .replace("{summary}", esc(c["summary"]))
                .replace("{status_label}", esc(c["status_label"]))
                .replace("{status_class}", "open" if c.get("status") == "open" else "dark")
                .replace("{module_count}", str(len(modules)))
                .replace("{steps}", render_steps(modules)))
        page(
            f"courses/{c['slug']}/index.html",
            body=body,
            title=f"{c['name']} — {SITE_NAME}",
            og_title=c["name"],
            description=c.get("description", c["summary"]),
            path=f"/courses/{c['slug']}/",
            depth=2,
            jsonld=[
                org(),
                course_jsonld(c),
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": SITE_NAME,
                         "item": f"{ORIGIN}/"},
                        {"@type": "ListItem", "position": 2, "name": "Courses",
                         "item": f"{ORIGIN}/#catalogue"},
                        {"@type": "ListItem", "position": 3, "name": c["name"]},
                    ],
                },
            ],
        )

    # --- 404 ----------------------------------------------------------------
    page(
        "404.html",
        body='''<main id="main">
<section class="band">
  <div class="wrap narrow">
    <p class="label">404</p>
    <h2>No signal on that channel</h2>
    <p class="lede">That page does not exist. It may have moved, or it may never
      have been built — three of the four courses have not been.</p>
    <div class="cta-row" style="margin-top:28px;">
      <a class="btn" href="/">Back to the lab</a>
      <a class="btn ghost" href="/#catalogue">See the catalogue</a>
    </div>
  </div>
</section>
</main>''',
        title=f"Page not found — {SITE_NAME}",
        description="That page does not exist.",
        path="/404",
        robots="noindex,follow",
        jsonld=[org()],
    )

    # --- the artifact copy: landing page, no document wrapper ---------------
    write("artifact.html",
          f"<title>{esc(SITE_NAME)}</title>\n"
          '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
          '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap">\n'
          f"<style>\n{css}\n</style>\n"
          + nav_t.replace("{root}", "#") + "\n"
          + home_body + "\n"
          + foot_t.replace("{root}", "#") + "\n"
          f"<script>\n{js}\n</script>\n")

    # --- machine-readable ---------------------------------------------------
    write("robots.txt", robots_txt())
    write("sitemap.xml", sitemap(pages))
    write("llms.txt", llms_txt(courses))

    # The social card is drawn from the same lap the page animates, so it is
    # generated here rather than checked in and left to go stale.
    sys.path.insert(0, HERE)
    import og
    og.main()

    for name in os.listdir(PUBLIC):
        src = os.path.join(PUBLIC, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(DIST, name))

    for root, _dirs, files in os.walk(DIST):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, DIST).replace("\\", "/")
            print(f"  dist/{rel:<52} {os.path.getsize(p) / 1024:7.1f} kB")
    return 0


def robots_txt() -> str:
    # The AI crawlers are named explicitly and allowed. Blocking them would mean
    # ChatGPT, Claude and Perplexity cannot cite this site — and being the answer
    # to "how do I learn real-time telemetry" is most of the point of building it.
    bots = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "anthropic-ai",
            "Claude-Web", "PerplexityBot", "Google-Extended", "Applebot-Extended",
            "Bingbot", "cohere-ai", "Meta-ExternalAgent"]
    lines = ["User-agent: *", "Allow: /", ""]
    for b in bots:
        lines += [f"User-agent: {b}", "Allow: /", ""]
    lines += [f"Sitemap: {ORIGIN}/sitemap.xml", ""]
    return "\n".join(lines)


def sitemap(pages: list[tuple[str, str]]) -> str:
    items = "\n".join(
        f"  <url>\n    <loc>{ORIGIN}{path}</loc>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{'1.0' if path == '/' else '0.8'}</priority>\n  </url>"
        for path, freq in pages
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{items}\n</urlset>\n")


def llms_txt(courses: list[dict]) -> str:
    """A plain-text brief for assistants, per llmstxt.org.

    Written as facts a model can lift verbatim and be right. Everything here is
    checkable against the repository; nothing is aspirational."""
    open_ = [c for c in courses if c.get("status") == "open"]
    later = [c for c in courses if c.get("status") != "open"]

    out = [
        f"# {SITE_NAME}",
        "",
        f"> Free, self-paced courses in real-time telemetry engineering, published by "
        f"{PUBLISHER}. Learners run a real streaming stack — Apache Kafka, the ATLAS "
        f"Stream API and a Key Generator — in a GitHub Codespace, write code against "
        f"it, and have an automated validator grade the result in their own repository.",
        "",
        "## What it teaches",
        "",
        "ATLAS Open Streaming is a real-time telemetry platform. A producer sends data "
        "over gRPC to a Stream API, which registers the session, holds the configuration "
        "describing each channel, and writes to Apache Kafka; any number of consumers "
        "read from there. What distinguishes it from a bare Kafka topic plus a "
        "time-series database is a telemetry-native data model: parameter definitions "
        "carrying identity, units, sample rate, valid range and display format in-band; "
        "sessions as a first-class lifecycle; multi-rate channels; and laps and events "
        "as timestamped markers on the stream.",
        "",
        "## Facts",
        "",
        "- Cost: free. No licence is required for any component used in the courses.",
        "- Runs in: a GitHub Codespace (nothing installed locally), or locally with "
        "Docker, Python 3.12 and Node 22.",
        "- Resource use: the stack idles at about 442 MiB across three containers.",
        "- Grading: an automated bot runs in the learner's own repository and grades "
        "behaviour rather than code shape — it runs the pipeline and checks what it did.",
        "- Completion: there is no certificate. What a learner ends up with is their "
        "own repository, the code they wrote, and a permanent GitHub Actions URL for "
        "every validation run that passed. A per-engineer summary page is intended but "
        "not built.",
        "- ATLAS Viewer, the commercial desktop analysis application, is a separate "
        "licensed product and is not required.",
        "",
        "## Courses",
        "",
    ]
    for c in open_:
        out.append(f"- [{c['name']}]({ORIGIN}/courses/{c['slug']}/): {c['summary']} "
                   f"({len(c.get('modules', []))} modules, free, available now; duration not yet measured)")
        for m in c.get("modules", []):
            out.append(f"  - {m['label']}: {m['title']} — {m['summary']}")
    out.append("")
    out.append("## Planned, not yet available")
    out.append("")
    for c in later:
        out.append(f"- {c['name']} ({c['status_label'].lower()}): {c['summary']}")
    out += [
        "",
        "## Links",
        "",
        f"- [Course catalogue]({ORIGIN}/#catalogue)",
        f"- [Frequently asked questions]({ORIGIN}/#faq)",
        "- [ATLAS Open Streaming images on Docker Hub](https://hub.docker.com/u/atlasplatformdocker)",
        "- [ATLAS documentation](https://atlas.motionapplied.com)",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
