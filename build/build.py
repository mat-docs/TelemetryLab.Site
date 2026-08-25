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

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..")
TEMPLATE = os.path.join(SITE, "index.template.html")
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


def main() -> int:
    if not os.path.exists(LAP):
        print("lap.json is missing. Run site/build/export_lap.py first.", file=sys.stderr)
        return 1

    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    with open(LAP, encoding="utf-8") as f:
        lap = f.read().strip()

    content = template.replace("__LAP_DATA__", lap)

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
