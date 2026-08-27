#!/usr/bin/env python3
"""
Build the static site.

Two outputs from one template, because they have different rules:

  dist/index.html    a complete document, for Netlify
  dist/artifact.html the same content without the document wrapper, for
                     publishing as an Artifact for review

The lap data is inlined rather than fetched. It is 23 kB, it removes a request
and a failure mode, and it means the page works from a file:// URL or anywhere
a strict CSP blocks fetches.
"""

from __future__ import annotations

import html
import os
import shutil
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..")
TEMPLATE = os.path.join(SITE, "index.template.html")
COURSES = os.path.join(SITE, "courses.toml")
LAP = os.path.join(SITE, "public", "lap.json")
DIST = os.path.join(SITE, "dist")

DOCUMENT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Learn to build on an open, real-time telemetry platform — by building on it. Nine modules, automatically assessed. Free, no licence, nothing to install.">
<meta name="theme-color" content="#0A0D0F">
<meta property="og:title" content="ATLAS Telemetry Lab">
<meta property="og:description" content="A real-time telemetry platform, running in your browser with nothing installed.">
<meta property="og:type" content="website">
{head}
</head>
<body>
{body}
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def render_catalogue(courses: list[dict]) -> str:
    """Render the course list from courses.toml.

    Two states only — a course is open or it is not. An open course gets a real
    channel in its lane; anything else gets a flat one, which is what an
    unconnected channel looks like on an instrument and cannot be mistaken for
    a launch date.
    """
    out = []
    for c in courses:
        open_ = c.get("status") == "open"
        cls = "course" if open_ else "course dark"
        lane = (
            f'<div class="lane" data-channel="{esc(c.get("channel", ""))}"></div>'
            if open_ else
            '<div class="lane" data-nosignal="1"></div>'
        )
        out.append(f"""      <article class="{cls}" id="{esc(c['id'])}">
        <div class="course-row">
          <div class="course-id">
            <span class="course-no">{esc(c['number'])}</span>
            <span class="status {'open' if open_ else 'dark'}">{esc(c['status_label'])}</span>
            <h3 class="course-name">{esc(c['name'])}</h3>
            <p class="course-summary">{esc(c['summary'])}</p>
            <p class="course-meta">{esc(c['meta'])}</p>
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


def main() -> int:
    if not os.path.exists(LAP):
        print("lap.json is missing. Run site/build/export_lap.py first.", file=sys.stderr)
        return 1

    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    with open(LAP, encoding="utf-8") as f:
        lap = f.read().strip()

    with open(COURSES, "rb") as f:
        courses = tomllib.load(f)["courses"]

    content = template.replace("__LAP_DATA__", lap)
    if "__CATALOGUE__" not in content:
        print("index.template.html has no __CATALOGUE__ placeholder.", file=sys.stderr)
        return 1
    content = content.replace("__CATALOGUE__", render_catalogue(courses))

    os.makedirs(DIST, exist_ok=True)

    # The artifact wants content only - no doctype, html, head or body tags.
    artifact_path = os.path.join(DIST, "artifact.html")
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Split the template's head-ish preamble (title, fonts, styles) from the
    # body so the standalone document nests them correctly.
    marker = '<div class="hero">'
    idx = content.index(marker)
    head, body = content[:idx].rstrip(), content[idx:]

    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(DOCUMENT.format(head=head, body=body))

    # Anything else in public/ ships as-is.
    public = os.path.join(SITE, "public")
    for name in os.listdir(public):
        src = os.path.join(public, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(DIST, name))

    for name in ("index.html", "artifact.html"):
        size = os.path.getsize(os.path.join(DIST, name)) / 1024
        print(f"  dist/{name:<16} {size:6.1f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
