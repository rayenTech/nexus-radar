# Nexus Radar

**Open-source research and technology intelligence platform**, powered by Flask and Python.

Nexus Radar collects scientific publication metadata and technology news, classifies each item into Cybersecurity, Artificial Intelligence, Next-Generation Networks (NGN) or General, removes duplicates, and displays the results in a Flask dashboard.

## Features in this starter version

- Flask application with a responsive Bootstrap dashboard.
- Research-paper collectors: arXiv, OpenAlex and Crossref.
- Technology-news collectors: configurable RSS/Atom feeds.
- Explainable keyword-based classification and relevance scoring.
- DOI/URL-based deduplication.
- Search, category filters, pagination, item details and a keyword-frequency trends page.
- SQLite for local development; PostgreSQL for deployment.
- GitHub Actions workflow that executes the collectors every two hours and writes to the shared PostgreSQL database.
- GitHub Actions schedule every two hours, plus a manual workflow trigger.
- Basic automated tests.

> Important: the two-hour schedule is a polling interval, not a guarantee that every source publishes new material every two hours. Some sources update less frequently, and scheduled GitHub Actions jobs can be delayed during busy periods.

---

# Part A — Run locally on Windows

## 1. Install prerequisites

Install:

- Python 3.11 or newer (Python 3.12 recommended).
- Git.
- Visual Studio Code (optional, but recommended).

During Python installation on Windows, enable **Add Python to PATH**.

Verify the installations in PowerShell:

```powershell
py --version
git --version
```

## 2. Extract and open the project

Extract `nexus-radar.zip`, then open PowerShell in the extracted folder:

```powershell
cd path\to\nexus-radar
```

The folder you open should contain `requirements.txt`, `wsgi.py`, `app/` and `collector/`.

## 3. Create a virtual environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for this terminal session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 4. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 5. Configure environment variables

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set a private secret key. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the result into `SECRET_KEY=`. The local version uses SQLite automatically, so you do not need to configure `DATABASE_URL` for the first run.

Optional values:

- `CONTACT_EMAIL`: contact address included in API request User-Agent headers where appropriate.
- `OPENALEX_API_KEY`: optional OpenAlex API key; the API can also be tested without one.
- `COLLECTION_LOOKBACK_DAYS`: how far back each collector looks (default: 7 days).
- `COLLECT_LIMIT`: maximum number of items requested per query/feed (default: 30).

Do not commit `.env` to GitHub. It is excluded by `.gitignore`.

## 6. Start the Flask website

```powershell
flask --app wsgi:app run --debug
```

Open this address in your browser:

```text
http://127.0.0.1:5000
```

The database is created automatically at `instance/nexus_radar.db` the first time the app starts.

## 7. Run the collectors once

Open a **second PowerShell window** in the project folder, activate the virtual environment again, then run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m collector.run
```

The first collection can take a few minutes because it queries several independent sources. Results are saved to the same local SQLite database used by Flask. Refresh the dashboard when the command finishes.

The collector prints a summary similar to:

```text
{'inserted': 42, 'skipped': 13, 'sources': {...}}
```

- `inserted`: new items saved.
- `skipped`: existing or invalid items ignored as duplicates/incomplete records.
- `sources`: source-by-source collection results.

If an external source is unavailable, its warning appears in the terminal. Other collectors continue.

## 8. Run tests

```powershell
pytest -q
```

The tests use an isolated in-memory SQLite database and do not call external APIs.

---

# Part B — Understand and customize the project

## 1. Main folders

```text
app/                    Flask application, routes, models, templates and CSS
collector/              arXiv, OpenAlex, Crossref and RSS collectors
.github/workflows/      tests and scheduled collection workflow
tests/                  automated tests
instance/                local SQLite database (created automatically)
```

## 2. Add or remove RSS sources

Edit `collector/sources.py` and find `RSS_FEEDS`:

```python
RSS_FEEDS = [
    {
        "name": "Example Security Blog",
        "url": "https://example.com/feed.xml",
        "category": "cybersecurity",
    },
]
```

Allowed categories are `cybersecurity`, `ai`, `ngn` and `general`. Use the actual RSS/Atom URL published by the source. Respect each publisher's terms and feed usage policies.

## 3. Change the scientific search coverage

In `collector/sources.py`, adjust:

- `ARXIV_CATEGORIES`
- `OPENALEX_QUERIES`
- `CROSSREF_QUERIES`

In `app/classification.py`, add domain keywords to `TAXONOMY` and high-priority terms to `PRIORITY_TERMS`.

The classifier is deliberately transparent and keyword-based in this first version. It does not use a trained AI model yet.

## 4. Add a new field or a database table

The main database model is `app/models.py`. This starter uses `db.create_all()` to create missing tables automatically. For a production system with changing schemas, add Flask-Migrate/Alembic migrations before changing existing columns.

---

# Part C — Deploy publicly

A Flask application is a server-side Python application. **GitHub Pages cannot run Flask**; GitHub hosts the source code and Actions schedule the collection, while a Python-capable host serves the web application.

This guide uses:

- GitHub for the public source repository and scheduled workflow.
- Render for the Flask web service.
- One PostgreSQL database with a connection string reachable from both Render and GitHub Actions (for example, Neon or Supabase).

SQLite is intended for local development, not for this hosted setup.

## 1. Create a PostgreSQL database

Create a PostgreSQL database with your chosen provider. Copy its connection string. It usually looks like:

```text
postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Keep the password private. The application converts the common `postgresql://`/`postgres://` schemes to the `psycopg` SQLAlchemy driver automatically.

