# Kibble Compare

A free-to-run PWA that scrapes Australian pet food retailers, lets you
search and compare prices (including per-kg/per-L unit pricing), and
flags big price drops or rises between scrapes.

## How it's free

- **Scraper**: runs on GitHub Actions' free tier (scheduled cron, no server).
- **Data**: static JSON files committed to the repo — no database needed.
- **Frontend**: static PWA, deploy free on GitHub Pages or Cloudflare Pages.
- **Hosting cost: $0**, as long as you stay within GitHub's free Actions minutes
  (2,000 min/month on a free account — a daily scrape of a handful of stores
  uses a tiny fraction of that).

## Project layout

```
scraper/
  adapters/
    base.py               shared schema + unit-price math
    shopify_adapter.py     generic adapter — works for any Shopify store
    coles_adapter.py        stub — needs live endpoint capture (see file)
    woolworths_adapter.py   stub — needs live endpoint capture (see file)
  stores_config.json       which stores to scrape, and which adapter to use
  scrape_all.py             orchestrator — run this to scrape everything
frontend/
  index.html / style.css / app.js    the PWA itself
  manifest.json / sw.js               PWA install + offline shell caching
  data/                                scraper output lives here (committed by CI)
.github/workflows/scrape.yml           daily scheduled scrape job
```

## Before you rely on any store, confirm its platform

I could not directly test these endpoints from this environment (no
network access to Australian retail sites), so `stores_config.json` marks
most stores as `"*_unconfirmed"` — plausible based on public signals, but
not verified live. Confirm each one for real before trusting its output.

**Shopify stores** (`shopify_unconfirmed`):
```bash
curl -s "https://www.petstock.com.au/products.json?limit=1" | head -c 300
```
JSON with a `"products"` array → it's Shopify, flip the config value to
`"shopify"`. 404 or HTML → not Shopify (or the feed is disabled), needs a
custom adapter.

**Magento stores** (`magento_unconfirmed` — currently just Petbarn):
```bash
curl -s -X POST https://www.petbarn.com.au/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ products(search:\"dog food\", pageSize:1) { items { name } } }"}'
```
JSON with product data → flip to `"magento"`. Error or 404 → GraphQL is
likely disabled publicly, needs a custom adapter instead.

Do this for each store once, and re-check occasionally — retailers do
migrate platforms.

## Store coverage

| Store | Platform (as configured) | Status |
|---|---|---|
| PETstock, Budget Pet Products, VetSupply, My Pet Warehouse, RSPCA World for Pets, Swaggle, Petz Park, Pet Chemist, The Vet Shed, PetPost, PetO | Shopify (unconfirmed) | enabled, needs live confirmation |
| Petbarn | Magento (unconfirmed) | enabled, needs live confirmation |
| Pet Circle | commercetools + custom BFF | disabled — needs a bespoke adapter, biggest catalogue, build last |
| Coles, Woolworths | custom internal APIs | disabled — needs live endpoint capture, pet-food category only |

## Running the scraper locally

```bash
cd scraper
pip install -r requirements.txt
python scrape_all.py
```

This writes `frontend/data/latest.json`, a dated snapshot under
`frontend/data/history/`, and `frontend/data/price_changes.json`.

## Enabling Pet Circle

See [`docs/pet-circle-capture-guide.md`](docs/pet-circle-capture-guide.md)
for a step-by-step DevTools walkthrough to capture their real search
request shape — there's no public feed to fall back on here, so this one
has to be captured live from a browser rather than guessed at.

## Enabling Coles / Woolworths

These are deliberately **disabled by default** in `stores_config.json`.
Both `coles_adapter.py` and `woolworths_adapter.py` are skeletons, not
working scrapers — the request shape (headers, session cookies, exact
endpoint) needs to be captured fresh from your own browser's DevTools
Network tab, since publishing an exact payload here would go stale
immediately. Once you've filled that in:

- keep them scoped to the pet-food category only (small slice of their
  catalogue = low request volume = lower detection risk)
- run them less often than the Shopify stores (e.g. weekly, not daily)
  until you've watched them behave reliably over a few runs
- expect occasional breakage — this is the highest-maintenance part of
  the project by nature, not a bug in the adapter

## Deploying the frontend (GitHub Pages, free)

1. Push this repo to GitHub.
2. Repo Settings → Pages → Deploy from branch → select the branch and
   `/frontend` folder as the source.
3. Your app is live at `https://<username>.github.io/<repo>/`.

The scheduled workflow keeps `frontend/data/*.json` fresh automatically;
Pages serves whatever is currently committed.

## Icons

`frontend/manifest.json` references `icons/icon-192.png` and
`icons/icon-512.png`, which aren't included — drop in your own square PNGs
at those sizes (or generate them from a logo) before the "Add to Home
Screen" install prompt will show a proper icon.

## Legal note

Coles and Woolworths' terms technically prohibit scraping, though
low-volume personal price tracking is a well-trodden grey area (this is
the same space apps like Frugl and various open-source scrapers operate
in). Keep request rates low, cache aggressively, and treat any
block/cease-and-desist as a signal to back off that store rather than
route around it.

## Feature ideas not yet built

- Shopping list mode: add several items, see which single store wins overall
- Own-brand vs branded equivalent finder
- Push notifications on watchlist price drops (needs a notification
  service — the only piece of this project that isn't fully free at scale)
- Historical "was this ever actually cheaper" indicator per product
