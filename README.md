# ATLAS Telemetry Lab — site

The site for **telemetrylab.atlas.motionapplied.com**: a landing page, a page
per course, and the machine-readable files that let search engines and AI
assistants describe the courses accurately rather than guess.

This is deliberately a **separate repository from the exercise**. The exercise
is a GitHub template: every learner gets a byte-for-byte copy of it. Anything
that lives in the template gets copied into every learner's repository and then
goes stale the moment we change it.

## Layout

```
courses.toml              the catalogue — the source of truth for courses
index.template.html       landing page body
course.template.html      course page body
partials/nav.html         shared header
partials/footer.html      shared footer
styles.css                all styles, inlined at build
app.js                    hero animation + channel lanes, inlined at build
build/build.py            assembles pages, structured data, robots, sitemap, llms.txt
build/og.py               draws dist/og.png from the real lap
build/refresh_lap.py      re-exports public/lap.json from the lab's simulator
```

## Build

```bash
python build/build.py
```

No dependencies — `tomllib` and `zlib` are standard library. Output:

| Output | What it is |
|---|---|
| `dist/index.html` | Landing page |
| `dist/courses/<slug>/index.html` | One per course with a `slug` |
| `dist/404.html` | `noindex`, kept out of the sitemap |
| `dist/robots.txt` | Allows the AI crawlers explicitly — see below |
| `dist/sitemap.xml` | Generated from the pages actually built |
| `dist/llms.txt` | Plain-text brief for assistants ([llmstxt.org](https://llmstxt.org)) |
| `dist/og.png` | Social card, 1200×630, drawn from the real lap |
| `dist/artifact.html` | Landing page without the document wrapper, for review |

## Adding or opening a course

Edit [`courses.toml`](courses.toml) and rebuild. The catalogue, the course
pages, the sitemap, the structured data and `llms.txt` all come from it — there
is no course markup anywhere in the templates.

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
slug         = "producers-and-bridges"   # omit and the course gets no page of its own
time         = "A weekend"
description  = "..."             # meta description + JSON-LD description

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

## SEO and AI search

- **Structured data** — `Organization`, `WebSite`, `ItemList`, `Course` and
  `BreadcrumbList`, plus `FAQPage` **generated from the page's own `<details>`
  blocks** rather than a second copy of the questions, so the markup cannot
  claim something the page does not say.
- **`robots.txt` allows the AI crawlers by name** — GPTBot, ClaudeBot,
  PerplexityBot, Google-Extended and the rest. Blocking them would mean those
  assistants cannot cite the site, and being the answer to "how do I learn
  real-time telemetry" is most of the point of building it.
- **`llms.txt`** states the facts an assistant would otherwise guess at: that it
  is free, that no licence is needed, what the stack is, how grading works, and
  that there is no certificate. Everything in it is checkable against the lab
  repository.
- **The FAQ is real content first.** The eight questions are the ones engineers
  actually ask, answered in 40–60 words each so a passage stands on its own.

## Brand

Built to the Motion Applied brand guidelines (February 2026).

| | |
|---|---|
| MA Orange | `#FA6914` |
| MA Grey | `#1F292E` |
| Neutrals | tints of MA Grey — 94%, 88%, 80%, 60%, 40% |
| Extended | Cool Grey `#DEE2D9` for body copy |
| Typeface | Montserrat, with Arial as the stated fallback |

Every neutral is MA Grey or a computed tint of it, because the guidelines
forbid introducing unsanctioned colours. Tint N% = N% MA Grey + (100−N)% white.
The guidelines illustrate 80/60/40; the 94% and 88% steps continue that scale
and exist because a dark interface needs two surfaces just above the ground.

The speed ramp on the lap and the social card is the sanctioned tint scale of
MA Orange — 100%, 80%, 60%, 40% — which is monotonic in lightness, so it works
as a sequential scale without inventing colours.

Typography follows the stated hierarchy: headlines and CTAs Montserrat Bold in
sentence case with no closing punctuation; sub-heads with closing punctuation;
body copy Montserrat Regular, which is what the guidelines specify on a dark
background. Monospace is not covered by the guidelines and appears only inside
`<code>` and the simulated terminal readout, using the system stack so no second
typeface competes with Montserrat.

Contrast on the `#1F292E` ground: white 14.8:1, Cool Grey 11.3:1, Grey 40%
6.3:1, MA Orange 5.0:1 — all pass AA for body text. Grey 60% and 80% are 3.7:1
and 1.9:1, so they draw lines and never text. MA Grey on an MA Orange button is
5.0:1; white would have been 2.96:1 and was not used.

**Not yet applied:** the Motion Applied logo. The guidelines require the logo to
be used with its symbol and never redrawn, and no asset was supplied — the nav
and footer currently carry a text wordmark. That needs the real file before
launch.

## The hero lap is real

The animated lap and the social card are actual telemetry from the lab's
simulator — the same code a learner runs in Module 1. It is exported once and
committed as `public/lap.json`, so this repository builds on its own.

Refresh it only when the simulator changes:

```bash
python build/refresh_lap.py --lab ../telemetry-lab
```

## Deploying

Netlify, from `netlify.toml`. Publish directory `dist`, build command
`python build/build.py`, Python 3.12.
