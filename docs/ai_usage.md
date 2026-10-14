# AI Tool Usage Record

## Purpose
AI coding assistance was used as a development aid for the hackathon MVP. Generated code is not treated as automatically correct; the implementation should be reviewed and validated before submission.

## Development activities assisted by AI
- Proposed a minimal architecture for Flask, SQLite, server-rendered templates, and an optional WooCommerce API client.
- Drafted the initial product CRUD routes, schema, validation rules, and UI templates.
- Designed the catalog-quality workflow as a plan-and-tools pipeline, with required-field, numeric-value, and duplicate-SKU checks.
- Drafted pytest coverage for dashboard loading, CRUD validation, catalog audit, demo sync, and the health endpoint.
- Prepared documentation for the architecture, setup, security boundaries, and demo workflow.

## Verification expected before submission
- Run `python -m py_compile app.py services/*.py tests/test_app.py`.
- Install dependencies and run `pytest -q`.
- Manually verify product creation, editing, searching, deleting, and duplicate-SKU rejection.
- Verify the UI labels a simulated synchronization as **Demo synced** and does not claim a remote change occurred.
- Review credentials handling, `.gitignore`, error messages, and README instructions.
- Record any remaining failures or limitations honestly in the final presentation.

## Transparency
The catalog-quality workflow in this MVP is deterministic and tool-assisted. It is not an LLM-powered agent. That choice keeps checks reproducible and functional offline; an LLM planner or recommendation model would be a future extension and should not be claimed unless implemented and tested.
