import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_auth_flow():
    # Login with seeded manager
    res = client.post("/api/auth/login", json={"username": "manager", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["role"] == "Inventory Manager"

    # Request OTP for password reset
    res_otp = client.post("/api/auth/forgot-password", json={"email": "staff@stocksense.io"})
    assert res_otp.status_code == 200
    otp_code = res_otp.json()["simulated_otp"]

    # Reset password with OTP
    res_reset = client.post("/api/auth/reset-password", json={
        "email": "staff@stocksense.io",
        "otp_code": otp_code,
        "new_password": "newpassword456"
    })
    assert res_reset.status_code == 200

    # Login with new password
    res_login_new = client.post("/api/auth/login", json={"username": "staff", "password": "newpassword456"})
    assert res_login_new.status_code == 200

def test_products_and_stock():
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 6

    # Verify steel rods exist and have stock
    steel = next((p for p in products if "RAW-STL-001" in p["sku"]), None)
    assert steel is not None
    assert steel["total_stock"] > 0
    assert len(steel["locations_stock"]) > 0

def test_create_and_validate_receipt():
    # Fetch a product and location
    prod = client.get("/api/products").json()[0]
    locs = client.get("/api/locations?internal_only=true").json()
    dest_loc = locs[0]

    initial_stock = prod["total_stock"]

    # Create Receipt
    op_payload = {
        "operation_type": "RECEIPT",
        "destination_location_id": dest_loc["id"],
        "partner_name": "Test Global Supplier",
        "notes": "Testing incoming goods validation",
        "items": [
            {"product_id": prod["id"], "demanded_qty": 20.0, "done_qty": 20.0}
        ]
    }
    res = client.post("/api/operations", json=op_payload)
    assert res.status_code == 200
    op = res.json()
    assert op["status"] == "READY"

    # Validate Receipt
    res_val = client.post(f"/api/operations/{op['id']}/validate")
    assert res_val.status_code == 200
    assert res_val.json()["status"] == "DONE"

    # Verify stock increased
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    assert prod_after["total_stock"] == initial_stock + 20.0

def test_delivery_order_workflow():
    products = client.get("/api/products").json()
    prod = next((p for p in products if p["total_stock"] >= 10.0 and len(p["locations_stock"]) > 0), None)
    assert prod is not None
    src_loc_id = prod["locations_stock"][0]["location_id"]

    # Create Delivery Order
    op_payload = {
        "operation_type": "DELIVERY",
        "source_location_id": src_loc_id,
        "partner_name": "Test Customer Inc",
        "notes": "Testing delivery picking, packing, validation",
        "items": [
            {"product_id": prod["id"], "demanded_qty": 5.0, "done_qty": 5.0}
        ]
    }
    op = client.post("/api/operations", json=op_payload).json()
    assert op["status"] == "READY"
    assert op["is_picked"] is False
    assert op["is_packed"] is False

    # Step 1: Pick
    res_pick = client.post(f"/api/operations/{op['id']}/pick")
    assert res_pick.status_code == 200
    assert res_pick.json()["is_picked"] is True

    # Step 2: Pack
    res_pack = client.post(f"/api/operations/{op['id']}/pack")
    assert res_pack.status_code == 200
    assert res_pack.json()["is_packed"] is True

    # Step 3: Validate
    res_val = client.post(f"/api/operations/{op['id']}/validate")
    assert res_val.status_code == 200
    assert res_val.json()["status"] == "DONE"

def test_stock_adjustment():
    prod = client.get("/api/products").json()[0]
    locs = client.get("/api/locations?internal_only=true").json()
    loc = locs[0]

    # Adjust physical count to 150
    adj_payload = {
        "product_id": prod["id"],
        "location_id": loc["id"],
        "counted_qty": 150.0,
        "notes": "Monthly physical inventory audit count"
    }
    res = client.post("/api/adjustments", json=adj_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "DONE"

    # Verify quant is exactly 150
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    matching_loc = next((l for l in prod_after["locations_stock"] if l["location_id"] == loc["id"]), None)
    assert matching_loc["quantity"] == 150.0

def test_demo_scenario():
    res = client.post("/api/demo/run-scenario")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["steps"]) == 4

def test_ledger_move_history():
    res = client.get("/api/ledger")
    assert res.status_code == 200
    ledger = res.json()
    assert len(ledger) > 0
    # Every ledger record has reference, quantity change, resulting balance
    entry = ledger[0]
    assert "reference_number" in entry
    assert "quantity_change" in entry
    assert "resulting_balance" in entry

def test_dashboard_kpis():
    res = client.get("/api/dashboard/kpis")
    assert res.status_code == 200
    kpis = res.json()["kpis"]
    assert "total_products_in_stock" in kpis
    assert "low_stock_items_count" in kpis
    assert "pending_receipts_count" in kpis
    assert "pending_deliveries_count" in kpis
    assert "internal_transfers_scheduled_count" in kpis
