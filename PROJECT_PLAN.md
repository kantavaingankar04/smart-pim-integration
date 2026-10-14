# Smart PIM — WooCommerce Product Information Management

## Problem
Product information maintained across e-commerce systems can be incomplete, inconsistent, or difficult to synchronize reliably.

## Proposed solution
Build a centralized product catalog dashboard with CRUD operations, product attribute validation, synchronization tracking, a WooCommerce REST API client, and a tool-assisted Catalog Quality Agent.

## Scope
- Create, view, edit, search, and delete products.
- Validate required attributes, unique SKUs, price, and stock.
- Review catalog findings and recommendations before making changes.
- Support clearly labeled demo synchronization and optional live WooCommerce synchronization.
- Record activity and provide tests and setup documentation.

## Architecture
- UI: HTML, CSS, JavaScript-compatible server-rendered templates.
- Backend: Python and Flask.
- Database: SQLite.
- Integration: WooCommerce REST API v3 via a backend-only client.
- Catalog agent: deterministic validation tools for required fields, numeric values, and duplicate SKUs.
- Tests: pytest.

## Assumptions and risks
- Live sync depends on a reachable WooCommerce store and valid API credentials.
- Demo sync is a simulation and does not update a remote store.
- API secrets remain in environment variables and are not committed.
- Agent recommendations require human review; no automatic data mutation is performed.
- The hackathon MVP prioritizes a dependable core workflow over advanced variations, access control, and large-scale sync.

## Delivery plan
1. Build catalog dashboard and SQLite data layer.
2. Add product forms and validation.
3. Add catalog quality tools and reporting.
4. Add demo and optional live WooCommerce sync.
5. Run tests and document architecture, setup, assumptions, and limitations.
6. Publish source to GitHub, record the planning video and closing demo, and submit the repository URL in the official form.

## Demo acceptance criteria
- Dashboard starts locally and shows seeded sample products.
- User can create, edit, search, and delete products.
- Duplicate SKUs and invalid stock values are rejected.
- Catalog Quality Agent reports the tools used, findings, and recommendations without silently changing data.
- Sync makes the difference between demo mode and real WooCommerce behavior clear.
- Tests run and README gives reproducible setup instructions.
