"""Generate the MachineSense AI hackathon pitch deck (python-pptx)."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---- palette (matches the dashboard) ----
BG      = RGBColor(0x0A, 0x0F, 0x17)
BG2     = RGBColor(0x0F, 0x17, 0x23)
PANEL   = RGBColor(0x16, 0x22, 0x33)
PANEL2  = RGBColor(0x1B, 0x2A, 0x3D)
BORDER  = RGBColor(0x25, 0x38, 0x50)
TEXT    = RGBColor(0xE6, 0xEE, 0xF7)
MUTED   = RGBColor(0x9A, 0xAD, 0xC4)
FAINT   = RGBColor(0x6B, 0x82, 0x9C)
CYAN    = RGBColor(0x22, 0xD3, 0xEE)
SKY     = RGBColor(0x38, 0xBD, 0xF8)
GREEN   = RGBColor(0x34, 0xD3, 0x99)
AMBER   = RGBColor(0xFB, 0xBF, 0x24)
ORANGE  = RGBColor(0xFB, 0x92, 0x3C)
RED     = RGBColor(0xF4, 0x3F, 0x5E)
PURPLE  = RGBColor(0xA7, 0x8B, 0xFA)

HEAD = "Century Schoolbook"   # safe serif with personality
BODY = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]


def slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    r.fill.solid(); r.fill.fore_color.rgb = bg; r.line.fill.background()
    r.shadow.inherit = False
    return s


def _noline(sh):
    sh.line.fill.background(); sh.shadow.inherit = False


def rect(s, x, y, w, h, fill=PANEL, line=None, radius=True):
    shape = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        try: shape.adjustments[0] = 0.06
        except Exception: pass
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    if line: shape.line.color.rgb = line; shape.line.width = Pt(1)
    else: shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def circle(s, x, y, d, fill):
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = fill; _noline(c)
    return c


def text(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space=1.0, wrap=True):
    """runs: list of paragraphs; each paragraph is list of (txt, size, color, bold, italic, font)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = space
        for (txt, size, color, bold, italic, font) in para:
            r = p.add_run(); r.text = txt
            r.font.size = Pt(size); r.font.color.rgb = color
            r.font.bold = bold; r.font.italic = italic; r.font.name = font
    return tb


def R(txt, size, color=TEXT, bold=False, italic=False, font=BODY):
    return (txt, size, color, bold, italic, font)


