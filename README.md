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

## Adding or opening a course

Edit [`courses.toml`](courses.toml) and rebuild. The catalogue section is
generated from it — there is no course markup in the template.

```toml
[[courses]]
id           = "course-02"
number       = "Course 02"
name         = "Producers and bridges"
status       = "open"            # "open", or anything else for not-yet
status_label = "Open now"
summary      = "..."
meta         = "3 modules · a weekend · free"
channel      = "Throttle"        # a channel in public/lap.json, drawn in the lane

  [[courses.modules]]
  label   = "Module 01"
  title   = "..."
  summary = "..."
  graded  = "..."
```

`status = "open"` draws the course in orange with a real telemetry channel in
its lane. Anything else draws it grey with a flat `NO SIGNAL` lane — which is
what an unconnected channel looks like on an instrument, and cannot be mistaken
for a launch date.

There are only two states on purpose. The words in `status_label` carry the
difference between "in development" and "planned"; the colours do not try to,
because teal against grey measures ΔE 13.0 to normal vision — below the
legibility floor.

## Build

```bash
python build/build.py
```

No dependencies — `tomllib` is in the standard library. Two outputs:

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
