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


def test_health_endpoint(client_and_db):
    client, _ = client_and_db
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
