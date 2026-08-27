// ---- Configuration & Data Source ------------------------------------
const DATA_URL = "latest.json";
const CHANGES_URL = "price_changes.json";

let allProducts = [];
let currentCategory = "all";

// Category Tagging Keywords
const TREAT_KEYWORDS = ['treat', 'bone', 'hoof', 'hooves', 'tendon', 'jerky', 'chew', 'stick', 'trotter', 'ear', 'churu', 'mousse', 'bites'];
const ACCESSORY_KEYWORDS = ['toy', 'pouch', 'dispenser', 'mat', 'ball', 'cuttlebone', 'cleaner', 'treatment'];

function getItemCategory(title) {
  const lowerTitle = title.toLowerCase();
  if (ACCESSORY_KEYWORDS.some(kw => lowerTitle.includes(kw))) return 'accessory';
  if (TREAT_KEYWORDS.some(kw => lowerTitle.includes(kw))) return 'treat';
  return 'food';
}

// Title normalizer to group cross-store duplicates
function getNormalizedKey(title) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .trim();
}

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
    allProducts = json.products || json || [];
    
    const productCount = Array.isArray(json) ? json.length : (json.product_count || allProducts.length);
    const scrapedAt = json.scraped_at ? new Date(json.scraped_at).toLocaleString("en-AU") : "Recently";

    document.getElementById("last-updated").textContent =
      `Prices last scraped: ${scrapedAt} · ${productCount} products tracked`;
  } catch (err) {
    document.getElementById("last-updated").textContent =
      "Couldn't load price data yet — run the scraper to generate data/latest.json";
  }

  try {
    const res = await fetch(CHANGES_URL, { cache: "no-store" });
    const json = await res.json();
    renderMovers(json.changes || []);
  } catch (err) {
    // no price_changes.json yet
  }
}

// ---- Search / render --------------------------------------------------
const searchInput = document.getElementById("search-input");
const sortSelect = document.getElementById("sort-select");
const groupToggle = document.getElementById("group-toggle");
const resultsList = document.getElementById("results-list");
const resultMeta = document.getElementById("result-meta");
const emptyState = document.getElementById("empty-state");

function matches(product, term) {
  if (!term) return true;
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
  return [...products].sort((a, b) => withValue(a, "unit_price") - withValue(b, "unit_price"));
}

function formatMoney(n) {
  return n === null || n === undefined ? "—" : `$${n.toFixed(2)}`;
}

function renderResults() {
  const term = searchInput.value.trim();
  resultsList.innerHTML = "";

  const filtered = allProducts.filter((p) => {
    const matchesTerm = matches(p, term);
    const category = getItemCategory(p.title);
    const matchesCategory = (currentCategory === "all") || (category === currentCategory);
    return matchesTerm && matchesCategory;
  });

  if (filtered.length === 0) {
    resultMeta.textContent = "";
    emptyState.hidden = false;
    return;
  }

  emptyState.hidden = true;

  // Render grouped view if toggle is checked
  if (groupToggle && groupToggle.checked) {
    const groups = {};
    filtered.forEach(p => {
      const key = getNormalizedKey(p.title);
      if (!groups[key]) groups[key] = [];
      groups[key].push(p);
    });

    const groupedArray = Object.values(groups);
    resultMeta.textContent = `${groupedArray.length} product(s) found across stores`;

    groupedArray.forEach(items => {
      items.sort((a, b) => (a.price || Infinity) - (b.price || Infinity));
      const mainItem = items[0];

      const card = document.createElement("div");
      card.className = "product-card";

      let storeListHtml = items.map((item, idx) => {
        const isCheapest = idx === 0 && items.length > 1;
        const cheapestBadge = isCheapest ? ' <span style="color:#00e676; font-weight:bold; font-size:12px;">★ CHEAPEST</span>' : '';
        return `
          <div style="display:flex; justify-content:space-between; margin-top:6px; padding-top:6px; border-top:1px solid #333;">
            <span><a href="${item.url}" target="_blank" rel="noopener">${item.store || item.store_id || "Store"}</a>${cheapestBadge}</span>
            <span><strong>${formatMoney(item.price)}</strong> ${item.unit_price ? `($${item.unit_price.toFixed(2)}/${item.unit_unit || "kg"})` : ""}</span>
          </div>
        `;
      }).join("");

      card.innerHTML = `
        <div class="product-info" style="width:100%;">
          <div class="product-title" style="font-weight:bold;">${mainItem.title}</div>
          <div class="product-store">${mainItem.brand ? "Brand: " + mainItem.brand + " · " : ""}${items.length} store offer(s)</div>
          ${storeListHtml}
        </div>
      `;
      resultsList.appendChild(card);
    });
    return;
  }

  // Regular itemized list view
  const matched = sortProducts(filtered, sortSelect.value);
  const storesCount = new Set(matched.map((p) => p.store_id || p.store)).size;
  resultMeta.textContent = `${matched.length} result(s) across ${storesCount} store(s)`;

  matched.forEach((p) => {
    const card = document.createElement("div");
    card.className = "product-card";

    const unitStr = p.unit_price ? `$${p.unit_price.toFixed(2)}/${p.unit_unit || "kg"}` : "No unit price";
    const outOfStockTag = p.in_stock === false ? ' · <span class="badge out-of-stock">OUT OF STOCK</span>' : "";
    const wasPrice = p.compare_at_price ? ` <span class="was-price">was $${p.compare_at_price.toFixed(2)}</span>` : "";

    card.innerHTML = `
      <div class="product-info">
        <a class="product-title" href="${p.url}" target="_blank" rel="noopener">${p.title}</a>
        <div class="product-store">${p.store || p.store_id || ""} ${p.brand ? "· " + p.brand : ""}${outOfStockTag}</div>
      </div>
      <div class="product-price">
        <div class="price-main">${formatMoney(p.price)}${wasPrice}</div>
        <div class="price-unit">${unitStr}</div>
      </div>
    `;
    resultsList.appendChild(card);
  });
}

// Category button listeners
document.querySelectorAll(".cat-btn").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    document.querySelectorAll(".cat-btn").forEach((b) => b.classList.remove("active"));
    e.target.classList.add("active");
    currentCategory = e.target.dataset.category;
    renderResults();
  });
});

searchInput.addEventListener("input", renderResults);
sortSelect.addEventListener("change", renderResults);
if (groupToggle) groupToggle.addEventListener("change", renderResults);

// ---- Price Movers ---------------------------------------------------
function renderMovers(changes) {
  const dropsList = document.getElementById("drops-list");
  const risesList = document.getElementById("rises-list");

  const drops = changes.filter((c) => c.delta < 0);
  const rises = changes.filter((c) => c.delta > 0);

  dropsList.innerHTML = drops.length ? "" : "<li>No price drops detected in the last scrape.</li>";
  risesList.innerHTML = rises.length ? "" : "<li>No price rises detected in the last scrape.</li>";

  drops.forEach((c) => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${c.url}" target="_blank">${c.title}</a>: dropped by $${Math.abs(c.delta).toFixed(2)} to $${c.new_price.toFixed(2)}`;
    dropsList.appendChild(li);
  });

  rises.forEach((c) => {
    const li = document.createElement("li");
    li.innerHTML = `<a href="${c.url}" target="_blank">${c.title}</a>: rose by $${c.delta.toFixed(2)} to $${c.new_price.toFixed(2)}`;
    risesList.appendChild(li);
  });
}

// Initial load
loadData();
