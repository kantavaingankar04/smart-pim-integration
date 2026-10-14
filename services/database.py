"""SQLite persistence and catalog queries for Smart PIM."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SEED_PRODUCTS = [
    ("Everyday Cotton T-Shirt", "TSHIRT-001", "Northstar", "Apparel", 599.00, 42, "Soft cotton crew-neck T-shirt for everyday wear."),
    ("Insulated Water Bottle", "BOTTLE-002", "TrailWorks", "Accessories", 799.00, 18, "Double-wall insulated stainless-steel bottle."),
    ("Wireless Desk Mouse", "MOUSE-003", "PixelPoint", "Electronics", 1299.00, 25, "Ergonomic wireless mouse with adjustable DPI."),
    ("Canvas Travel Tote", "TOTE-004", "Northstar", "Accessories", 449.00, 0, "Reusable canvas tote for daily essentials."),
    ("Ceramic Coffee Mug", "MUG-005", "HomeKind", "Home", 349.00, 31, "Minimal ceramic mug with a comfortable handle."),
]


def connect_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session(path):
    conn = connect_db(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path):
    with db_session(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
            brand TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL,
            price REAL NOT NULL CHECK(price >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            description TEXT NOT NULL DEFAULT '',
            sync_status TEXT NOT NULL DEFAULT 'Not synced',
            sync_message TEXT NOT NULL DEFAULT '',
            synced_at TEXT,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            created_at TEXT NOT NULL
        )""")
        conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        seeded = conn.execute("SELECT value FROM app_meta WHERE key = 'demo_seeded'").fetchone()
        if not seeded:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count == 0:
                conn.executemany("""INSERT INTO products
                    (name, sku, brand, category, price, stock, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [(*row, now) for row in SEED_PRODUCTS])
                conn.execute("INSERT INTO activity(action, details, level, created_at) VALUES (?, ?, ?, ?)",
                             ("Demo catalog loaded", "Five sample products are ready to explore.", "success", now))
            conn.execute("INSERT INTO app_meta(key, value) VALUES ('demo_seeded', '1')")


def list_products(path, query=""):
    with db_session(path) as conn:
        if query:
            pattern = f"%{query}%"
            rows = conn.execute("""SELECT * FROM products WHERE name LIKE ? OR sku LIKE ?
                OR brand LIKE ? OR category LIKE ? ORDER BY id DESC""",
                (pattern, pattern, pattern, pattern)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def get_product(path, product_id):
    with db_session(path) as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None


def save_product(path, data, product_id=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with db_session(path) as conn:
            if product_id is None:
                cur = conn.execute("""INSERT INTO products
                    (name, sku, brand, category, price, stock, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (data["name"], data["sku"], data.get("brand", ""), data["category"],
                     data["price"], data["stock"], data.get("description", ""), now))
                return cur.lastrowid
            conn.execute("""UPDATE products SET name=?, sku=?, brand=?, category=?, price=?, stock=?,
                description=?, sync_status='Not synced', sync_message='', synced_at=NULL WHERE id=?""",
                (data["name"], data["sku"], data.get("brand", ""), data["category"],
                 data["price"], data["stock"], data.get("description", ""), product_id))
            return product_id
    except sqlite3.IntegrityError as exc:
        if "sku" in str(exc).lower() or "unique" in str(exc).lower():
            raise ValueError("That SKU already exists. Use a unique SKU.") from exc
        raise ValueError("Product could not be saved. Check the supplied values.") from exc


def delete_product(path, product_id):
    with db_session(path) as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def get_stats(path):
    with db_session(path) as conn:
        row = conn.execute("""SELECT COUNT(*) AS total,
            COALESCE(SUM(stock),0) AS units,
            COALESCE(SUM(price * stock),0) AS inventory_value,
            SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS out_of_stock,
            SUM(CASE WHEN sync_status = 'Synced' THEN 1 ELSE 0 END) AS synced
            FROM products""").fetchone()
        return dict(row)


def update_sync_status(path, product_id, status, message):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_session(path) as conn:
        conn.execute("UPDATE products SET sync_status=?, sync_message=?, synced_at=? WHERE id=?",
                     (status, message, now if status == "Synced" else None, product_id))


def add_activity(path, action, details, level="info"):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db_session(path) as conn:
        conn.execute("INSERT INTO activity(action, details, level, created_at) VALUES (?, ?, ?, ?)",
                     (action, details, level, now))


def list_activities(path, limit=10):
    with db_session(path) as conn:
        rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]