def tag(s, x, y, label, color, w=1.7):
    """small pill chip"""
    p = rect(s, x, y, w, 0.34, fill=PANEL2, radius=True)
    try: p.adjustments[0] = 0.5
    except Exception: pass
    text(s, x, y, w, 0.34, [[R(label, 11, color, True)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def iconbox(s, x, y, glyph, color, d=0.62):
    c = rect(s, x, y, d, d, fill=PANEL2, radius=True)
    try: c.adjustments[0] = 0.35
    except Exception: pass
    text(s, x, y, d, d, [[R(glyph, 18, color, True)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# =====================================================================
# 1 — TITLE
# =====================================================================
s = slide(BG)
# subtle brand mark
rect(s, 0.9, 1.55, 0.9, 0.9, fill=CYAN, radius=True)
text(s, 0.9, 1.55, 0.9, 0.9, [[R("⚙", 34, BG)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, 2.05, 1.5, 9, 1.1, [[R("MachineSense ", 52, TEXT, True, False, HEAD),
                             R("AI", 52, CYAN, True, False, HEAD)]], anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.95, 2.95, 11, 0.7,
     [[R("Explainable Industrial Intelligence for Indian Industry", 24, MUTED, False, True, HEAD)]])
text(s, 0.95, 3.75, 11.4, 0.9,
     [[R("Predictive maintenance · Digital-twin simulation · Energy optimization — powered by IoT and Explainable AI",
         15, FAINT)]])
# stat strip
stats = [("SIH 2026", "Software Edition", CYAN), ("63M+", "Factories & Workshops", GREEN),
         ("Industry 4.0", "Domain", PURPLE), ("Working", "Prototype Status", AMBER)]
x = 0.95
for val, lab, col in stats:
    rect(s, x, 4.95, 2.75, 1.15, fill=BG2, line=BORDER)
    text(s, x + 0.25, 5.12, 2.4, 0.5, [[R(val, 24, col, True, False, HEAD)]])
    text(s, x + 0.25, 5.62, 2.4, 0.4, [[R(lab.upper(), 10.5, FAINT, True)]])
    x += 2.95
text(s, 0.95, 6.75, 11, 0.4, [[R("Smart India Hackathon 2026  ·  Industry 4.0 · AI · IoT · Digital Twin", 12, FAINT, True)]])

# =====================================================================
# 2 — PROBLEM
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "THE PROBLEM", RED, w=1.9)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("Indian factories are flying blind on machine health", 34, TEXT, True, False, HEAD)]])
text(s, 0.9, 2.05, 11.5, 0.6,
     [[R("Small and medium manufacturers keep the country running — but can't afford the Industry 4.0 tools that prevent costly breakdowns.", 15, MUTED)]])

cards = [
    ("Unplanned Downtime", "Sudden machine failures halt production lines with no warning, missing deadlines and orders.", RED),
    ("High Maintenance Cost", "Reactive, fix-it-when-it-breaks maintenance is far costlier than planned intervention.", ORANGE),
    ("Energy Wastage", "Inefficient, ageing machines silently burn excess power — a cost few factories even measure.", AMBER),
    ("No Affordable Industry 4.0", "Existing predictive-maintenance suites are enterprise-priced and out of reach.", PURPLE),
]
x, y = 0.9, 2.95
for i, (t, d, col) in enumerate(cards):
    cx = x + (i % 2) * 5.95
    cy = y + (i // 2) * 1.95
    rect(s, cx, cy, 5.6, 1.72, fill=PANEL, line=BORDER)
    iconbox(s, cx + 0.3, cy + 0.32, "!", col)
    text(s, cx + 1.15, cy + 0.28, 4.2, 0.5, [[R(t, 17, TEXT, True, False, HEAD)]])
    text(s, cx + 1.15, cy + 0.78, 4.25, 0.85, [[R(d, 12.5, MUTED)]])

# =====================================================================
# 3 — SOLUTION
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "OUR SOLUTION", CYAN, w=1.9)
text(s, 0.9, 1.15, 12.0, 0.7, [[R("One affordable platform. Total machine intelligence.", 30, TEXT, True, False, HEAD)]])
text(s, 0.9, 2.35, 11.6, 0.9,
     [[R("MachineSense AI attaches low-cost IoT sensors to any machine, streams the data to an AI engine, and turns it into a live ",
         15, MUTED), R("Machine Health Score", 15, CYAN, True),
       R(", failure predictions, energy insights and clear maintenance actions — validated in a digital twin before you act.", 15, MUTED)]])

steps = [("Sense", "Low-cost IoT sensors capture vibration, temperature, current, sound & power", CYAN),
         ("Analyse", "AI scores health, detects anomalies and predicts remaining useful life", PURPLE),
         ("Validate", "Digital twin simulates the fix and its impact before any spanner is turned", SKY),
         ("Act", "Operators get prioritised, explainable maintenance & energy recommendations", GREEN)]
x, y = 0.9, 3.65
w = 2.85
for i, (t, d, col) in enumerate(steps):
    cx = x + i * (w + 0.13)
    rect(s, cx, y, w, 2.9, fill=PANEL, line=BORDER)
    circle(s, cx + 0.3, y + 0.32, 0.66, col)
    text(s, cx + 0.3, y + 0.32, 0.66, 0.66, [[R(str(i + 1), 22, BG, True, False, HEAD)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, cx + 0.3, y + 1.15, w - 0.55, 0.5, [[R(t, 18, TEXT, True, False, HEAD)]])
    text(s, cx + 0.3, y + 1.68, w - 0.55, 1.1, [[R(d, 12, MUTED)]])

# =====================================================================
# 4 — HOW IT WORKS (architecture)
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "ARCHITECTURE", SKY, w=1.9)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("From factory floor to actionable insight", 32, TEXT, True, False, HEAD)]])

flow = ["Industrial\nMachines", "IoT\nSensors", "Edge\nGateway", "Cloud", "AI\nEngine", "Digital\nTwin", "Recommend-\nations", "Dashboard"]
cols = [FAINT, CYAN, SKY, MUTED, PURPLE, SKY, GREEN, CYAN]
x, y = 0.75, 2.75
bw, bh, gap = 1.34, 1.15, 0.18
for i, (label, col) in enumerate(zip(flow, cols)):
    cx = x + i * (bw + gap)
    rect(s, cx, y, bw, bh, fill=PANEL, line=BORDER)
    text(s, cx, y, bw, bh, [[R(label, 12.5, TEXT, True)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=0.95)
    if i < len(flow) - 1:
        text(s, cx + bw - 0.02, y, gap + 0.06, bh, [[R("›", 22, CYAN, True)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# layer explanations
lay = [("Edge", "Sensors + ESP32 gateway pre-process signals on-site for low latency", CYAN),
       ("Cloud + AI", "Time-series models score health, flag anomalies and forecast failures", PURPLE),
       ("Decision", "Digital twin validates actions; dashboard delivers explainable guidance", GREEN)]
x2, y2 = 0.9, 4.5
for i, (t, d, col) in enumerate(lay):
    cx = x2 + i * 3.95
    rect(s, cx, y2, 3.7, 1.75, fill=BG2, line=BORDER)
    iconbox(s, cx + 0.28, y2 + 0.3, "▣", col)
    text(s, cx + 1.1, y2 + 0.3, 2.5, 0.5, [[R(t, 16, TEXT, True, False, HEAD)]])
    text(s, cx + 0.28, y2 + 0.95, 3.2, 0.75, [[R(d, 12, MUTED)]])

# =====================================================================
# 5 — FEATURES
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "CAPABILITIES", GREEN, w=1.9)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("Six capabilities, one platform", 32, TEXT, True, False, HEAD)]])

feats = [
    ("Real-time Monitoring", "Continuous IoT streaming of every critical sensor across the fleet.", CYAN, "◉"),
    ("Predictive Maintenance", "Remaining-useful-life & failure-risk forecasts from live degradation trends.", SKY, "◔"),
    ("Explainable AI", "Every score broken down by sensor with plain-language root-cause reasoning.", PURPLE, "◈"),
    ("Energy Optimization", "Detects waste and quantifies recoverable cost and CO₂ across machines.", GREEN, "⚡"),
    ("Digital Twin", "Validate maintenance actions in simulation before touching the real asset.", AMBER, "▣"),
    ("Smart Alerts", "Robust anomaly detection flags issues the moment behaviour deviates.", RED, "!"),
]
x, y = 0.9, 2.35
cw, ch = 3.85, 1.95
for i, (t, d, col, g) in enumerate(feats):
    cx = x + (i % 3) * (cw + 0.12)
    cy = y + (i // 3) * (ch + 0.15)
    rect(s, cx, cy, cw, ch, fill=PANEL, line=BORDER)
    iconbox(s, cx + 0.3, cy + 0.3, g, col)
    text(s, cx + 0.3, cy + 1.02, cw - 0.6, 0.45, [[R(t, 16, TEXT, True, False, HEAD)]])
    text(s, cx + 0.3, cy + 1.45, cw - 0.6, 0.5, [[R(d, 11.5, MUTED)]])

# =====================================================================
# 6 — DIFFERENTIATORS
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "WHY WE WIN", PURPLE, w=1.9)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("What makes MachineSense AI different", 32, TEXT, True, False, HEAD)]])

