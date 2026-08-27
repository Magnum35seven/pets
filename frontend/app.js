const DATA_URL = "data/latest.json";
const CHANGES_URL = "data/price_changes.json";

let allProducts = [];

// ---- Tab switching --------------------------------------------------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.remove("is-active");
      b.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("is-active"));

    btn.classList.add("is-active");
    btn.setAttribute("aria-selected", "true");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("is-active");
  });
});

// ---- Data loading -----------------------------------------------------
async function loadData() {
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    const json = await res.json();
    allProducts = json.products || [];
    document.getElementById("last-updated").textContent =
      `Prices last scraped: ${new Date(json.scraped_at).toLocaleString("en-AU")} · ${json.product_count} products tracked`;
  } catch (err) {
    document.getElementById("last-updated").textContent =
      "Couldn't load price data yet — run the scraper to generate data/latest.json";
  }

  try {
    const res = await fetch(CHANGES_URL, { cache: "no-store" });
    const json = await res.json();
    renderMovers(json.changes || []);
  } catch (err) {
    // no price_changes.json yet (first ever run) — that's fine
  }
}

// ---- Search / render --------------------------------------------------
const searchInput = document.getElementById("search-input");
const sortSelect = document.getElementById("sort-select");
const resultsList = document.getElementById("results-list");
const resultMeta = document.getElementById("result-meta");
const emptyState = document.getElementById("empty-state");

function matches(product, term) {
  if (!term) return false;
  const haystack = `${product.title} ${product.brand || ""}`.toLowerCase();
  return term
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

function sortProducts(products, mode) {
  const withValue = (p, field) => (p[field] === null || p[field] === undefined ? Infinity : p[field]);
  if (mode === "price") {
    return [...products].sort((a, b) => withValue(a, "price") - withValue(b, "price"));
  }
  if (mode === "discount") {
    const pct = (p) => (p.compare_at_price ? (p.compare_at_price - p.price) / p.compare_at_price : 0);
    return [...products].sort((a, b) => pct(b) - pct(a));
  }
  // default: unit price
  return [...products].sort((a, b) => withValue(a, "unit_price") - withValue(b, "unit_price"));
}

function formatMoney(n) {
  return n === null || n === undefined ? "—" : `$${n.toFixed(2)}`;
}

function renderResults() {
  const term = searchInput.value.trim();
  resultsList.innerHTML = "";

  if (!term) {
    resultMeta.textContent = "";
    emptyState.hidden = true;
    return;
  }

  const matched = sortProducts(allProducts.filter((p) => matches(p, term)), sortSelect.value);
  resultMeta.textContent = matched.length
    ? `${matched.length} result(s) across ${new Set(matched.map((p) => p.store)).size} store(s)`
    : "";
  emptyState.hidden = matched.length > 0;

  const cheapestUnitPrice = matched.reduce((min, p) => {
    if (p.unit_price === null || p.unit_price === undefined) return min;
    return min === null ? p.unit_price : Math.min(min, p.unit_price);
  }, null);

  matched.forEach((p) => {
    const li = document.createElement("li");
    li.className = "docket-item";
    if (cheapestUnitPrice !== null && p.unit_price === cheapestUnitPrice) {
      li.classList.add("is-cheapest");
    }

    const unitLabel = p.unit_price_basis ? `/${p.unit_price_basis}` : "";

    li.innerHTML = `
      <a class="docket-title" href="${p.url}" target="_blank" rel="noopener">${p.title}</a>
      <div class="docket-store">${p.store_name}${p.brand ? " · " + p.brand : ""}${p.in_stock === false ? " · OUT OF STOCK" : ""}</div>
      <div class="docket-price">${formatMoney(p.price)}${p.compare_at_price ? `<span class="was">was ${formatMoney(p.compare_at_price)}</span>` : ""}</div>
      <div class="docket-unitprice">${p.unit_price ? formatMoney(p.unit_price) + unitLabel : ""}</div>
    `;
    resultsList.appendChild(li);
  });
}

searchInput.addEventListener("input", renderResults);
sortSelect.addEventListener("change", renderResults);

// ---- Price movers tab ---------------------------------------------
function renderMovers(changes) {
  const list = document.getElementById("movers-list");
  const empty = document.getElementById("movers-empty");
  list.innerHTML = "";
  empty.hidden = changes.length > 0;

  changes.forEach((c) => {
    const li = document.createElement("li");
    li.className = "docket-item";
    const badgeClass = c.direction === "drop" ? "drop" : "rise";
    const arrow = c.direction === "drop" ? "▼" : "▲";

    li.innerHTML = `
      <a class="docket-title" href="${c.url}" target="_blank" rel="noopener">${c.title}</a>
      <div class="docket-store">${c.store_name}</div>
      <div class="docket-price">${formatMoney(c.new_price)}<span class="was">was ${formatMoney(c.old_price)}</span></div>
      <div class="docket-unitprice"><span class="pct-badge ${badgeClass}">${arrow} ${Math.abs(c.pct_change)}%</span></div>
    `;
    list.appendChild(li);
  });
}

// ---- PWA service worker ---------------------------------------------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
}

loadData();
