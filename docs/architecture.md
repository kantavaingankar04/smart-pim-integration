# Architecture

## Request flow

`Browser (HTML/CSS)` → `Flask routes` → `service layer` → `SQLite`

The optional WooCommerce path is `Flask sync route` → `services/woocommerce.py` → WooCommerce REST API v3. The catalog-quality route calls `services/catalog_agent.py`, which runs three deterministic validation tools and returns findings for human review.

## Main modules

- `app.py`: page routes, form validation, sync orchestration, health endpoint, user feedback.
- `services/database.py`: SQLite schema, seed catalog, CRUD and activity logging.
- `services/catalog_agent.py`: required-field checks, numeric validation, duplicate-SKU detection, prioritized recommendations.
- `services/woocommerce.py`: create-or-update by SKU when live credentials are configured; explicit demo fallback otherwise.
- `templates/`: dashboard, product form, and catalog-agent report.
- `tests/test_app.py`: smoke, CRUD validation, quality workflow and demo sync tests.

## Security and reliability notes

- Credentials are read from environment variables and are never rendered in the browser.
- `.env` and the local SQLite database are excluded by `.gitignore`.
- Requests to WooCommerce use a timeout and concise error reporting.
- The agent recommends changes but never silently mutates product information.
- This is a hackathon MVP; production deployment should add authentication, CSRF protection, stronger role/access controls, database migrations, rate limiting, and structured observability.

## Sync behavior

Without `WC_STORE_URL`, `WC_CONSUMER_KEY`, and `WC_CONSUMER_SECRET`, the app records a `Demo synced` result. With all three values configured, it looks up a product by SKU and updates the match or creates a new product. A demo result is not proof that the remote store was changed.
