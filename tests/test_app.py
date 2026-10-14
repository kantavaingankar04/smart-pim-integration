import os
import tempfile

import pytest

from app import app as flask_app
from services.catalog_agent import audit_catalog
from services.database import init_db, list_products, save_product
from services.woocommerce import sync_product


@pytest.fixture()
def client_and_db(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setitem(flask_app.config, "DATABASE", db_path)
    flask_app.config["TESTING"] = True
    init_db(db_path)
    with flask_app.test_client() as client:
        yield client, db_path
    os.unlink(db_path)


def test_dashboard_loads_seed_catalog(client_and_db):
    client, _ = client_and_db
    response = client.get("/")
    assert response.status_code == 200
    assert b"Product catalog" in response.data
    assert b"Everyday Cotton T-Shirt" in response.data


def test_create_product_and_reject_duplicate_sku(client_and_db):
    client, db_path = client_and_db
    payload = {"name": "Test Product", "sku": "TEST-900", "brand": "Tester",
               "category": "Testing", "price": "25.50", "stock": "4", "description": "A test item."}
    response = client.post("/products/new", data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"Test Product" in response.data
    with pytest.raises(ValueError, match="unique SKU"):
        save_product(db_path, {**payload, "name": "Duplicate"})


def test_form_validation_rejects_negative_stock(client_and_db):
    client, _ = client_and_db
    response = client.post("/products/new", data={"name": "Bad", "sku": "BAD-1", "category": "Test", "price": "5", "stock": "-1"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Stock cannot be negative" in response.data


def test_catalog_agent_uses_tools_and_reports_summary(client_and_db):
    _, db_path = client_and_db
    report = audit_catalog(list_products(db_path))
    assert report["products_scanned"] == 5
    assert report["tools_used"] == ["required_fields", "numeric_values", "duplicate_skus"]
    assert "no product data was changed" in report["summary"].lower()


def test_quality_page_renders(client_and_db):
    client, _ = client_and_db
    response = client.get("/quality")
    assert response.status_code == 200
    assert b"Catalog Quality Agent" in response.data


def test_sync_falls_back_to_explicit_demo_mode(monkeypatch):
    monkeypatch.delenv("WC_STORE_URL", raising=False)
    monkeypatch.delenv("WC_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("WC_CONSUMER_SECRET", raising=False)
    result = sync_product({"sku": "T-1", "name": "Test", "price": 10, "stock": 1, "description": ""})
    assert result["ok"] is True
    assert result["status"] == "Demo synced"
    assert result["mode"] == "demo"


def test_export_catalog_csv_downloads_seed_products(client_and_db):
    client, _ = client_and_db
    response = client.get("/products/export.csv")
    assert response.status_code == 200
    assert response.content_type.startswith("text/csv")
    disposition = response.headers["Content-Disposition"]
    assert disposition.startswith('attachment; filename="smart_pim_catalog_')
    assert disposition.endswith('.csv"')
    csv_text = response.data.decode("utf-8-sig")
    assert "id,name,sku,brand,category,price,stock" in csv_text
    assert "Everyday Cotton T-Shirt" in csv_text
    assert "TSHIRT-001" in csv_text


def test_export_csv_parses_correctly_with_all_seed_products(client_and_db):
    """Verify the CSV is well-formed and contains all five seed products."""
    import csv as csv_mod
    import io as io_mod

    client, _ = client_and_db
    response = client.get("/products/export.csv")
    csv_text = response.data.decode("utf-8-sig")
    reader = csv_mod.DictReader(io_mod.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 5
    skus = {row["sku"] for row in rows}
    assert "TSHIRT-001" in skus
    assert "BOTTLE-002" in skus
    assert "MUG-005" in skus
    for row in rows:
        assert row["name"]
        assert row["category"]


def test_export_csv_escaping_and_unicode(client_and_db):
    """A product with commas, quotes, newlines and Unicode survives a round-trip."""
    import csv as csv_mod
    import io as io_mod

    client, db_path = client_and_db
    tricky_name = 'Commas, "Quotes", and\nnewlines'
    unicode_desc = "हिन्दी विवरण — prix spécial"
    save_product(db_path, {
        "name": tricky_name, "sku": "TRICKY-99", "brand": "Test",
        "category": "Special", "price": 42.50, "stock": 3,
        "description": unicode_desc,
    })
    response = client.get("/products/export.csv")
    csv_text = response.data.decode("utf-8-sig")
    reader = csv_mod.DictReader(io_mod.StringIO(csv_text))
    rows = {row["sku"]: row for row in reader}
    assert "TRICKY-99" in rows
    assert rows["TRICKY-99"]["name"] == tricky_name
    assert rows["TRICKY-99"]["description"] == unicode_desc


def test_export_csv_formula_injection_protection(client_and_db):
    """Dangerous text prefixes are neutralized; numeric price remains usable."""
    import csv as csv_mod
    import io as io_mod

    client, db_path = client_and_db
    save_product(db_path, {
        "name": "=cmd('calc')", "sku": "INJECT-01", "brand": "+evil",
        "category": "@danger", "price": 10.00, "stock": 1,
        "description": "-DDE(link)",
    })
    save_product(db_path, {
        "name": "\t=hidden", "sku": "INJECT-02", "brand": "\r=hidden",
        "category": "Safe", "price": 9.99, "stock": 0,
        "description": "",
    })
    response = client.get("/products/export.csv")
    csv_text = response.data.decode("utf-8-sig")
    reader = csv_mod.DictReader(io_mod.StringIO(csv_text))
    rows = {row["sku"]: row for row in reader}

    # Dangerous text fields are escaped with a leading single-quote.
    assert rows["INJECT-01"]["name"].startswith("'")
    assert rows["INJECT-01"]["brand"].startswith("'")
    assert rows["INJECT-01"]["category"].startswith("'")
    assert rows["INJECT-01"]["description"].startswith("'")

    # Tab and carriage-return prefixed values are also escaped.
    assert rows["INJECT-02"]["name"].startswith("'")
    assert rows["INJECT-02"]["brand"].startswith("'")

    # Numeric fields like price pass through as usable numbers, not strings.
    assert float(rows["INJECT-01"]["price"]) == 10.0
    assert float(rows["INJECT-02"]["price"]) == 9.99


def test_export_csv_empty_catalog(monkeypatch):
    """An empty database still returns a valid header-only CSV (HTTP 200)."""
    import csv as csv_mod
    import io as io_mod

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setitem(flask_app.config, "DATABASE", db_path)
    flask_app.config["TESTING"] = True
    init_db(db_path)

    # Delete all seeded products to simulate an empty catalog.
    from services.database import db_session
    with db_session(db_path) as conn:
        conn.execute("DELETE FROM products")

    with flask_app.test_client() as client:
        response = client.get("/products/export.csv")
        assert response.status_code == 200
        assert response.content_type.startswith("text/csv")
        csv_text = response.data.decode("utf-8-sig")
        reader = csv_mod.DictReader(io_mod.StringIO(csv_text))
        rows = list(reader)
        assert len(rows) == 0
        assert "id" in reader.fieldnames
        assert "name" in reader.fieldnames
    os.unlink(db_path)


def test_export_does_not_modify_data(client_and_db):
    """Exporting the catalog must not create, delete or update any records."""
    client, db_path = client_and_db
    products_before = list_products(db_path)
    from services.database import list_activities
    activities_before = list_activities(db_path, limit=100)

    response = client.get("/products/export.csv")
    assert response.status_code == 200

    products_after = list_products(db_path)
    activities_after = list_activities(db_path, limit=100)
    assert len(products_before) == len(products_after)
    assert len(activities_before) == len(activities_after)
    for before, after in zip(
        sorted(products_before, key=lambda p: p["id"]),
        sorted(products_after, key=lambda p: p["id"]),
    ):
        assert before == after


def test_health_endpoint(client_and_db):
    client, _ = client_and_db
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

