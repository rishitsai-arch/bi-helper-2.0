"""
vanna_client.py
Wires up Vanna (open-source, self-hosted) to actually run SQL against your
live PostgreSQL/MySQL database and return real results — not just a plan.

Uses:
  - ChromaDB_VectorStore : free, local vector store for training data (no setup)
  - OpenAI_Chat          : Vanna's OpenAI-compatible chat class, pointed at
                            Groq's endpoint (Groq is OpenAI-compatible, so this
                            works with your existing free Groq key — no separate
                            Vanna/OpenAI key needed)

Install with:  pip install vanna chromadb openai
"""

from urllib.parse import urlparse

import streamlit as st
from openai import OpenAI
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat


class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """Combines a local ChromaDB vector store with a Groq-backed chat model."""

    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, client=config["client"], config=config)


@st.cache_resource
def get_vanna(groq_api_key: str, connection_string: str, db_type: str):
    """
    Builds and connects a Vanna instance.
    db_type: "postgres", "mysql", or "sqlite"
    connection_string:
        postgres/mysql -> SQLAlchemy-style string, e.g.
            postgresql://user:password@host:5432/dbname
            mysql+pymysql://user:password@host:3306/dbname
        sqlite -> local file path, e.g. "sample_sales.db"
    """
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
    vn = MyVanna(config={"client": client, "model": "llama-3.3-70b-versatile"})

    if db_type == "sqlite":
        vn.connect_to_sqlite(connection_string)
        return vn

    parsed = urlparse(connection_string)
    host = parsed.hostname
    port = parsed.port
    user = parsed.username
    password = parsed.password
    dbname = parsed.path.lstrip("/")

    if db_type == "postgres":
        vn.connect_to_postgres(
            host=host, dbname=dbname, user=user, password=password,
            port=port or 5432,
        )
    elif db_type == "mysql":
        vn.connect_to_mysql(
            host=host, dbname=dbname, user=user, password=password,
            port=port or 3306,
        )
    else:
        raise ValueError("db_type must be 'postgres', 'mysql', or 'sqlite'")

    return vn


def train_on_schema(vn, db_type: str = "postgres"):
    """
    One-time training step: reads the DB's own schema (table/column names
    and types) and feeds it to Vanna so it knows what it's querying.
    Safe to call every run — Vanna skips duplicate training data.
    """
    try:
        if db_type == "sqlite":
            df_schema = vn.run_sql(
                "SELECT name AS table_name, sql AS table_definition "
                "FROM sqlite_master WHERE type='table'"
            )
        else:
            df_schema = vn.run_sql(
                "SELECT table_name, column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
            )
        schema_text = df_schema.to_string(index=False)
        vn.train(documentation=f"Database schema:\n{schema_text}")
    except Exception as e:
        # Non-fatal — Vanna can still work with less training, just less accurately
        print(f"Schema training skipped: {e}")


def ask_vanna(vn, question: str):
    """
    Turns one natural-language question into SQL, runs it against the live
    database, and returns both the SQL and the resulting DataFrame.
    """
    sql = vn.generate_sql(question)
    df = vn.run_sql(sql)
    return sql, df
