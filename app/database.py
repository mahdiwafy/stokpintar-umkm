import sqlite3
import os
from contextlib import contextmanager

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
DB_PATH = os.path.join(DB_DIR, "stok_umkm.db")

os.makedirs(DB_DIR, exist_ok=True)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Umum',
            unit TEXT NOT NULL DEFAULT 'pcs',
            cost_price REAL NOT NULL DEFAULT 0.0,
            selling_price REAL NOT NULL DEFAULT 0.0,
            current_stock REAL NOT NULL DEFAULT 0.0,
            min_stock REAL NOT NULL DEFAULT 5.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('sale', 'restock', 'adjustment')),
            total_amount REAL NOT NULL DEFAULT 0.0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE RESTRICT,
            quantity REAL NOT NULL,
            price_per_unit REAL NOT NULL,
            subtotal REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);
        CREATE INDEX IF NOT EXISTS idx_items_stock ON items(current_stock);
        CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
        """)

        # Seed sample items if table is empty
        cursor = conn.execute("SELECT COUNT(*) AS count FROM items;")
        if cursor.fetchone()["count"] == 0:
            sample_items = [
                ("Beras Premium 5kg", "Sembako", "karung", 64000, 72000, 12, 4),
                ("Minyak Goreng 1L", "Sembako", "pouch", 15500, 18000, 6, 5),
                ("Telur Ayam 1kg", "Sembako", "kg", 25000, 28000, 18, 5),
                ("Gula Pasir 1kg", "Sembako", "kg", 14500, 17000, 8, 4),
                ("Mie Goreng Instan", "Makanan", "bungkus", 2800, 3500, 48, 10),
                ("Kopi Kapal Api Sachet", "Minuman", "renceng", 11000, 13500, 7, 3),
                ("Susu Kental Manis Kaleng", "Minuman", "kaleng", 10500, 12500, 2, 4),
                ("Sabun Cuci Piring 750ml", "Kebutuhan Rumah", "botol", 12000, 14500, 3, 3),
            ]
            conn.executemany("""
                INSERT INTO items (name, category, unit, cost_price, selling_price, current_stock, min_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, sample_items)
