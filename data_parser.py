"""
data_parser.py
Handles all input types: CSV/Excel, live database, plain text description,
or pasted DAX/semantic model definitions. Every input type gets turned into
a compact text summary that gets fed into the LLM prompt.
"""

import pandas as pd


def parse_csv_excel(uploaded_file):
    """Reads a Streamlit-uploaded CSV or Excel file into a DataFrame."""
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    return df


def parse_db(connection_string: str, query: str):
    """
    Connects to a live database and runs a query.
    connection_string examples:
      postgresql://user:password@host:5432/dbname
      mysql+pymysql://user:password@host:3306/dbname
      mssql+pyodbc://user:password@host/dbname?driver=ODBC+Driver+17+for+SQL+Server
    """
    from sqlalchemy import create_engine
    engine = create_engine(connection_string)
    df = pd.read_sql(query, engine)
    return df


def profile_dataframe(df: pd.DataFrame, max_sample_rows: int = 5) -> dict:
    """Builds a structured profile (columns, types, nulls, samples) from a DataFrame."""
    profile = {
        "row_count": len(df),
        "columns": [],
        "sample_rows": df.head(max_sample_rows).to_dict(orient="records"),
    }
    for col in df.columns:
        col_data = df[col]
        profile["columns"].append({
            "name": col,
            "dtype": str(col_data.dtype),
            "null_pct": round(col_data.isna().mean() * 100, 1),
            "unique_count": int(col_data.nunique()),
            "sample_values": col_data.dropna().unique()[:5].tolist(),
        })
    return profile


def profile_text_description(text: str) -> dict:
    """Wraps a free-text data/business description."""
    return {"raw_description": text}


def profile_dax_model(text: str) -> dict:
    """Wraps pasted DAX measures or semantic model schema."""
    return {"raw_model": text}


def summarize_for_prompt(profile: dict, input_type: str) -> str:
    """
    Converts any profile dict into a single compact text block
    ready to drop into the LLM prompt.

    input_type: "csv" | "excel" | "db" | "text" | "dax"
    """
    if input_type in ("csv", "excel", "db"):
        lines = [f"Rows: {profile['row_count']}", "Columns:"]
        for c in profile["columns"]:
            lines.append(
                f"- {c['name']} ({c['dtype']}, {c['null_pct']}% null, "
                f"{c['unique_count']} unique) e.g. {c['sample_values']}"
            )
        lines.append(f"Sample rows: {profile['sample_rows'][:3]}")
        return "\n".join(lines)

    elif input_type == "text":
        return profile["raw_description"]

    elif input_type == "dax":
        return profile["raw_model"]

    raise ValueError(f"Unknown input_type: {input_type}")
