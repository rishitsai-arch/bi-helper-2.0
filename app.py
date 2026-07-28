"""
app.py
Streamlit UI. Ties together data_parser.py, llm_client.py, and prompts.py.
Run locally with:  streamlit run app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

from data_parser import (
    parse_csv_excel,
    parse_db,
    profile_dataframe,
    profile_text_description,
    profile_dax_model,
    summarize_for_prompt,
)
from llm_client import generate
from prompts import build_report_prompt, compile_full_report
from vanna_client import get_vanna, train_on_schema, ask_vanna

# Load .env file if present (local development only — never committed to GitHub)
load_dotenv()


def get_saved_key(provider: str) -> str:
    """
    Auto-detect an API key so the user doesn't have to paste it every time.
    Checks, in order:
      1. Streamlit secrets (used when deployed on Streamlit Community Cloud)
      2. Environment variables / .env file (used for local development)
    Falls back to an empty string, which means the sidebar box stays blank
    and the user pastes it manually.
    """
    env_var_name = "GROQ_API_KEY" if provider == "groq" else "GEMINI_API_KEY"

    # 1. Streamlit secrets (deployed)
    try:
        if env_var_name in st.secrets:
            return st.secrets[env_var_name]
    except Exception:
        pass  # no secrets.toml present — that's fine, just move on

    # 2. .env / environment variable (local)
    return os.getenv(env_var_name, "")


st.set_page_config(page_title="BI Report AI", layout="wide")
st.title("AI-Assisted Power BI Report Planner")
st.caption("Give it your data, get a report structure, DAX measures, and a step-by-step build guide.")

# ---------------- Sidebar: provider + API key ----------------
with st.sidebar:
    st.header("LLM Settings")
    provider = st.selectbox("Provider", ["gemini", "groq"], index=0)

    # Auto-fills from .env (local) or st.secrets (deployed) if found.
    # Still shown/editable in the box so you can override it any time.
    auto_key = get_saved_key(provider)
    api_key = st.text_input(
        "API Key",
        type="password",
        value=auto_key,
        help="Groq: console.groq.com | Gemini: aistudio.google.com/apikey",
    )
    if auto_key:
        st.caption("✅ Key auto-loaded from saved settings")

    st.markdown("---")
    st.caption("Get a free key:")
    st.markdown("- [Groq Console](https://console.groq.com)")
    st.markdown("- [Google AI Studio](https://aistudio.google.com/apikey)")

# ---------------- Input selection ----------------
input_type = st.radio(
    "Input type",
    ["CSV/Excel", "Database", "Text description", "Existing DAX/model"],
    horizontal=True,
)

data_summary = None

if input_type == "CSV/Excel":
    file = st.file_uploader("Upload file", type=["csv", "xlsx"])
    if file:
        df = parse_csv_excel(file)
        st.dataframe(df.head())
        data_summary = summarize_for_prompt(profile_dataframe(df), "csv")

elif input_type == "Database":
    db_type = st.selectbox("Database type", ["postgres", "mysql", "sqlite"])

    if db_type == "sqlite":
        st.caption("Upload a .db file — e.g. the sample_sales.db provided for testing.")
        sqlite_file = st.file_uploader("SQLite file", type=["db", "sqlite", "sqlite3"])
        query = st.text_area("SQL query", "SELECT * FROM customers LIMIT 1000")
        if sqlite_file and st.button("Load from DB"):
            try:
                local_path = f"/tmp/{sqlite_file.name}"
                with open(local_path, "wb") as f:
                    f.write(sqlite_file.getbuffer())
                df = parse_db(f"sqlite:///{local_path}", query)
                st.dataframe(df.head())
                data_summary = summarize_for_prompt(profile_dataframe(df), "db")
                st.session_state["data_summary"] = data_summary
                st.session_state["db_conn_str"] = local_path  # Vanna wants the raw file path for sqlite
                st.session_state["db_type"] = "sqlite"
            except Exception as e:
                st.error(f"Could not load SQLite file: {e}")
    else:
        st.caption("Example: postgresql://user:password@host:5432/dbname")
        conn_str = st.text_input("Connection string")
        query = st.text_area("SQL query", "SELECT * FROM your_table LIMIT 1000")
        if st.button("Load from DB"):
            try:
                df = parse_db(conn_str, query)
                st.dataframe(df.head())
                data_summary = summarize_for_prompt(profile_dataframe(df), "db")
                st.session_state["data_summary"] = data_summary
                st.session_state["db_conn_str"] = conn_str
                st.session_state["db_type"] = db_type
            except Exception as e:
                st.error(f"Could not connect / query: {e}")

    data_summary = st.session_state.get("data_summary")

elif input_type == "Text description":
    text = st.text_area("Describe your data / business need", height=150)
    if text:
        data_summary = summarize_for_prompt(profile_text_description(text), "text")

elif input_type == "Existing DAX/model":
    dax_text = st.text_area("Paste existing DAX measures or model schema", height=200)
    if dax_text:
        data_summary = summarize_for_prompt(profile_dax_model(dax_text), "dax")

context = st.text_area(
    "Optional: business context (who's the audience, what decisions will this drive?)"
)

# ---------------- Generate ----------------
if st.button("Generate Report Plan", type="primary", disabled=not (data_summary and api_key)):
    with st.spinner("Generating your report plan..."):
        try:
            prompt = build_report_prompt(data_summary, context)
            result = generate(provider, api_key, prompt)
            st.session_state["report_result"] = result
        except Exception as e:
            st.error(f"Generation failed: {e}")

if not api_key:
    st.info("Enter an API key in the sidebar to enable generation.")

# ---------------- Show report plan ----------------
if st.session_state.get("report_result"):
    result = st.session_state["report_result"]
    st.markdown(result)
    st.download_button("Download as Markdown", result, file_name="report_plan.md")

    # ---------------- Vanna: ask your own questions on the real DB ----------------
    has_live_db = st.session_state.get("db_conn_str") and st.session_state.get("db_type")

    if "qa_history" not in st.session_state:
        st.session_state["qa_history"] = []

    if has_live_db:
        st.markdown("---")
        st.subheader("Ask your own questions (Vanna)")
        st.caption(
            "Type a question in plain English. Uses your Groq key to generate SQL, "
            "runs it against your connected database, and shows the real result."
        )

        if provider != "groq" or not api_key:
            st.warning("This uses your Groq key specifically — switch the provider to Groq in the sidebar to enable it.")
        else:
            user_question = st.text_input("Your question", placeholder="e.g. What is total revenue by region?")

            if st.button("Ask") and user_question:
                with st.spinner("Thinking..."):
                    try:
                        vn = get_vanna(api_key, st.session_state["db_conn_str"], st.session_state["db_type"])
                        if not st.session_state.get("vanna_trained"):
                            train_on_schema(vn, st.session_state["db_type"])
                            st.session_state["vanna_trained"] = True
                        sql, df_result, fig = ask_vanna(vn, user_question)
                        st.session_state["qa_history"].insert(
                            0, {"question": user_question, "sql": sql, "df": df_result, "fig": fig}
                        )
                    except Exception as e:
                        st.error(f"Could not answer this question: {e}")

            # Show history, most recent first
            for qa in st.session_state["qa_history"]:
                st.markdown(f"**Q: {qa['question']}**")
                st.code(qa["sql"], language="sql")
                st.dataframe(qa["df"])
                if qa["fig"] is not None:
                    st.plotly_chart(qa["fig"], use_container_width=True)
                st.markdown("---")

            # ---------------- Generate full report from plan + everything asked so far ----------------
            if st.session_state["qa_history"]:
                st.subheader("Generate Full Report")
                st.caption("Bundles the report plan above with every question you've asked and its real results into one downloadable file.")
                if st.button("Generate Full Report", type="primary"):
                    full_report = compile_full_report(result, st.session_state["qa_history"])
                    st.session_state["full_report"] = full_report

                if st.session_state.get("full_report"):
                    st.download_button(
                        "Download Full Report (Markdown)",
                        st.session_state["full_report"],
                        file_name="full_report.md",
                    )
