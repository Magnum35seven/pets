# Capturing Pet Circle's search API (DevTools walkthrough)

Pet Circle runs on commercetools with a custom backend-for-frontend layer,
so there's no documented public feed like Shopify's `/products.json` or
Magento's `/graphql`. The storefront still has to call *something* to
render search results, though — this walkthrough finds that call so you
can replicate it in Python.

## 1. Open the site with a clean network log

1. Go to `https://www.petcircle.com.au/` in Chrome or Firefox.
2. Open DevTools (`F12` or `Ctrl+Shift+I` / `Cmd+Option+I`).
3. Click the **Network** tab.
4. Filter to **Fetch/XHR** only (there's a filter row of pills — click
   "Fetch/XHR", or type `Fetch/XHR` in the filter box). This hides images,
   CSS, and ad/analytics noise so you're only looking at real data calls.
5. Tick **Preserve log** — otherwise navigating clears everything you
   just captured.

## 2. Trigger the search request

1. Click the search box on the site and type something specific and
   pet-food-shaped, e.g. `royal canin dog food`.
2. Press Enter, or wait for live-search suggestions to appear.
3. Watch the Network panel — one or more new requests will appear as the
   results render. You're looking for one whose **response** (not just
   the request) contains product data: names, prices, SKUs.

## 3. Identify the right request

Click through the requests that just appeared and check each one's
**Response** or **Preview** tab. You're looking for JSON containing
recognisable fields like `name`, `price`, `sku`, `slug`, or similar.
Ignore requests to analytics/tracking domains (Segment, Google Tag
Manager, etc.) — you want the one hosted on `petcircle.com.au` itself or
a first-party API subdomain.

Once you've found it, click the **Headers** tab for that request and
note down:

- **Request URL** — the full endpoint, e.g. `https://www.petcircle.com.au/api/search` (exact path varies)
- **Request Method** — `GET` or `POST`
- **Request Payload / Query String Parameters** — the exact body or query params sent
- **Content-Type** header
- Any **Authorization**, **X-Api-Key**, or custom `X-*` headers — commercetools-backed sites often need a client token here
- Whether a **Cookie** header is present — if so, the request may need a warmed-up session (visit the homepage first, like the Woolworths/Coles adapters already do)

Right-click the request → **Copy** → **Copy as cURL** is the fastest way
to get an exact, pasteable version of everything above in one go.

## 4. Check for a GraphQL shape

If the Request Payload looks like a `query { ... }` string rather than
plain params, it's GraphQL — copy the full query and note the
**operation name** (e.g. `SearchProducts`) and the variable names it
expects (e.g. `searchTerm`, `page`, `pageSize`). This tells you the exact
shape to send from Python.

## 5. Translate into the adapter

Once you have the cURL command, converting it to Python is close to
mechanical — `requests` mirrors cURL's shape directly:

- cURL `-H "Header: value"` → `session.headers.update({"Header": "value"})`
- cURL `-d '{...}'` with `Content-Type: application/json` → `session.post(url, json={...})`
- cURL cookies from a prior request → `session.get(homepage_url)` first, same session object, so cookies carry over automatically

Drop the translated request into a new `scraper/adapters/petcircle_adapter.py`,
following the same shape as `coles_adapter.py` / `woolworths_adapter.py` —
same normalised output schema (see `adapters/base.py`), same
`compute_unit_price()` call for consistency with every other store.

## 6. Sanity-check before wiring it into the schedule

Run the new adapter standalone against a couple of different search terms
first (not through `scrape_all.py` yet) and print the raw output — confirm
prices/titles look right before it goes into the daily scrape and starts
being trusted by the price-diffing logic.

## Things that commonly go wrong

- **Response looks empty/blocked** on the second identical request — the
  session cookie may be single-use or short-lived; re-warm it (fresh GET
  to the homepage) before each search rather than reusing one session
  across a whole scrape run.
- **A `X-Correlation-Id` or similar per-request token** appears in the
  payload — this is usually generated client-side per page load and
  often doesn't need to be valid, but if requests fail without it, a
  random UUID in that field is normally enough to satisfy the check.
- **Pagination shape isn't obvious** — scroll the results page to trigger
  infinite-scroll loading, or click "next page" if there's pagination UI,
  and watch for a *second* request with a `page`/`offset`/`cursor`
  parameter that changed — that's your pagination variable.
