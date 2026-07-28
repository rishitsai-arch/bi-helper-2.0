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
"""

def compile_full_report(report_plan: str, qa_history: list) -> str:
    """
    Bundles the LLM-generated report plan together with every question the
    user has actually asked Vanna (and the real data it returned) into a
    single downloadable markdown report.
    qa_history: list of dicts, each with keys 'question', 'sql', 'df' (pandas DataFrame)
    """
    parts = ["# Power BI Report Plan\n", report_plan.strip(), "\n\n---\n"]

    if qa_history:
        parts.append("\n# Data Q&A — Real Results\n")
        for i, qa in enumerate(qa_history, start=1):
            parts.append(f"\n## Q{i}: {qa['question']}\n")
            parts.append(f"```sql\n{qa['sql']}\n```\n")
            parts.append(qa["df"].to_markdown(index=False))
            parts.append("\n")
    else:
        parts.append("\n_No questions were asked yet — ask Vanna some questions above before generating the full report._\n")

    return "\n".join(parts)
