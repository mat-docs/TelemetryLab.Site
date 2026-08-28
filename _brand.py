"""Bring the site onto the Motion Applied 2026 brand guidelines."""
import io
import re


def patch(path, edits):
    s = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    for old, new, why in edits:
        assert old in s, f"NOT FOUND in {path}: {why}"
        s = s.replace(old, new)
        print(f"  ok: {why}")
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- tokens ----
TOKENS = '''/* Motion Applied brand guidelines, February 2026.
     Primary palette: MA Orange #FA6914, MA Grey #1F292E. Those two lead; the
     extended palette is for accents only.

     Every neutral here is MA Grey or a tint of it, computed rather than picked,
     because the guidelines forbid introducing unsanctioned colours. Tint N% =
     N% MA Grey + (100-N)% white. The guidelines illustrate 80/60/40; the 94%
     and 88% steps continue the same scale and exist because a dark interface
     needs two surfaces just above the ground.

     Contrast against the #1F292E ground: white 14.8:1, Cool Grey 11.3:1,
     Grey 40% 6.3:1, MA Orange 5.0:1 — all pass AA for body text. Grey 60% and
     80% are 3.7:1 and 1.9:1, so they draw lines and never text. */
  :root {
    color-scheme: dark;
    --ground:   #1F292E;   /* MA Grey */
    --surface:  #2C363B;   /* MA Grey, 94% tint */
    --raised:   #3A4347;   /* MA Grey, 88% tint */
    --line:     #4C5458;   /* MA Grey, 80% tint */
    --line-2:   #797F82;   /* MA Grey, 60% tint */
    --muted:    #A5A9AB;   /* MA Grey, 40% tint */
    --ink-2:    #DEE2D9;   /* MA Cool Grey, extended palette */
    --ink:      #FFFFFF;   /* MA White */
    --accent:   #FA6914;   /* MA Orange */
    --accent-d: #FB8743;   /* MA Orange, 80% tint */
    --accent-l: #FCA572;   /* MA Orange, 60% tint */

    /* Montserrat is the brand's primary typeface, Arial its stated fallback.
       Monospace is not covered by the guidelines and is used only inside
       <code>, where a proportional face would misrepresent what is written. */
    --sans: Montserrat, Arial, Helvetica, sans-serif;
    --display: Montserrat, Arial, Helvetica, sans-serif;
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }'''

s = io.open("styles.css", encoding="utf-8", newline="").read().replace("\r\n", "\n")
start = s.index("/* A telemetry display is a dark instrument")
end = s.index("* { box-sizing: border-box; }")
s = s[:start] + TOKENS + "\n\n  " + s[end:]
io.open("styles.css", "w", encoding="utf-8", newline="\n").write(s)
print("  ok: brand token block")

# ------------------------------------------------------------ typography ----
patch("styles.css", [
    # Body copy on a dark background is Montserrat Regular, per the guidelines.
    ("font-family: var(--sans);\n    font-size: 16.5px;\n    line-height: 1.6;",
     "font-family: var(--sans);\n    font-weight: 400;\n    font-size: 16.5px;\n    line-height: 1.6;",
     "body weight"),
    # Headlines are Montserrat Bold. Montserrat is geometric and runs wide, so
    # the large sizes need more negative tracking than Plex did.
    ("font-weight: 800;\n  font-size: clamp(42px, 6.6vw, 82px);\n  line-height: 0.96;\n  letter-spacing: -0.012em;",
     "font-weight: 700;\n  font-size: clamp(38px, 5.9vw, 72px);\n  line-height: 1.02;\n  letter-spacing: -0.028em;",
     "h1"),
    ("font-weight: 700;\n  font-size: clamp(29px, 3.6vw, 43px);\n  line-height: 1.04;\n  letter-spacing: -0.008em;",
     "font-weight: 700;\n  font-size: clamp(27px, 3.3vw, 39px);\n  line-height: 1.12;\n  letter-spacing: -0.02em;",
     "h2"),
    ("font-size: 24px;\n    line-height: 1.12;\n    letter-spacing: -0.005em;",
     "font-size: 21px;\n    line-height: 1.2;\n    letter-spacing: -0.015em;",
     "course name"),
    ("font-weight: 700;\n  font-size: 22px;\n  letter-spacing: -0.005em;",
     "font-weight: 700;\n  font-size: 20px;\n  letter-spacing: -0.015em;",
     "steps h3"),
])