# big two panels
rect(s, 0.9, 2.35, 5.75, 3.9, fill=PANEL, line=BORDER)
iconbox(s, 1.25, 2.7, "◈", PURPLE, d=0.75)
text(s, 2.2, 2.75, 4.2, 0.6, [[R("Explainable, not a black box", 18, TEXT, True, False, HEAD)]])
text(s, 1.25, 3.7, 5.1, 2.4,
     [[R("Most AI tools output a number you must trust blindly. We show ", 13, MUTED),
       R("exactly which sensor drove the score", 13, CYAN, True),
       R(" and why — in plain English.", 13, MUTED)],
      [R("", 6)],
      [R("• Per-sensor health-impact breakdown", 13, TEXT)],
      [R("• Human-readable root-cause reasoning", 13, TEXT)],
      [R("• Prioritised, actionable recommendations", 13, TEXT)],
      [R("• Builds operator trust and adoption", 13, TEXT)]], space=1.15)

rect(s, 6.95, 2.35, 5.75, 3.9, fill=PANEL, line=BORDER)
iconbox(s, 7.3, 2.7, "▣", AMBER, d=0.75)
text(s, 8.25, 2.75, 4.2, 0.6, [[R("Digital twin de-risks decisions", 18, TEXT, True, False, HEAD)]])
text(s, 7.3, 3.7, 5.1, 2.4,
     [[R("Before spending on a repair, simulate it. The twin projects the ", 13, MUTED),
       R("health, life and energy impact", 13, AMBER, True),
       R(" of each action.", 13, MUTED)],
      [R("", 6)],
      [R("• Test 'what-if' fixes with zero risk", 13, TEXT)],
      [R("• Compare before / after outcomes", 13, TEXT)],
      [R("• Avoid unnecessary maintenance spend", 13, TEXT)],
      [R("• Quantify ROI of every action", 13, TEXT)]], space=1.15)

text(s, 0.9, 6.55, 11.8, 0.5,
     [[R("Affordable · India-first · Explainable · Twin-validated — an integrated platform, not a point tool.",
         13, FAINT, False, True)]])

