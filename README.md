# Pet Products

A free-to-run PWA that scrapes Australian pet food and treat retailers, lets you search and compare prices (including per-kg/per-L unit pricing), and flags price drops or rises between scrapes.

## How it's free
- **Scraper**: runs on GitHub Actions' free tier (scheduled cron, no server).
- **Data**: static JSON files committed to the repo — no database needed.
- **Frontend**: static PWA, deploy free on GitHub Pages or Cloudflare Pages.
- **Hosting cost: $0**, as long as you stay within GitHub's free Actions minutes (2,000 min/month on a free account).

## Project layout
scraper/
adapters/
base.py               shared schema + unit-price math
shopify_adapter.py    generic adapter — works for any Shopify store
coles_adapter.py      stub — needs live endpoint capture
woolworths_adapter.py stub — needs live endpoint capture
stores_config.json      which stores to scrape, and which adapter to use
scrape_all.py          orchestrator — run this to scrape everything
frontend/
index.html / style.css / app.js    the PWA itself
manifest.json / sw.js              PWA install + offline shell caching
latest.json                        scraper output lives here
.github/workflows/scrape.yml         weekly scheduled scrape job


## Running the scraper locally
```bash
cd scraper
pip install -r requirements.txt
python scrape_all.py
This writes frontend/latest.json with updated pricing and 3-scrape historical tracking.

Deploying the frontend (GitHub Pages, free)
Push this repo to GitHub.

Repo Settings → Pages → Deploy from branch → select the branch and /frontend folder as the source.

Your app is live at https://<username>.github.io/<repo>/.