# Everything that used the monospace as a typographic device is now Montserrat.
# Only <code> keeps it.
css = io.open("styles.css", encoding="utf-8", newline="").read()
protect = ".evidence {"
head, _, tail = css.partition(protect)
head = head.replace("font-family: var(--mono);", "font-family: var(--sans);")
css = head + protect + tail
io.open("styles.css", "w", encoding="utf-8", newline="\n").write(css)
print("  ok: mono demoted to <code> and the evidence block")

patch("styles.css", [
    # The readout is numeric data; Montserrat Medium with tabular figures keeps
    # the columns aligned without a second typeface.
    ("font-family: var(--sans);\n    font-size: 20px;\n    font-weight: 500;",
     "font-family: var(--sans);\n    font-size: 20px;\n    font-weight: 600;",
     "readout value weight"),
    ("letter-spacing: 0.08em;\n    text-transform: uppercase;\n    text-decoration: none;\n    padding: 14px 22px;",
     "font-weight: 700;\n    letter-spacing: 0.06em;\n    text-transform: uppercase;\n    text-decoration: none;\n    padding: 14px 22px;",
     "CTA is Montserrat Bold"),
])

# ------------------------------------------------------------------ code ----
patch("build/build.py", [
    ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap",
     "https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap",
     "Montserrat webfont"),
    ('<meta name="theme-color" content="#0A0D0F">',
     '<meta name="theme-color" content="#1F292E">', "theme colour"),
    ("rect width='32' height='32' fill='%230A0D0F'", "rect width='32' height='32' fill='%231F292E'",
     "favicon ground"),
    ("stroke='%23ED6D20'", "stroke='%23FA6914'", "favicon stroke"),
])

# The speed ramp is now four sanctioned tints of MA Orange, light to dark. It is
# monotonic in lightness, which is what a sequential scale needs, and it avoids
# inventing the browns and creams the old ramp used.
patch("app.js", [
    ("const RAMP = ['#5A2609', '#A8480F', '#ED6D20', '#F9A463', '#FFD9B0'];",
     "const RAMP = ['#FA6914', '#FB8743', '#FCA572', '#FDC3A1'];",
     "speed ramp -> MA Orange tints"),
    ("ctx.strokeStyle = '#1B2429';", "ctx.strokeStyle = '#3A4347';", "unlit circuit -> MA Grey 88%"),
    ("ctx.fillStyle = '#FFF6EE';", "ctx.fillStyle = '#FFFFFF';", "car marker -> MA White"),
    ("ctx.strokeStyle = 'rgba(255,214,178,0.28)';", "ctx.strokeStyle = 'rgba(250,105,20,0.45)';",
     "car halo -> MA Orange"),
])

patch("build/og.py", [
    ("GROUND = (0x0A, 0x0D, 0x0F)", "GROUND = (0x1F, 0x29, 0x2E)   # MA Grey", "og ground"),
    ("DIM = (0x1B, 0x24, 0x29)", "DIM = (0x3A, 0x43, 0x47)      # MA Grey, 88% tint", "og dim"),
    ("ACCENT = (0xED, 0x6D, 0x20)", "ACCENT = (0xFA, 0x69, 0x14)   # MA Orange", "og accent"),
    ("RAMP = [(0x5A, 0x26, 0x09), (0xA8, 0x48, 0x0F), (0xED, 0x6D, 0x20),\n        (0xF9, 0xA4, 0x63), (0xFF, 0xD9, 0xB0)]",
     "# Sanctioned tints of MA Orange: 100%, 80%, 60%, 40%.\nRAMP = [(0xFA, 0x69, 0x14), (0xFB, 0x87, 0x43),\n        (0xFC, 0xA5, 0x72), (0xFD, 0xC3, 0xA1)]",
     "og ramp"),
])

# ------------------------------------------------- headline punctuation -----
# "All headlines should be set in sentence case with no punctuation at end."
# "Punctuation should be used at end of subhead."
for path in ("index.template.html", "course.template.html", "build/build.py"):
    s = io.open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    before = s
    s = re.sub(r"(<h1>[^<]*?)\.(</h1>)", r"\1\2", s)
    s = re.sub(r"(<h2>[^<]*?)\.(</h2>)", r"\1\2", s)
    s = re.sub(r"(<h3>[^<]*?)\.(</h3>)", r"\1\2", s)
    s = re.sub(r'(<p class="label">[^<.]*?)(</p>)', r"\1.\2", s)
    if s != before:
        io.open(path, "w", encoding="utf-8", newline="\n").write(s)
        print(f"  ok: headline/subhead punctuation in {path}")
