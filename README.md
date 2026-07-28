# BI Report AI

A Streamlit app that takes your data (CSV/Excel, database, plain text
description, or existing DAX/model) and generates:
1. A suggested Power BI report structure (pages, KPIs, visuals, filters)
2. DAX measures with formulas
3. A step-by-step build guide for Power BI Desktop

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — run this |
| `data_parser.py` | Turns any input type into a text summary |
| `llm_client.py` | Calls Groq or Gemini's free-tier API |
| `prompts.py` | The prompt template — edit this to tune output quality |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for API key env vars (optional, key is entered in-app by default) |

## Where to put your API key

Two ways to give the app your key — no code editing needed either way:

**Option 1 — paste it each time:** just type it into the sidebar "API Key"
box when the app is running. Nothing is saved.

**Option 2 — auto-load it (recommended if you don't want to re-paste it
every session):**

- **Running locally:** copy `.env.example` to a new file named `.env` in
  the same folder, and fill in your real key:
  ```
  GROQ_API_KEY=your_actual_key_here
  GEMINI_API_KEY=your_actual_key_here
  ```
  The app reads this automatically on startup and pre-fills the sidebar box.
  `.env` should **never** be committed to GitHub — add it to `.gitignore`.

- **Deployed on Streamlit Community Cloud:** go to your app → Settings →
  Secrets, and add:
  ```toml
  GROQ_API_KEY = "your_actual_key_here"
  GEMINI_API_KEY = "your_actual_key_here"
  ```
  The app checks `st.secrets` first automatically — same effect, no `.env`
  file needed on the server.

Either way, the sidebar box still shows the key and lets you override it
manually any time — auto-loading just saves you from re-typing it.

## Getting a free API key

- **Groq** (fast, open-source models, 1,000 requests/day free): https://console.groq.com
- **Gemini** (stronger reasoning, 1,500 requests/day free): https://aistudio.google.com/apikey

Gemini is set as the default provider since it holds structure better across
the long, multi-section output this app generates. Switch the dropdown to
Groq any time for faster (but slightly less structured) responses.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

## Deploy — Option A: Streamlit Community Cloud (free, easiest)

1. Push this folder to a GitHub repo.
2. Go to https://share.streamlit.io → "New app" → point it at your repo and `app.py`.
3. Deploys automatically. Users enter their own API key in the sidebar
   (or you can set one in Settings → Secrets and read it with `st.secrets`).

## Deploy — Option B: Render

1. Push this folder to a GitHub repo.
2. On Render: New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. Add any env vars you need under the Render dashboard's Environment tab.

## Database connections

The "Database" input type uses SQLAlchemy connection strings, e.g.:

```
postgresql://user:password@host:5432/dbname
mysql+pymysql://user:password@host:3306/dbname
mssql+pyodbc://user:password@host/dbname?driver=ODBC+Driver+17+for+SQL+Server
```

`psycopg2-binary` is included for Postgres out of the box. For MySQL or SQL
Server, add `pymysql` or `pyodbc` to `requirements.txt`.

## Notes / next steps

- Prompt quality lives entirely in `prompts.py` — tweak the section
  instructions there if outputs are too generic or too long.
- To add a Chrome extension front-end later, this same `llm_client.py` +
  `prompts.py` logic can sit behind a small API endpoint (e.g. FastAPI)
  that the extension calls instead of Streamlit.

## Vanna integration (ask your own questions, get real answers)

After the report plan generates, if you loaded data via a live database
connection (Postgres, MySQL, or the sample SQLite file), an "Ask your own
questions" box appears. Type any business question in plain English —
Vanna generates the SQL, runs it against your real database, and shows the
actual result table plus a chart (when the data shape supports one).

Every question you ask is kept in a running history. Once you've asked at
least one, a "Generate Full Report" button appears — this bundles the
report plan (structure, DAX, build guide) together with every question
you've asked and its real results into one downloadable markdown file.

**Important:**
- This only appears when you used the "Database" input type and loaded
  data from a live connection (not CSV/text/DAX inputs — Vanna needs a
  real database to query against).
- It currently uses your **Groq key** specifically (Groq is OpenAI-compatible,
  so Vanna's OpenAI integration works with it directly, at no extra cost).
  Switch the sidebar provider to Groq before running this step.
- Vanna's original open-source project was archived in March 2026. `pip
  install vanna` still works and is what this app uses, but it's no longer
  actively maintained by the original team — if you hit installation issues,
  check github.com/vanna-ai/vanna for the current status.
- On first run per session, Vanna trains itself on your database's schema
  (table/column names) automatically — this can take a few seconds.
- `vanna_client.py` is where all of this logic lives if you want to adjust
  the model, add manual training examples (DDL, example queries) for
  better accuracy, or point it at a different LLM.
