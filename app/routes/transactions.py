from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..database import get_db
from ..models import SaleCreate, RestockCreate

router = APIRouter(prefix="/api/transactions", tags=["Transactions & Cashflow"])

@router.post("/sale", status_code=201)
def process_sale(payload: SaleCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Keranjang belanja tidak boleh kosong")

    with get_db() as conn:
        total_amount = 0.0
        line_items_data = []

        # 1. Validate items and verify stocks
        for ci in payload.items:
            item = conn.execute("SELECT * FROM items WHERE id = ?;", (ci.item_id,)).fetchone()
            if not item:
                raise HTTPException(status_code=404, detail=f"Barang dengan ID {ci.item_id} tidak ditemukan")

            available = item["current_stock"]
            if available < ci.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stok {item['name']} tidak mencukupi! Tersedia: {available} {item['unit']}, diminta: {ci.quantity} {item['unit']}."
                )

            price = ci.price_per_unit if ci.price_per_unit is not None else item["selling_price"]
            subtotal = price * ci.quantity
            total_amount += subtotal

            line_items_data.append({
                "item_id": item["id"],
                "name": item["name"],
                "quantity": ci.quantity,
                "price": price,
                "subtotal": subtotal,
                "old_stock": available,
                "new_stock": available - ci.quantity
            })

        # 2. Insert transaction record
        cur = conn.execute("""
            INSERT INTO transactions (type, total_amount, notes)
            VALUES ('sale', ?, ?);
        """, (total_amount, payload.notes or "Penjualan Kasir Cepat"))
        tx_id = cur.lastrowid

        # 3. Insert transaction items & deduct stock atomically
        for line in line_items_data:
            conn.execute("""
                INSERT INTO transaction_items (transaction_id, item_id, quantity, price_per_unit, subtotal)
                VALUES (?, ?, ?, ?, ?);
            """, (tx_id, line["item_id"], line["quantity"], line["price"], line["subtotal"]))

            conn.execute("""
                UPDATE items
                SET current_stock = current_stock - ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (line["quantity"], line["item_id"]))

        return {
            "success": True,
            "transaction_id": tx_id,
            "type": "sale",
            "total_amount": total_amount,
            "items_sold": line_items_data,
            "message": f"Transaksi penjualan berhasil diproses. Total: Rp {total_amount:,.0f}"
        }

@router.post("/restock", status_code=201)
def process_restock(payload: RestockCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Daftar kulakan tidak boleh kosong")

    with get_db() as conn:
        total_amount = 0.0
        restocked_details = []

        for ri in payload.items:
            item_id = ri.item_id
            # If item_id is missing, search by name or create new item
            if not item_id and ri.name:
                existing = conn.execute("SELECT * FROM items WHERE LOWER(name) = LOWER(?);", (ri.name.strip(),)).fetchone()
                if existing:
                    item_id = existing["id"]
                else:
                    cur = conn.execute("""
                        INSERT INTO items (name, category, unit, cost_price, selling_price, current_stock, min_stock)
                        VALUES (?, 'Umum', 'pcs', ?, ?, 0, 5);
                    """, (ri.name.strip(), ri.cost_price, ri.selling_price or (ri.cost_price * 1.2)))
                    item_id = cur.lastrowid

            if not item_id:
                raise HTTPException(status_code=400, detail="Data barang kulakan wajib menyertakan ID barang atau nama barang")

            item = conn.execute("SELECT * FROM items WHERE id = ?;", (item_id,)).fetchone()
            if not item:
                raise HTTPException(status_code=404, detail=f"Barang ID {item_id} tidak ditemukan")

            subtotal = ri.cost_price * ri.quantity
            total_amount += subtotal

            # Update item cost price & selling price if provided
            conn.execute("""
                UPDATE items
                SET current_stock = current_stock + ?,
                    cost_price = ?,
                    selling_price = COALESCE(?, selling_price),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (ri.quantity, ri.cost_price, ri.selling_price, item_id))

            restocked_details.append({
                "item_id": item_id,
                "name": item["name"],
                "quantity_added": ri.quantity,
                "new_stock": item["current_stock"] + ri.quantity,
                "cost_price": ri.cost_price,
                "subtotal": subtotal
            })

        # Insert transaction record
        cur = conn.execute("""
            INSERT INTO transactions (type, total_amount, notes)
            VALUES ('restock', ?, ?);
        """, (total_amount, payload.notes or "Kulakan / Belanja Stok"))
        tx_id = cur.lastrowid

        for line in restocked_details:
            conn.execute("""
                INSERT INTO transaction_items (transaction_id, item_id, quantity, price_per_unit, subtotal)
                VALUES (?, ?, ?, ?, ?);
            """, (tx_id, line["item_id"], line["quantity_added"], line["cost_price"], line["subtotal"]))

        return {
            "success": True,
            "transaction_id": tx_id,
            "type": "restock",
            "total_expense": total_amount,
            "restocked_items": restocked_details,
            "message": f"Kulakan berhasil dicatat. Total belanja: Rp {total_amount:,.0f}"
        }

@router.get("")
def list_transactions(
    type: Optional[str] = Query(None, description="Filter tipe: sale, restock, adjustment"),
    limit: int = Query(30, ge=1, le=100)
):
    query = """
        SELECT t.id, t.type, t.total_amount, t.notes, t.created_at,
               COUNT(ti.id) AS items_count
        FROM transactions t
        LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
        WHERE 1=1
    """
    params = []
    if type:
        query += " AND t.type = ?"
        params.append(type)
    
    query += " GROUP BY t.id ORDER BY t.created_at DESC LIMIT ?;"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@router.get("/summary")
def get_summary():
    with get_db() as conn:
        # Today's sales
        sales_row = conn.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_sales, COUNT(*) AS count_sales
            FROM transactions
            WHERE type = 'sale' AND DATE(created_at, '+7 hours') = DATE('now', '+7 hours');
        """).fetchone()

        # Today's restock (expenses)
        restock_row = conn.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_restock, COUNT(*) AS count_restock
            FROM transactions
            WHERE type = 'restock' AND DATE(created_at, '+7 hours') = DATE('now', '+7 hours');
        """).fetchone()

        # Low stock items count
        low_stock_row = conn.execute("""
            SELECT COUNT(*) AS count_low FROM items WHERE current_stock <= min_stock;
        """).fetchone()

        # Total items registered
        total_items_row = conn.execute("SELECT COUNT(*) AS total FROM items;").fetchone()

        return {
            "today_sales_revenue": sales_row["total_sales"],
            "today_sales_count": sales_row["count_sales"],
            "today_restock_expense": restock_row["total_restock"],
            "today_restock_count": restock_row["count_restock"],
            "net_cashflow_today": sales_row["total_sales"] - restock_row["total_restock"],
            "critical_stock_count": low_stock_row["count_low"],
            "total_inventory_items": total_items_row["total"]
        }
