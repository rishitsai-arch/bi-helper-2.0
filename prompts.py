"""
prompts.py
Prompt templates. This is the file you'll iterate on most as you tune
output quality — editing this never requires touching data_parser.py,
llm_client.py, or app.py.
"""


def build_report_prompt(data_summary: str, business_context: str = "") -> str:
    return f"""You are a senior Power BI developer. Based on the data below, produce a complete Power BI report plan.

DATA SUMMARY:
{data_summary}

BUSINESS CONTEXT (if provided):
{business_context or "Not provided — infer a reasonable business use case from the data."}

Respond in exactly these three sections, clearly labeled:

## 1. REPORT STRUCTURE
- Suggested report pages (name each page and its purpose)
- Key KPIs / cards for each page
- Recommended visual types per section (bar, line, matrix, decomposition tree, etc.) and why
- Suggested filters/slicers and drill-down hierarchy

## 2. DAX MEASURES
- List concrete DAX measures needed (name + full formula), covering core KPIs, YoY/MoM comparisons, and any ratios relevant to this data
- Note any calculated columns or star-schema relationship changes needed first

## 3. STEP-BY-STEP BUILD GUIDE
Write this as literal numbered steps a developer follows in Power BI Desktop, e.g.:
1. Get Data > [source type] > connect to ...
2. In Power Query, transform ...
3. Build relationships: ...
4. Create measure: ...
5. Add visual: ... on page ...
(Continue until the full report is buildable end-to-end.)

## 4. VANNA QUESTIONS
List 5-8 plain-English business questions (one per line, numbered) that,
if answered with real data from the database, would populate the KPIs and
visuals above. Write these as questions a non-technical stakeholder would
ask out loud — e.g. "What were total sales by region last quarter?" — NOT
as SQL or DAX. These will be run against the live database automatically.
"""


def extract_vanna_questions(report_text: str) -> list[str]:
    """
    Pulls the numbered questions out of the '## 4. VANNA QUESTIONS' section
    of the LLM's report output, so they can be fed into Vanna one by one.
    """
    if "VANNA QUESTIONS" not in report_text:
        return []

    section = report_text.split("VANNA QUESTIONS", 1)[1]
    questions = []
    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading numbering like "1.", "1)", "- "
        stripped = line.lstrip("0123456789.)- ").strip()
        if stripped and len(stripped) > 5:
            questions.append(stripped)
    return questions
