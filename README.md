# Smart PIM — WooCommerce Product Information Manager

A hackathon MVP to manage a product catalog, validate product attributes, review catalog-quality findings, and synchronize products with WooCommerce. It runs locally with sample data and does not require store credentials for the demo workflow.

## Features

- Product dashboard with catalog stats, search, and recent activity.
- Create, edit, and delete products with required-field, numeric, and unique-SKU validation.
- Tool-assisted **Catalog Quality Agent** with a visible plan, validation tools, severity-ranked findings, and recommendations.
- WooCommerce REST API v3 create/update-by-SKU path when credentials are configured.
- Explicit demo-sync behavior when live credentials are absent.
- Downloadable catalog export as spreadsheet-friendly CSV.
- SQLite persistence and automated tests.

> Agent transparency: this MVP uses deterministic tool-based checks, not an LLM. It works offline and does not automatically change product data.

## Requirements

- Python 3.10 or newer
- `pip`
- Optional WooCommerce store with REST API credentials for live sync

## Run locally (macOS/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The database is created automatically and seeded with five sample products on first run. Stop the server with `Ctrl+C`.

## Run tests

```bash
pytest -q
```

## Optional live WooCommerce sync

Set environment variables in the same terminal before starting the application:

```bash
export WC_STORE_URL="https://your-real-store.example"
export WC_CONSUMER_KEY="ck_your_key"
export WC_CONSUMER_SECRET="cs_your_secret"
python app.py
```

Generate credentials inside your WooCommerce admin under **WooCommerce → Settings → Advanced → REST API** and grant only the required permissions. Do not commit credentials or paste them into frontend JavaScript. Use a test/staging store first. If credentials are not configured, the interface records a clearly labeled demo sync; no remote store is modified.

## API/health check

Open <http://127.0.0.1:5000/health>. It returns a small JSON health response and indicates whether a store URL is configured.

## Project layout

```text
smart-pim-integration/
├── app.py
├── services/
│   ├── database.py
│   ├── catalog_agent.py
│   └── woocommerce.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── product_form.html
│   └── quality.html
├── static/style.css
├── tests/test_app.py
├── docs/architecture.md
├── .env.example
├── .gitignore
├── requirements.txt
└── PROJECT_PLAN.md
```

## Known limitations / production hardening

This MVP is designed for a short hackathon demo. It does not include authentication, role-based permissions, CSRF protection, image uploads, variation products, pagination, or background sync jobs. The deterministic catalog quality tools should not be described as an LLM agent. The live integration sends product name, SKU, price, description, and stock; category creation/mapping and remote category IDs are not implemented yet. Test against a disposable or staging store first.

## Hackathon demo flow

1. Open Overview and point out the sample catalog, inventory metrics, search, and activity list.
2. Export the catalog CSV to demonstrate data portability.
3. Create a product and show the required-field / duplicate-SKU validation.
4. Open Catalog Quality Agent and explain its three tools and human-review recommendations.
5. Click Sync on a product. In demo mode, call out the explicit `Demo synced` state; with valid credentials, demonstrate the actual remote create/update.
6. Run `pytest -q` and show the results.

## Submission assets

- Planning video: recorded separately during Phase 1.
- Closing video: record the real app and the final tests; do not claim demo sync modified a live store.
- Repository: publish this project to GitHub and submit the repository URL through the organizer's form.
