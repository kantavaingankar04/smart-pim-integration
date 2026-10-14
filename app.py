"""Smart PIM: lightweight product information management demo."""
from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from services.database import (
    add_activity, connect_db, delete_product, get_product, get_stats,
    init_db, list_activities, list_products, save_product, update_sync_status,
)
from services.catalog_agent import audit_catalog
from services.woocommerce import sync_product

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "local-demo-change-me")
app.config["DATABASE"] = os.getenv("PIM_DATABASE", str(BASE_DIR / "smart_pim.db"))
app.config["WC_STORE_URL"] = os.getenv("WC_STORE_URL", "")
app.config["WC_LIVE_MODE"] = all(os.getenv(k, "").strip() for k in ("WC_STORE_URL", "WC_CONSUMER_KEY", "WC_CONSUMER_SECRET"))

PRODUCT_FIELDS = ("name", "sku", "brand", "category", "price", "stock", "description")


def parse_product_form(form):
    """Validate and normalize a product form. Returns (data, errors)."""
    data = {key: form.get(key, "").strip() for key in PRODUCT_FIELDS}
    errors = []
    for field in ("name", "sku", "category"):
        if not data[field]:
            errors.append(f"{field.capitalize()} is required.")
    try:
        data["price"] = round(float(data["price"]), 2)
        if data["price"] < 0:
            errors.append("Price cannot be negative.")
    except (TypeError, ValueError):
        data["price"] = 0
        errors.append("Enter a valid price, e.g. 499.00.")
    try:
        data["stock"] = int(data["stock"])
        if data["stock"] < 0:
            errors.append("Stock cannot be negative.")
    except (TypeError, ValueError):
        data["stock"] = 0
        errors.append("Stock must be a whole number.")
    return data, errors


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


@app.before_request
def ensure_database():
    init_db(app.config["DATABASE"])


@app.get("/")
def dashboard():
    query = request.args.get("q", "").strip()
    products = list_products(app.config["DATABASE"], query=query)
    stats = get_stats(app.config["DATABASE"])
    activities = list_activities(app.config["DATABASE"], limit=5)
    return render_template("index.html", products=products, stats=stats,
                           activities=activities, query=query)


@app.route("/products/new", methods=["GET", "POST"])
def new_product():
    if request.method == "POST":
        data, errors = parse_product_form(request.form)
        if not errors:
            try:
                product_id = save_product(app.config["DATABASE"], data)
                add_activity(app.config["DATABASE"], "Product created", f"{data['name']} ({data['sku']})", "success")
                flash("Product created successfully.", "success")
                return redirect(url_for("dashboard"))
            except ValueError as exc:
                errors.append(str(exc))
        for error in errors:
            flash(error, "error")
        return render_template("product_form.html", product=data, mode="Create")
    return render_template("product_form.html", product=None, mode="Create")


@app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    existing = get_product(app.config["DATABASE"], product_id)
    if not existing:
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        data, errors = parse_product_form(request.form)
        if not errors:
            try:
                save_product(app.config["DATABASE"], data, product_id=product_id)
                add_activity(app.config["DATABASE"], "Product updated", f"{data['name']} ({data['sku']})", "success")
                flash("Product updated successfully.", "success")
                return redirect(url_for("dashboard"))
            except ValueError as exc:
                errors.append(str(exc))
        for error in errors:
            flash(error, "error")
        return render_template("product_form.html", product=data, mode="Edit", product_id=product_id)
    return render_template("product_form.html", product=existing, mode="Edit", product_id=product_id)


@app.post("/products/<int:product_id>/delete")
def remove_product(product_id):
    product = get_product(app.config["DATABASE"], product_id)
    if product:
        delete_product(app.config["DATABASE"], product_id)
        add_activity(app.config["DATABASE"], "Product deleted", f"{product['name']} ({product['sku']})", "warning")
        flash("Product deleted.", "success")
    return redirect(url_for("dashboard"))


@app.get("/products/export.csv")
def export_products():
    """Download the complete catalog as a spreadsheet-friendly CSV."""
    products = list_products(app.config["DATABASE"])
    fields = ("id", "name", "sku", "brand", "category", "price", "stock",
              "description", "sync_status", "sync_message", "synced_at", "created_at")
    text_fields = {"name", "sku", "brand", "category", "description", "sync_status", "sync_message", "synced_at", "created_at"}

    def safe_cell(value, field):
        value = "" if value is None else str(value)
        # Reduce spreadsheet formula-injection risk for user-controlled text cells.
        if field in text_fields and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(fields)
    for product in products:
        writer.writerow([safe_cell(product.get(field), field) for field in fields])

    response = app.response_class("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = 'attachment; filename="smart-pim-catalog.csv"'
    return response


@app.get("/quality")
def quality_agent():
    products = list_products(app.config["DATABASE"])
    report = audit_catalog(products)
    return render_template("quality.html", report=report)


@app.post("/products/<int:product_id>/sync")
def product_sync(product_id):
    product = get_product(app.config["DATABASE"], product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))
    result = sync_product(product)
    status = "success" if result["ok"] else "error"
    update_sync_status(app.config["DATABASE"], product_id, result["status"], result["message"])
    add_activity(app.config["DATABASE"], "WooCommerce sync", f"{product['name']}: {result['message']}", status)
    flash(result["message"], "success" if result["ok"] else "error")
    return redirect(request.referrer or url_for("dashboard"))


@app.get("/health")
def health():
    return {"status": "ok", "application": "Smart PIM", "mode": "live" if app.config["WC_LIVE_MODE"] else "demo"}


if __name__ == "__main__":
    init_db(app.config["DATABASE"])
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