# =====================================================================
# 7 — TECH STACK
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "TECHNOLOGY", CYAN, w=1.9)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("Built on a modern, scalable stack", 32, TEXT, True, False, HEAD)]])

groups = [
    ("Hardware", CYAN, ["ESP32 microcontroller", "Vibration sensor", "Current sensor", "Sound sensor", "Temperature sensor"]),
    ("Software", GREEN, ["Python", "FastAPI", "React frontend", "PostgreSQL", "Docker"]),
    ("AI / Analytics", PURPLE, ["Time-series analysis", "Anomaly detection", "ML health scoring", "RUL prediction", "Digital-twin models"]),
]
x, y = 0.9, 2.4
for i, (title, col, items) in enumerate(groups):
    cx = x + i * 3.95
    rect(s, cx, y, 3.7, 4.05, fill=PANEL, line=BORDER)
    circle(s, cx + 0.3, y + 0.32, 0.4, col)
    text(s, cx + 0.95, y + 0.3, 2.5, 0.5, [[R(title, 17, TEXT, True, False, HEAD)]])
    yy = y + 1.15
    for it in items:
        text(s, cx + 0.4, yy, 0.3, 0.4, [[R("▸", 12, col, True)]])
        text(s, cx + 0.75, yy, 2.7, 0.4, [[R(it, 13, MUTED)]])
        yy += 0.56

# =====================================================================
# 8 — MARKET
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "MARKET OPPORTUNITY", GREEN, w=2.5)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("A vast, underserved market", 32, TEXT, True, False, HEAD)]])

big = [("63M+", "factories & workshops seeking\naffordable digitisation", CYAN),
       ("~30%", "typical downtime reduction\nfrom predictive maintenance", GREEN),
       ("10-20%", "energy savings unlocked\nby continuous optimization", AMBER)]
x, y = 0.9, 2.45
for i, (v, l, col) in enumerate(big):
    cx = x + i * 3.95
    rect(s, cx, y, 3.7, 2.1, fill=BG2, line=BORDER)
    text(s, cx + 0.35, y + 0.35, 3, 0.8, [[R(v, 40, col, True, False, HEAD)]])
    text(s, cx + 0.35, y + 1.25, 3.1, 0.7, [[R(l, 12.5, MUTED)]], space=1.0)

rect(s, 0.9, 4.85, 11.8, 1.75, fill=PANEL, line=BORDER)
text(s, 1.25, 5.1, 11, 0.5, [[R("Go-to-market: SaaS subscription + optional hardware kit", 17, TEXT, True, False, HEAD)]])
text(s, 1.25, 5.7, 11.2, 0.8,
     [[R("A low monthly per-machine fee makes advanced intelligence accessible, with hardware kits and onboarding support as add-ons. Land with one line, expand across the factory — and across a manufacturing cluster.", 13, MUTED)]])

# =====================================================================
# 9 — IMPACT
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "IMPACT", CYAN, w=1.6)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("Measurable outcomes for every factory", 32, TEXT, True, False, HEAD)]])

impacts = [("↓", "Reduce Downtime", "Catch failures before they happen and schedule fixes in planned windows.", GREEN),
           ("₹", "Lower Maintenance Cost", "Shift from reactive to predictive — fix only what needs fixing, when it needs it.", CYAN),
           ("⚡", "Cut Energy Bills", "Surface hidden waste and recover a measurable slice of monthly power spend.", AMBER),
           ("⧗", "Extend Equipment Life", "Reduce stress on assets and defer costly capital replacement.", PURPLE),
           ("◈", "Boost Productivity", "Keep lines running and quality high with always-on machine intelligence.", SKY),
           ("♻", "Improve Sustainability", "Lower energy use and CO₂ — good for cost and for compliance.", GREEN)]
