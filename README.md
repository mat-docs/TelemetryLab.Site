# ATLAS Telemetry Lab — site

The landing page for **telemetrylab.atlas.motionapplied.com**. Its only job is
to explain what the lab is and send people to the exercise template.

This is deliberately a **separate repository from the exercise**. The exercise
is a GitHub template: every learner gets a byte-for-byte copy of it. Anything
that lives in the template gets copied into every learner's repository, shows up
in their file tree, and then goes stale the moment we change it. A marketing
page has no business being there — and keeping it here means we can redeploy the
site as often as we like without touching a template that people are mid-way
through.

## Build

```bash
python build/build.py
```

No dependencies. Two outputs:

| Output | For |
|---|---|
| `dist/index.html` | Netlify — a complete document |
| `dist/artifact.html` | Publishing as an Artifact for review — content only, no wrapper |

## The hero lap is real

The animated lap is actual telemetry from the lab's simulator — the same code a
learner runs in Module 1 — not a decorative squiggle. It is exported once and
committed as `public/lap.json`, so this repository builds on its own.

Refresh it only when the simulator changes:

```bash
python build/refresh_lap.py --lab ../telemetry-lab
```

## Deploying

Netlify, from `netlify.toml`. Publish directory `dist`, build command
`python build/build.py`, Python 3.12.
