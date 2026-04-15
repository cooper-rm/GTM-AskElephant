"""
Part 1 Brief PDF Generator — AskElephant Outside-In Read
Usage: python generate_brief.py
Output: part1_brief.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ─── CONFIG ───────────────────────────────────────────────────────────
OUTPUT_FILE = "part1_brief.pdf"
TITLE = "AskElephant \u2014 GTM Engineer Pre-Work"
AUTHOR = "Morgan Cooper, M.S."
DATE = "April 2026"

FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BOLD_ITALIC = "Helvetica-BoldOblique"
FONT_SIZE = 11
LEADING = 15
MARGIN = 1 * inch
LINK_COLOR = HexColor("#1a0dab")

# ─── REFERENCES ───────────────────────────────────────────────────────
# Add references here as you build out the brief.
# Format: (person, title, company, source_label, url)

REFERENCES = [
    {
        "id": 1,
        "person": "Kevin",
        "title": "RevOps",
        "company": "Prophetic Software",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 2,
        "person": "Brittany Vandall-Miller",
        "title": "Director of Sales and Business Development",
        "company": "Trailway Growth",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 3,
        "person": "Italo Leiva",
        "title": "Partner",
        "company": "Peddle",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 4,
        "person": "Multiple customers",
        "title": "Various",
        "company": "Vendilli, alldemand, Revvy, hapily, 1406 Consulting, Mind and Metrics",
        "source": "HubSpot ecosystem customers identified from testimonials and case studies",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 5,
        "person": "Multiple customers",
        "title": "Various",
        "company": "Finally, Copper, Peddle, Intelligent Technical Solutions",
        "source": "Mid-market customers identified from public company data",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 6,
        "person": "Greg Larsen",
        "title": "Consultant",
        "company": "Catalyst Sales Consulting",
        "source": "Website testimonial on Gong limitations",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 7,
        "person": "Eric Maida",
        "title": "VP of Growth",
        "company": "TrustModel",
        "source": "Website testimonial on Gong comparison",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 8,
        "person": "Kyleah Etherton",
        "title": "RevOps",
        "company": "Tilt",
        "source": "Website testimonial on cancelling Gong",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 9,
        "person": "Clay",
        "title": "",
        "company": "Clay",
        "source": "Product description \u2014 data enrichment and outbound prospecting platform",
        "url": "https://www.clay.com",
    },
    {
        "id": 10,
        "person": "11x",
        "title": "",
        "company": "11x",
        "source": "Product description \u2014 AI-powered autonomous SDR platform",
        "url": "https://www.11x.ai",
    },
    {
        "id": 11,
        "person": "Cognism",
        "title": "",
        "company": "Cognism",
        "source": "State of Cold Calling Report \u2014 cold call success rates dropped from 4.82% to 2.3%",
        "url": "https://www.cognism.com/blog/cold-calling-success-rates",
    },
    {
        "id": 12,
        "person": "Landbase",
        "title": "",
        "company": "Landbase (citing Gartner)",
        "source": "B2B contact data accuracy \u2014 70% of CRM data is outdated, incomplete, or inaccurate",
        "url": "https://www.landbase.com/blog/b2b-contact-data-accuracy-statistic",
    },
    {
        "id": 13,
        "person": "Gartner",
        "title": "",
        "company": "Gartner",
        "source": "Data quality research \u2014 poor data costs organizations $12.9\u201315M annually",
        "url": "https://www.gartner.com/en/data-analytics/topics/data-quality",
    },
    {
        "id": 14,
        "person": "Salesforce",
        "title": "",
        "company": "Salesforce",
        "source": "2024 State of Sales Report \u2014 reps spend 70% of time on non-selling tasks",
        "url": "https://www.salesforce.com/news/stories/sales-research-2023/",
    },
    {
        "id": 15,
        "person": "Cooper, M.R. & Busch, M.",
        "title": "",
        "company": "Regis University",
        "source": "Capacity-Limited Failure in Approximate Nearest Neighbor Search on Image Embedding Spaces. J. Imaging 2026, 12, 55",
        "url": "https://doi.org/10.3390/jimaging12020055",
    },
]


def ref(n):
    """Inline reference marker: [1], [2], etc."""
    return f'<super><font size="8">[{n}]</font></super>'


def link(url, text):
    """Clickable hyperlink."""
    return f'<a href="{url}" color="#{LINK_COLOR.hexval()[2:]}">{text}</a>'


def quote(text):
    """Italic quote."""
    return f'<i>\u201c{text}\u201d</i>'


# ─── STYLES ───────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName=FONT_BODY,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=HexColor("#555555"),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName=FONT_BOLD,
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        fontName=FONT_BODY,
        fontSize=FONT_SIZE,
        leading=LEADING,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="BodyBold",
        fontName=FONT_BOLD,
        fontSize=FONT_SIZE,
        leading=LEADING,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="RefItem",
        fontName=FONT_BODY,
        fontSize=10,
        leading=13,
        leftIndent=24,
        firstLineIndent=-24,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Placeholder",
        fontName=FONT_ITALIC,
        fontSize=FONT_SIZE,
        leading=LEADING,
        textColor=HexColor("#999999"),
        spaceAfter=8,
    ))
    return styles


# ─── CONTENT ──────────────────────────────────────────────────────────
# Edit your brief content here. Use ref(n) for citations, quote() for
# direct quotes, link() for hyperlinks, and <b>...</b> for bold.

def build_content(styles):
    story = []
    s = styles

    # ── Title page ──
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("AskElephant", s["DocTitle"]))
    story.append(Spacer(1, 24))
    story.append(HRFlowable(
        width="40%", thickness=1,
        color=HexColor("#333333"), spaceAfter=24
    ))
    story.append(Paragraph("GTM Engineer Pre-Work", s["DocSubtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(AUTHOR, s["DocSubtitle"]))
    story.append(Paragraph(DATE, s["DocSubtitle"]))
    story.append(PageBreak())

    # ── Question 1 ──
    story.append(Paragraph(
        "1. Who does AskElephant sell to?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "Based on AskElephant\u2019s public customer base, the current core is "
        "clearly <b>SMB</b> \u2014 sales and CS leaders at 20\u2013100 person B2B "
        "companies running HubSpot, with heavy concentration in the HubSpot "
        "ecosystem itself " + ref(4) + ". There\u2019s a mild tilt toward "
        "<b>mid-market (100\u20131,000 employees)</b> with customers like Finally, "
        "Copper, Peddle, and ITS already on the platform " + ref(5) + ", and "
        "signals that a GTM play targeting mid-market is in motion. That\u2019s "
        "where the real opportunity lives: companies that use technology daily "
        "but don\u2019t have the technical depth to build automation themselves, "
        "with distinct sales, CS, implementation, and RevOps teams that create 50+ seat "
        "expansion opportunities. The trigger is <b>post-call-recorder "
        "disillusionment</b>: these teams adopted Fathom and Fireflies for "
        "recording but nobody is closing the loop from transcript to CRM "
        "update, follow-up, and pipeline accuracy \u2014 automatically "
        + ref(1) + ref(2) + ref(3) + ".",
        s["Body"],
    ))

    # ── Question 2 ──
    story.append(Paragraph(
        "2. What is AskElephant actually building?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "AskElephant is building autonomous infrastructure that captures, "
        "routes, and acts on revenue data end-to-end \u2014 AI is the engine, "
        "not the product. It starts with the call, but the value is everything "
        "that happens after: CRM fields written, follow-ups drafted, next "
        "steps pushed, forecasts updated, handoffs generated \u2014 without a "
        "rep touching it. Today, every competitor owns a slice: Gong owns "
        "conversation intelligence but charges enterprise prices and struggles "
        "with accurate CRM field writes " + ref(6) + ref(7) + ref(8)
        + "; Fathom and Fireflies own the transcript but the data stays in a "
        "silo " + ref(3) + "; Clay " + ref(9) + " and 11x " + ref(10)
        + " own pre-sale prospecting and outbound; Clari owns forecasting but "
        "reads from the same dirty CRM data everyone else ignores. AskElephant "
        "is positioning to own the entire revenue operations layer \u2014 pre-sale, "
        "active selling, and post-sale \u2014 not just the connective tissue between "
        "these tools, but the replacement for needing them separately at all. "
        "The lane is: one system that makes the CRM accurate, acts on that "
        "data, and does it at a price point any company size can afford.",
        s["Body"],
    ))

    # ── Question 3 ──
    story.append(Paragraph(
        "3. Three revenue-work problems customers actually feel.",
        s["SectionHeader"],
    ))
    story.append(Paragraph(
        "<b>Outbound is dying a slow death.</b> Cold call success rates "
        "collapsed 52% in a single year \u2014 from 4.82% to 2.3% "
        + ref(11) + ". Less than 1 in 50 calls converts. Revenue teams are "
        "doing more work for fewer results.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Revenue data is a swamp, not a structured lake.</b> 70% of CRM "
        "data is outdated, incomplete, or inaccurate " + ref(12) + ". "
        "Gartner estimates poor data quality costs organizations "
        "$12.9\u201315 million annually " + ref(13) + ". Reps don\u2019t update "
        "fields. Notes live in someone\u2019s head. Forecasts are built on "
        "whatever someone remembers to enter.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Reps spend more time on admin than selling.</b> 70% of a sales "
        "rep\u2019s time goes to non-selling tasks \u2014 54% of the workweek is "
        "just data handling " + ref(14) + ". That\u2019s over 21 hours a week "
        "managing information instead of engaging customers. The systems "
        "revenue teams use create busywork instead of eliminating it.",
        s["Body"],
    ))

    # ── Question 4 ──
    story.append(Paragraph(
        "4. The sharpest thing I\u2019d change about the story.",
        s["SectionHeader"],
    ))
    story.append(Paragraph(
        "<b>Stop leading with AI. Lead with data.</b>",
        s["Body"],
    ))
    story.append(Paragraph(
        "AskElephant\u2019s current story is \u201cAI employees for revenue teams.\u201d "
        "The problem is that every tool in this space says the same thing. "
        "What actually makes AskElephant defensible isn\u2019t the AI \u2014 it\u2019s the "
        "data layer underneath. AskElephant sits on every call, every CRM "
        "field, every follow-up, every handoff across the entire revenue "
        "cycle. That\u2019s a proprietary data asset that compounds over time. "
        "The AI is replaceable \u2014 models get commoditized, prompts get copied, "
        "agents get rebuilt. The structured revenue data that feeds them is not.",
        s["Body"],
    ))
    story.append(Paragraph(
        "If I had one call to change the narrative: position AskElephant as "
        "the revenue data platform that happens to automate with AI, not the "
        "AI platform that happens to touch data. The moat isn\u2019t the model. "
        "The moat is that no competitor has the same depth of structured, "
        "cross-functional revenue data to train against, score with, or act "
        "on. When the AI layer is grounded in real data, the outputs get "
        "better over time. When it\u2019s not, it\u2019s just another prompt wrapper "
        "waiting to be replaced.",
        s["Body"],
    ))

    # ── Part 2: Motion Pick ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Part 2 \u2014 Pick Your Motion", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Motion: C \u2014 Closed-Won Activation</b>", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "I ruled out Motion A due to external data access \u2014 mapping a buying "
        "committee requires LinkedIn, Apollo, and ZoomInfo, all paywalled or "
        "rate-limited. Building the system would mean fighting data access, not "
        "demonstrating architecture. Motion B requires time series anomaly "
        "detection to identify when and why a deal went dark \u2014 that needs "
        "sequential activity data that\u2019s difficult to synthesize realistically, "
        "and the complexity of the detection layer would dominate the build time.",
        s["Body"],
    ))
    story.append(Paragraph(
        "Motion C has a fixed, consistent trigger: the deal closes, the handoff "
        "runs. The variance is in the deal attributes, not the process shape. I "
        "can engineer tabular features from raw deal data (notes, CRM fields, "
        "contacts, call context) and train real models on it. Rather than "
        "building an AI system that happens to touch data, I wanted to "
        "demonstrate a <b>data system that incorporates agent orchestration.</b> "
        "The ML models make the judgment calls \u2014 an XGBoost churn classifier "
        "scores risk with SHAP explainability, and an HNSW-indexed embedding "
        "space retrieves historically similar deals with their actual outcomes "
        "as grounded context for agents. The HNSW parameter tuning draws on my "
        "own published research on capacity-limited failure in approximate "
        "nearest neighbor search " + ref(15) + ". The agents are downstream: "
        "they generate artifacts based on what the data already decided, not "
        "what a prompt guessed.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Working vs. shipped:</b> the system produces a different handoff "
        "for a high-risk, single-threaded deal than for a smooth enterprise "
        "close \u2014 because the models learned the difference, not because someone "
        "wrote two templates.",
        s["Body"],
    ))

    # ── References page ──
    story.append(PageBreak())
    story.append(Paragraph("References", s["SectionHeader"]))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=HexColor("#cccccc"), spaceAfter=12
    ))

    for r in REFERENCES:
        ref_text = (
            f"[{r['id']}] {r['person']}, {r['title']} at {r['company']}. "
            f"{r['source']}. {link(r['url'], r['url'])}"
        )
        story.append(Paragraph(ref_text, s["RefItem"]))

    return story


# ─── BUILD PDF ────────────────────────────────────────────────────────

def main():
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=TITLE,
        author=AUTHOR,
    )
    styles = build_styles()
    story = build_content(styles)
    doc.build(story)
    print(f"Generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
