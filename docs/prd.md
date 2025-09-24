Understood 👍 — here’s the **clean write-up** version of the documentation, no markdown files or formatting, just the plain text content you’d put inside README, LICENSE, and supporting files.

---

**Project Name**
OpenQuest

**Overview**
OpenQuest is a zero-configuration real-time data aggregation tool designed for traders, analysts, and developers who use OpenAlgo. It connects directly to OpenAlgo via REST and WebSocket, streams tick-level data for MCX futures, and stores it inside QuestDB. This enables high-performance time-series storage, visualization, and future backtesting.

The application is built using Flask, TailwindCSS, and DaisyUI with a Supabase green and black theme. All configuration is handled inside the web UI—no `.env` files or CLI arguments. Users only need to provide their OpenAlgo API key and connection URLs.

**Key Features**

* Zero-config UI setup: configure OpenAlgo API key and host URLs directly in the dashboard.
* Real-time ingestion of LTP, Quote, and Depth streams.
* Automatic QuestDB schema creation for MCX futures symbols.
* Aggregates all MCX futures symbols listed in the reference file.
* Interactive dashboard with live metrics such as tick rate, spreads, imbalance, and last update per symbol.
* Modern UI theme using Supabase green and black.

**Architecture**

* Flask application serving UI with Jinja templates.
* TailwindCSS and DaisyUI for styling (via CDN, no build chain).
* WebSocket client to OpenAlgo for LTP, Quote, and Depth streams.
* QuestDB for storage of high-frequency time-series ticks.
* Aggregator layer subscribes to all MCX futures symbols and continuously writes data to QuestDB tables.

**QuestDB Schema**

* ticks\_ltp: timestamp, symbol, ltp.
* ticks\_quote: timestamp, symbol, bid, ask, spread, volume, open interest.
* ticks\_depth: timestamp, symbol, orderbook level, bid, ask, quantities.

**Quick Start**
Prerequisites:

* Python 3.11+
* QuestDB running locally at [http://127.0.0.1:9000](http://127.0.0.1:9000)
* OpenAlgo running locally at [http://127.0.0.1:5000](http://127.0.0.1:5000) (REST) and ws\://127.0.0.1:8765 (WebSocket)

Steps:

1. Clone the repository.
2. Install dependencies with pip.
3. Run `python run.py`.
4. Open `http://127.0.0.1:5000` in the browser to access OpenQuest.

In the dashboard, configure your API key and OpenAlgo connection URLs. Enable or disable streams (LTP, Quote, Depth) as needed.

**Roadmap**

* Add logging and monitoring.
* Implement role-based access and security.
* Provide REST API endpoints for external integrations.
* Containerized deployment with Docker.
* Extended support for Prometheus metrics.

**License**
This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). You are free to use, modify, and distribute the software, provided that modifications and derivative works are also open-sourced under the same license when distributed.

**.gitignore Defaults**
Ignore Python bytecode, virtual environments, SQLite databases, cache folders, and OS-specific files. Typical entries include:

* **pycache**/
* \*.pyc, \*.pyo, \*.pyd
* venv/
* .DS\_Store
* \*.db, \*.sqlite3
* instance/
* .pytest\_cache/
* .mypy\_cache/

**Requirements**
Minimal Python dependencies: (use always the latest library)

* Flask
* psycopg2-binary
* websockets
* aiohttp
* black
* pytest