x, y = 0.9, 2.35
cw, ch = 3.85, 1.95
for i, (g, t, d, col) in enumerate(impacts):
    cx = x + (i % 3) * (cw + 0.12)
    cy = y + (i // 3) * (ch + 0.15)
    rect(s, cx, cy, cw, ch, fill=PANEL, line=BORDER)
    circle(s, cx + 0.3, cy + 0.3, 0.6, PANEL2)
    text(s, cx + 0.3, cy + 0.3, 0.6, 0.6, [[R(g, 20, col, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, cx + 1.1, cy + 0.34, cw - 1.3, 0.5, [[R(t, 15.5, TEXT, True, False, HEAD)]])
    text(s, cx + 0.3, cy + 1.05, cw - 0.6, 0.8, [[R(d, 11.5, MUTED)]])

# =====================================================================
# 10 — COST & ROADMAP
# =====================================================================
s = slide(BG)
tag(s, 0.9, 0.7, "INVESTMENT & ROADMAP", AMBER, w=2.7)
text(s, 0.9, 1.15, 11.5, 0.9, [[R("₹19.8 Lakh to a market-ready platform", 32, TEXT, True, False, HEAD)]])

# cost breakdown (left)
rect(s, 0.9, 2.3, 6.6, 4.35, fill=PANEL, line=BORDER)
text(s, 1.2, 2.5, 6, 0.5, [[R("Estimated Project Cost", 16, TEXT, True, False, HEAD)]])
costs = [("AI Research & Model Development", "3,50,000", CYAN),
         ("Software Development", "4,00,000", GREEN),
         ("IoT Sensors & Prototype Hardware", "2,50,000", SKY),
         ("Digital Twin Development", "2,00,000", PURPLE),
         ("Contingency", "2,00,000", FAINT),
         ("Testing, Cloud, UI/UX & Other", "5,80,000", MUTED)]
maxv = 400000
yy = 3.08
for lab, val, col in costs:
    v = int(val.replace(",", ""))
    text(s, 1.2, yy, 3.9, 0.32, [[R(lab, 11.5, TEXT)]])
    text(s, 6.1, yy, 1.2, 0.32, [[R("₹" + val, 11.5, col, True)]], align=PP_ALIGN.RIGHT)
    bw = 6.1 * (v / maxv)
    rect(s, 1.2, yy + 0.3, 6.1, 0.1, fill=PANEL2, radius=False)
    rect(s, 1.2, yy + 0.3, max(0.1, bw), 0.1, fill=col, radius=False)
    yy += 0.5
text(s, 1.2, yy + 0.0, 6, 0.4, [[R("Total   ", 15, TEXT, True), R("₹19,80,000", 15, AMBER, True, False, HEAD)]])

# roadmap (right)
rect(s, 7.7, 2.3, 5.0, 4.35, fill=BG2, line=BORDER)
text(s, 8.0, 2.5, 4.4, 0.5, [[R("Roadmap & Future Scope", 16, TEXT, True, False, HEAD)]])
phases = [("Now", "Working prototype: dashboard, AI engine, digital twin", CYAN),
          ("Next", "Field pilots with industry partners, hardware kit, mobile app", SKY),
          ("Later", "Robotics integration, voice assistant, autonomous scheduling", PURPLE),
          ("Vision", "Federated learning across factories & clusters", GREEN)]
yy = 3.2
for t, d, col in phases:
    circle(s, 8.0, yy + 0.05, 0.24, col)
    text(s, 8.4, yy - 0.02, 4.0, 0.35, [[R(t, 14, TEXT, True, False, HEAD)]])
    text(s, 8.4, yy + 0.33, 4.1, 0.55, [[R(d, 11.5, MUTED)]])
    yy += 0.86

# =====================================================================
# 11 — CLOSING
# =====================================================================
s = slide(BG)
rect(s, 0.9, 1.7, 0.85, 0.85, fill=CYAN, radius=True)
text(s, 0.9, 1.7, 0.85, 0.85, [[R("⚙", 30, BG)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, 2.0, 1.62, 10, 1.0, [[R("Making Industry 4.0 affordable", 40, TEXT, True, False, HEAD)]])
text(s, 2.0, 2.5, 10.5, 0.6, [[R("for every Indian factory.", 40, CYAN, True, False, HEAD)]])
text(s, 0.95, 3.75, 11.4, 0.9,
     [[R("MachineSense AI turns low-cost sensors into predictive, explainable, twin-validated machine intelligence — reducing downtime, cost and energy for the businesses that need it most.",
         15, MUTED)]])

# CTA strip
labels = [("Live Demo", "Interactive dashboard prototype", CYAN),
          ("Full Stack", "FastAPI + AI engine + web UI", GREEN),
          ("Ready to Pilot", "Seeking industry partners", AMBER)]
x = 0.95
for t, d, col in labels:
    rect(s, x, 5.0, 3.8, 1.2, fill=PANEL, line=BORDER)
    text(s, x + 0.3, 5.18, 3.3, 0.45, [[R(t, 16, col, True, False, HEAD)]])
    text(s, x + 0.3, 5.66, 3.3, 0.45, [[R(d, 12, MUTED)]])
    x += 3.98
text(s, 0.95, 6.65, 11, 0.4, [[R("Thank you  ·  MachineSense AI  ·  Smart India Hackathon 2026", 13, FAINT, True)]])

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MachineSenseAI_Pitch_Deck.pptx")
prs.save(out)
print("saved", out, "slides:", len(prs.slides._sldIdLst))
