from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..database import get_db
from ..models import ItemCreate, ItemUpdate, ItemStockAdjust, ItemResponse

router = APIRouter(prefix="/api/items", tags=["Items & Inventory"])

def row_to_item(row) -> dict:
    d = dict(row)
    d["is_low_stock"] = d["current_stock"] <= d["min_stock"]
    return d

@router.get("", response_model=List[ItemResponse])
def get_items(
    q: Optional[str] = Query(None, description="Cari nama atau barcode"),
    category: Optional[str] = Query(None, description="Filter kategori"),
    low_stock: Optional[bool] = Query(None, description="Hanya tampilkan stok menipis")
):
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if q:
        query += " AND (name LIKE ? OR barcode LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    
    if category and category != "Semua":
        query += " AND category = ?"
        params.append(category)

    if low_stock:
        query += " AND current_stock <= min_stock"

    query += " ORDER BY (current_stock <= min_stock) DESC, name ASC;"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [row_to_item(r) for r in rows]

@router.get("/categories")
def get_categories():
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM items ORDER BY category ASC;").fetchall()
        return [r["category"] for r in rows if r["category"]]

@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?;", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
        return row_to_item(row)

@router.post("", response_model=ItemResponse, status_code=201)
def create_item(payload: ItemCreate):
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO items (barcode, name, category, unit, cost_price, selling_price, current_stock, min_stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (payload.barcode, payload.name, payload.category, payload.unit, payload.cost_price, payload.selling_price, payload.current_stock, payload.min_stock))
        new_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM items WHERE id = ?;", (new_id,)).fetchone()
        return row_to_item(row)

@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdate):
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM items WHERE id = ?;", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")

        updates = []
        params = []
        for field, value in payload.model_dump(exclude_unset=True).items():
            updates.append(f"{field} = ?")
            params.append(value)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(item_id)
            conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?;", params)

        row = conn.execute("SELECT * FROM items WHERE id = ?;", (item_id,)).fetchone()
        return row_to_item(row)

@router.post("/{item_id}/adjust")
def adjust_stock(item_id: int, payload: ItemStockAdjust):
    with get_db() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?;", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")

        old_stock = item["current_stock"]
        new_stock = payload.actual_stock
        diff = new_stock - old_stock

        # Update item stock
        conn.execute("UPDATE items SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (new_stock, item_id))

        # Log adjustment transaction
        cur = conn.execute("""
            INSERT INTO transactions (type, total_amount, notes)
            VALUES ('adjustment', 0.0, ?);
        """, (f"{payload.notes} (Audit fisik: {old_stock} -> {new_stock} {item['unit']}, selisih: {diff:+g})",))
        tx_id = cur.lastrowid

        conn.execute("""
            INSERT INTO transaction_items (transaction_id, item_id, quantity, price_per_unit, subtotal)
            VALUES (?, ?, ?, ?, 0.0);
        """, (tx_id, item_id, diff, item["cost_price"]))

        return {
            "success": True,
            "item_id": item_id,
            "old_stock": old_stock,
            "new_stock": new_stock,
            "difference": diff,
            "unit": item["unit"],
            "message": f"Stok {item['name']} berhasil diperbarui menjadi {new_stock} {item['unit']}."
        }

@router.delete("/{item_id}")
def delete_item(item_id: int):
    with get_db() as conn:
        # Check if item is used in transactions
        used = conn.execute("SELECT COUNT(*) AS count FROM transaction_items WHERE item_id = ?;", (item_id,)).fetchone()
        if used["count"] > 0:
            raise HTTPException(status_code=400, detail="Barang sudah memiliki riwayat transaksi dan tidak dapat dihapus secara permanen.")
        
        conn.execute("DELETE FROM items WHERE id = ?;", (item_id,))
        return {"success": True, "message": "Barang berhasil dihapus"}
