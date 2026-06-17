# ☁️ Cloud Infrastructure FinOps Portal

An automated, 3-tier enterprise analytics solution built to parse, process, and visualize corporate cloud resource costs. This portal integrates a local SQL database with a dynamic web UI to provide instant resource cost optimizations.

## 🛠️ Tech Stack & Tooling
- **Frontend & Dashboard:** Streamlit, Plotly Express, Pandas
- **Database Engine:** Microsoft SQL Server (SSMS)
- **Database Driver:** Python `pyodbc`
- **Version Control:** Git & GitHub (Structured via Feature Branching)

## 🏗️ System Architecture
1. **Data Layer (`sample.csv`):** Contains server metrics, CPU usage logs, and financial spend details.
2. **Backend Storage Layer (`SQL Server`):** Uses a `MERGE` (Upsert) script to dynamically insert or update unique server configurations without database duplication.
3. **Frontend Application Layer (`Streamlit`):** Automatically reloads data, provides metric KPI badges (Spend, Savings, Waste), and features active database row removal tools.

## 🌿 Repository Branching Structure
This project follows professional engineering standards with dedicated timelines:
- `main`: Safe, production-ready release.
- `feature-pipeline`: Dedicated development branch for SQL schema, pyodbc integrations, and ETL loaders.
- `feature-ui`: Dedicated branch for frontend interactivity, Plotly charts, and Streamlit session states.
