import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_items(client):
    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 8
    assert "name" in items[0]
    assert "current_stock" in items[0]
    assert "is_low_stock" in items[0]

def test_create_and_delete_item(client):
    payload = {
        "name": "Kecap Manis 550ml",
        "category": "Sembako",
        "unit": "botol",
        "cost_price": 18000,
        "selling_price": 21000,
        "current_stock": 10,
        "min_stock": 3
    }
    create_resp = client.post("/api/items", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "Kecap Manis 550ml"
    item_id = created["id"]

    del_resp = client.delete(f"/api/items/{item_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

def test_sale_deducts_stock(client):
    # Create item with exactly 10 stock
    item_payload = {
        "name": "Sabun Mandi Uji",
        "category": "Kebutuhan",
        "unit": "pcs",
        "cost_price": 3000,
        "selling_price": 4500,
        "current_stock": 10,
        "min_stock": 2
    }
    item_resp = client.post("/api/items", json=item_payload).json()
    item_id = item_resp["id"]

    # Sell 4 pcs
    sale_payload = {
        "items": [{"item_id": item_id, "quantity": 4}],
        "notes": "Penjualan Uji Coba"
    }
    sale_resp = client.post("/api/transactions/sale", json=sale_payload)
    assert sale_resp.status_code == 201
    sale_data = sale_resp.json()
    assert sale_data["total_amount"] == 18000  # 4 * 4500

    # Verify stock is now 6
    updated_item = client.get(f"/api/items/{item_id}").json()
    assert updated_item["current_stock"] == 6

def test_sale_rejects_insufficient_stock(client):
    item_payload = {
        "name": "Barang Langka",
        "category": "Umum",
        "unit": "pcs",
        "cost_price": 1000,
        "selling_price": 2000,
        "current_stock": 2,
        "min_stock": 1
    }
    item_resp = client.post("/api/items", json=item_payload).json()
    item_id = item_resp["id"]

    # Try to sell 5 pcs (only 2 available)
    sale_payload = {
        "items": [{"item_id": item_id, "quantity": 5}]
    }
    sale_resp = client.post("/api/transactions/sale", json=sale_payload)
    assert sale_resp.status_code == 400
    assert "tidak mencukupi" in sale_resp.json()["detail"].lower()

def test_restock_increments_stock(client):
    item_payload = {
        "name": "Kopi Kulakan",
        "category": "Minuman",
        "unit": "renceng",
        "cost_price": 10000,
        "selling_price": 13000,
        "current_stock": 5,
        "min_stock": 3
    }
    item_resp = client.post("/api/items", json=item_payload).json()
    item_id = item_resp["id"]

    restock_payload = {
        "items": [{"item_id": item_id, "quantity": 10, "cost_price": 9500}],
        "notes": "Kulakan Pasar Grosir"
    }
    restock_resp = client.post("/api/transactions/restock", json=restock_payload)
    assert restock_resp.status_code == 201
    assert restock_resp.json()["total_expense"] == 95000

    # Stock should now be 15
    updated_item = client.get(f"/api/items/{item_id}").json()
    assert updated_item["current_stock"] == 15
    assert updated_item["cost_price"] == 9500

def test_stock_adjustment(client):
    item_payload = {
        "name": "Garam Halus",
        "category": "Sembako",
        "unit": "bungkus",
        "cost_price": 2000,
        "selling_price": 3000,
        "current_stock": 20,
        "min_stock": 5
    }
    item_resp = client.post("/api/items", json=item_payload).json()
    item_id = item_resp["id"]

    # Merchant audits and finds only 18 physically (2 leaked/damaged)
    adjust_resp = client.post(f"/api/items/{item_id}/adjust", json={
        "actual_stock": 18,
        "notes": "2 bungkus kemasan robek"
    })
    assert adjust_resp.status_code == 200
    assert adjust_resp.json()["new_stock"] == 18
    assert adjust_resp.json()["difference"] == -2

    updated_item = client.get(f"/api/items/{item_id}").json()
    assert updated_item["current_stock"] == 18

def test_summary_report(client):
    summary_resp = client.get("/api/transactions/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    assert "today_sales_revenue" in data
    assert "today_restock_expense" in data
    assert "critical_stock_count" in data