## 2. Push the project to GitHub

Create an empty GitHub repository named `nexus-radar` (or another name). In PowerShell, from the project folder:

```powershell
git init
git add .
git commit -m "Initial Nexus Radar Flask application"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/nexus-radar.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. Make sure the repository is public if you want the project to be open source.

## 3. Deploy Flask on Render

1. Sign in to Render and choose **New → Web Service**.
2. Connect your GitHub account and select the `nexus-radar` repository.
3. Set the runtime to Python.
4. Set **Build Command** to:

   ```text
   pip install -r requirements.txt
   ```

5. Set **Start Command** to:

   ```text
   gunicorn --bind 0.0.0.0:$PORT wsgi:app
   ```

6. Add these environment variables in Render:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Your hosted PostgreSQL connection string |
   | `SECRET_KEY` | A long random secret generated locally |

7. Set the health-check path to `/health` if the host asks for one.
8. Deploy. Open your Render service URL and check that the dashboard loads.

The `Procfile` is also included, but use the explicit start command above if Render asks for one.

## 4. Configure GitHub Actions secrets

The workflow `.github/workflows/collect.yml` runs the Python collectors on a GitHub-hosted runner. The runner writes to the same PostgreSQL database used by Flask. This avoids keeping a long HTTP request open while the sources are queried.

In your GitHub repository:

1. Open **Settings → Secrets and variables → Actions**.
2. Choose **New repository secret**.
3. Add these secrets:

   | Secret name | Value |
   |---|---|
   | `DATABASE_URL` | The same PostgreSQL connection string configured in Render |
   | `OPENALEX_API_KEY` | Optional OpenAlex API key |
   | `CONTACT_EMAIL` | Optional contact email used in API request identification |

Use a database connection string that permits external connections from GitHub Actions. Do not use a provider's private/internal-only connection URL. Keep the URL private because it contains database credentials. Never put it in source code or a public README.

## 5. Test the scheduled collection manually

1. In GitHub, open **Actions**.
2. Select **Collect research and technology updates**.
3. Click **Run workflow**.
4. Open the workflow run and inspect its output.
5. Refresh the public dashboard after a successful run.

The schedule is:

```yaml
- cron: "23 */2 * * *"
```

This means minute 23 of every second hour, in UTC. GitHub scheduled workflows run from the default branch and may be delayed during busy periods. Keep the workflow file on `main` (or whatever your default branch is).

## 6. Test the health check

Open:

```text
https://YOUR-APP.onrender.com/health
```

Expected response:

```json
{"status":"ok","utc":"..."}
```

The `/health` endpoint confirms that the web service is responding. The collector itself runs as a separate scheduled GitHub Actions job; inspect its logs in the Actions tab if the dashboard is not receiving new items.

---

# Part D — Important limitations and next improvements

1. **Polling is not instant news delivery.** The workflow checks every two hours, but upstream sources decide when to publish or refresh their feeds. Some research sources publish in batches, so a two-hour polling schedule does not guarantee new papers every two hours.
2. **A preprint is not necessarily peer reviewed.** arXiv records should be labelled as preprints. Crossref/OpenAlex metadata does not prove that a paper has passed peer review either. Add explicit publication-status verification before presenting that label as fact.
3. **The current trend page is a frequency counter.** It counts keywords in the collected sample; it is not a statistical trend detector or citation-impact ranking.
4. **The current classifier is keyword-based.** It is explainable and easy to customize, but it may misclassify ambiguous titles. An embedding/LLM classifier can be added later.
5. **Only metadata and source-provided abstracts are stored.** The app links to the original publisher or repository and does not download or redistribute paywalled full-text papers.
6. **Check source terms and API policies.** Use polite request rates, identify the application where required, and comply with each API/feed's terms.
7. **Back up PostgreSQL.** A public research dashboard should not rely on a single unbacked-up database.

## Suggested next development milestones

- Add source-health monitoring and a collection-run history table.
- Store author profiles, publication venues and DOI metadata in normalized tables.
- Add a publication-status field (`preprint`, `journal article`, `conference paper`, `unknown`) based on verified source metadata.
- Add saved searches and email/Telegram digests.
- Add semantic search and AI-generated structured summaries with citations back to the original paper.
- Add user accounts only when personalized dashboards are needed.

## License

MIT. See `LICENSE`.
