"""
StockSense - Comprehensive Specification & Edge Case Test Suite
Validates all requirements, workflows, and edge cases from the PDF problem statement:
- Authentication & OTP Password Reset
- Product Management, UoM, Stock per Location & Reordering Rules
- Receipts (Incoming Stock) & Stock Ledger Verification
- Delivery Orders (Outgoing Stock) with Pick & Pack Workflow and Stock Depletion
- Internal Transfers (Inter-Warehouse/Rack) with Stock Invariance Checks
- Stock Adjustments (Physical Count Reconciliation)
- Complete Double-Entry Move History (Stock Ledger)
- Dashboard KPIs & Multi-Dimensional Dynamic Filtering
- Multi-Warehouse & Locations Hierarchy
- Edge Cases (Insufficient stock, negative counts, duplicate SKUs, replay attacks, duplicate validation)
- Simplified 4-Step Flow from PDF Page 4
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ==============================================================================
# 1. AUTHENTICATION & TARGET USERS (PDF Page 1 & Page 2)
# ==============================================================================

def test_user_personas_and_login():
    """Verify target users: Inventory Manager and Warehouse Staff can authenticate."""
    # Inventory Manager
    res_mgr = client.post("/api/auth/login", json={"username": "manager", "password": "password123"})
    assert res_mgr.status_code == 200
    data_mgr = res_mgr.json()
    assert data_mgr["user"]["role"] == "Inventory Manager"
    token_mgr = data_mgr["token"]

    # Verify Profile Endpoint
    res_me = client.get(f"/api/auth/me?token={token_mgr}")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "manager@stocksense.io"

    # Warehouse Staff
    res_staff = client.post("/api/auth/login", json={"username": "staff", "password": "password123"})
    if res_staff.status_code == 401:
        res_staff = client.post("/api/auth/login", json={"username": "staff", "password": "newpassword456"})
    assert res_staff.status_code == 200
    assert res_staff.json()["user"]["role"] == "Warehouse Staff"

    # Edge Case: Invalid password
    res_bad = client.post("/api/auth/login", json={"username": "manager", "password": "wrongpassword"})
    assert res_bad.status_code == 401

import uuid

def test_user_registration_and_edge_cases():
    """Verify user sign up and duplicate constraints."""
    uid = uuid.uuid4().hex[:6]
    username = f"warehouse_lead_{uid}"
    email = f"lead_{uid}@stocksense.io"

    reg_payload = {
        "username": username,
        "email": email,
        "full_name": "Jordan Lead",
        "password": "securepassword123",
        "role": "Warehouse Staff"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200
    assert res.json()["username"] == username

    # Edge Case: Duplicate username rejection
    res_dup_user = client.post("/api/auth/register", json=reg_payload)
    assert res_dup_user.status_code == 400
    assert "Username already taken" in res_dup_user.json()["detail"]

    # Edge Case: Duplicate email rejection
    reg_payload_diff_user = reg_payload.copy()
    reg_payload_diff_user["username"] = "diff_user_lead"
    res_dup_email = client.post("/api/auth/register", json=reg_payload_diff_user)
    assert res_dup_email.status_code == 400
    assert "Email already registered" in res_dup_email.json()["detail"]

def test_otp_password_reset_and_edge_cases():
    """Verify OTP generation, password reset, and replay attack prevention."""
    uid = uuid.uuid4().hex[:6]
    test_email = f"reset_test_{uid}@stocksense.io"
    test_user = f"reset_user_{uid}"

    # Register fresh user
    client.post("/api/auth/register", json={
        "username": test_user,
        "email": test_email,
        "full_name": "Reset Tester",
        "password": "oldpassword123",
        "role": "Warehouse Staff"
    })

    # Step 1: Request OTP
    res_req = client.post("/api/auth/forgot-password", json={"email": test_email})
    assert res_req.status_code == 200
    otp_code = res_req.json()["simulated_otp"]
    assert len(otp_code) == 6

    # Edge Case 1: Non-existent email
    res_non_exist = client.post("/api/auth/forgot-password", json={"email": "ghost@nonexistent.io"})
    assert res_non_exist.status_code == 404

    # Edge Case 2: Wrong OTP Code
    res_wrong_otp = client.post("/api/auth/reset-password", json={
        "email": test_email,
        "otp_code": "000000",
        "new_password": "brandnewpassword999"
    })
    assert res_wrong_otp.status_code == 400
    assert "Invalid or expired OTP" in res_wrong_otp.json()["detail"]

    # Step 2: Valid OTP verification
    res_valid = client.post("/api/auth/reset-password", json={
        "email": test_email,
        "otp_code": otp_code,
        "new_password": "brandnewpassword999"
    })
    assert res_valid.status_code == 200

    # Step 3: Verify login with new password
    res_login_new = client.post("/api/auth/login", json={
        "username": test_user,
        "password": "brandnewpassword999"
    })
    assert res_login_new.status_code == 200

    # Edge Case 3: Replay attack (using same OTP code a second time must fail)
    res_replay = client.post("/api/auth/reset-password", json={
        "email": test_email,
        "otp_code": otp_code,
        "new_password": "anotherpassword"
    })
    assert res_replay.status_code == 400


# ==============================================================================
# 2. PRODUCT MANAGEMENT & REORDERING RULES (PDF Page 2 & Page 3)
# ==============================================================================

def test_product_lifecycle_and_edge_cases():
    """Test product creation with UOM, initial stock, and edge cases."""
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]
    locs = client.get("/api/locations?internal_only=true").json()
    main_store_id = locs[0]["id"]

    uid = uuid.uuid4().hex[:6]
    sku = f"TEST-PROD-{uid}"
    prod_data = {
        "sku": sku,
        "name": f"Heavy Duty Steel Fasteners {uid}",
        "description": "High tensile grade 12 fasteners",
        "category_id": cat_id,
        "uom": "boxes",
        "min_reorder_qty": 20.0,
        "max_target_qty": 200.0,
        "cost_price": 12.50,
        "selling_price": 24.00,
        "initial_stock": 50.0,
        "initial_location_id": main_store_id
    }
    res = client.post("/api/products", json=prod_data)
    assert res.status_code == 200
    p = res.json()
    assert p["sku"] == sku
    assert p["total_stock"] == 50.0
    assert p["is_low_stock"] is False
    assert p["is_out_of_stock"] is False
    assert len(p["locations_stock"]) > 0

    # Verify initial stock created a ledger entry
    res_ledger = client.get(f"/api/ledger?product_id={p['id']}")
    assert res_ledger.status_code == 200
    assert len(res_ledger.json()) >= 1
    assert res_ledger.json()[0]["quantity_change"] == 50.0

    # Edge Case 1: Duplicate SKU rejection
    res_dup_sku = client.post("/api/products", json=prod_data)
    assert res_dup_sku.status_code == 400
    assert "already exists" in res_dup_sku.json()["detail"]

    # Edge Case 2: Negative initial stock
    bad_prod = prod_data.copy()
    bad_prod["sku"] = f"BAD-PROD-NEG-{uid}"
    bad_prod["initial_stock"] = -10.0
    res_neg_stock = client.post("/api/products", json=bad_prod)
    assert res_neg_stock.status_code == 400

    # Edge Case 3: Negative min reorder quantity
    bad_prod["initial_stock"] = 0
    bad_prod["min_reorder_qty"] = -5.0
    res_neg_min = client.post("/api/products", json=bad_prod)
    assert res_neg_min.status_code == 400

def test_reordering_rules_and_low_stock_alerts():
    """Verify products under min_reorder_qty trigger low stock alerts."""
    # Find or create a product with stock <= min_reorder_qty
    products = client.get("/api/products").json()
    low_stock_prods = [p for p in products if p["is_low_stock"] or p["is_out_of_stock"]]
    assert len(low_stock_prods) > 0

    # Test filtering by low stock only
    res_filtered = client.get("/api/products?low_stock_only=true")
    assert res_filtered.status_code == 200
    filtered_list = res_filtered.json()
    for item in filtered_list:
        assert item["is_low_stock"] or item["is_out_of_stock"]


# ==============================================================================
# 3. RECEIPTS (INCOMING GOODS) (PDF Page 2)
# ==============================================================================

def test_receipt_full_workflow():
    """
    Process:
    1. Create a new receipt
    2. Add supplier & products
    3. Input quantities received
    4. Validate -> stock increases automatically (Example: Receive 50 units -> stock +50)
    """
    prods = client.get("/api/products").json()
    prod = prods[0]
    initial_stock = prod["total_stock"]

    locs = client.get("/api/locations?internal_only=true").json()
    dest_loc = locs[0]

    receipt_payload = {
        "operation_type": "RECEIPT",
        "destination_location_id": dest_loc["id"],
        "partner_name": "Apex Global Vendor Supplies",
        "notes": "Incoming batch of raw materials",
        "items": [
            {"product_id": prod["id"], "demanded_qty": 30.0, "done_qty": 30.0}
        ]
    }
    res_op = client.post("/api/operations", json=receipt_payload)
    assert res_op.status_code == 200
    op = res_op.json()
    assert op["operation_type"] == "RECEIPT"
    assert op["status"] == "READY"

    # Validate receipt
    res_val = client.post(f"/api/operations/{op['id']}/validate")
    assert res_val.status_code == 200
    assert res_val.json()["status"] == "DONE"

    # Verify stock increased by +30
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    assert prod_after["total_stock"] == initial_stock + 30.0

    # Verify Move History (Stock Ledger) entry
    ledger_entries = client.get(f"/api/ledger?product_id={prod['id']}").json()
    latest_move = ledger_entries[0]
    assert latest_move["operation_type"] == "RECEIPT"
    assert latest_move["quantity_change"] == 30.0
    dest_loc_stock = next((l["quantity"] for l in prod_after["locations_stock"] if l["location_id"] == dest_loc["id"]), 0.0)
    assert latest_move["resulting_balance"] == dest_loc_stock

    # Edge Case: Attempting to validate an already DONE operation must fail
    res_reval = client.post(f"/api/operations/{op['id']}/validate")
    assert res_reval.status_code == 400
    assert "already been validated" in res_reval.json()["detail"]


# ==============================================================================
# 4. DELIVERY ORDERS (OUTGOING GOODS) (PDF Page 3)
# ==============================================================================

def test_delivery_order_workflow_and_stock_reduction():
    """
    Process:
    1. Pick items
    2. Pack items
    3. Validate -> stock decreases automatically (Example: order for 10 chairs -> reduces by 10)
    """
    products = client.get("/api/products").json()
    # Find a product with available on-hand stock >= 15
    prod = next((p for p in products if p["total_stock"] >= 15.0 and len(p["locations_stock"]) > 0), None)
    assert prod is not None
    src_loc_id = prod["locations_stock"][0]["location_id"]
    initial_stock = prod["total_stock"]

    delivery_payload = {
        "operation_type": "DELIVERY",
        "source_location_id": src_loc_id,
        "partner_name": "Executive Offices Corp",
        "notes": "Customer shipment delivery order",
        "items": [
            {"product_id": prod["id"], "demanded_qty": 10.0, "done_qty": 10.0}
        ]
    }
    op = client.post("/api/operations", json=delivery_payload).json()
    assert op["status"] == "READY"
    assert op["is_picked"] is False
    assert op["is_packed"] is False

    # Step 1: Pick items
    res_pick = client.post(f"/api/operations/{op['id']}/pick")
    assert res_pick.status_code == 200
    assert res_pick.json()["is_picked"] is True

    # Step 2: Pack items
    res_pack = client.post(f"/api/operations/{op['id']}/pack")
    assert res_pack.status_code == 200
    assert res_pack.json()["is_packed"] is True

    # Step 3: Validate -> stock decreases automatically
    res_val = client.post(f"/api/operations/{op['id']}/validate")
    assert res_val.status_code == 200
    assert res_val.json()["status"] == "DONE"

    # Verify stock decreased by 10
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    assert prod_after["total_stock"] == initial_stock - 10.0

    # Verify Move History (Stock Ledger)
    ledger = client.get(f"/api/ledger?product_id={prod['id']}").json()
    latest_del = ledger[0]
    assert latest_del["operation_type"] == "DELIVERY"
    assert latest_del["quantity_change"] == -10.0

def test_delivery_order_insufficient_stock_edge_case():
    """Edge Case: Delivery order demanding more stock than available must be rejected."""
    products = client.get("/api/products").json()
    prod = products[0]
    locs = client.get("/api/locations?internal_only=true").json()
    src_loc_id = locs[0]["id"]

    # Find quantity at this location
    loc_quant = next((l["quantity"] for l in prod["locations_stock"] if l["location_id"] == src_loc_id), 0.0)

    # Request more than available
    excess_qty = loc_quant + 5000.0
    excess_op = client.post("/api/operations", json={
        "operation_type": "DELIVERY",
        "source_location_id": src_loc_id,
        "partner_name": "Overdemanding Client",
        "items": [
            {"product_id": prod["id"], "demanded_qty": excess_qty, "done_qty": excess_qty}
        ]
    }).json()

    # Validating must fail with 400 Insufficient stock
    res_val = client.post(f"/api/operations/{excess_op['id']}/validate")
    assert res_val.status_code == 400
    assert "Insufficient stock" in res_val.json()["detail"]


# ==============================================================================
# 5. INTERNAL TRANSFERS (PDF Page 3)
# ==============================================================================

def test_internal_transfer_and_stock_invariance():
    """
    Example from PDF:
    - Main Warehouse -> Production Floor
    - Rack A -> Rack B
    - Stock unchanged in total company, but location balances updated.
    - Each movement logged in the ledger.
    """
    products = client.get("/api/products").json()
    prod = next((p for p in products if p["total_stock"] >= 10.0 and len(p["locations_stock"]) > 0), None)
    assert prod is not None

    locs = client.get("/api/locations?internal_only=true").json()
    src_loc = locs[0]
    dst_loc = locs[1]

    # Ensure source has stock
    initial_company_total = prod["total_stock"]
    src_before = next((l["quantity"] for l in prod["locations_stock"] if l["location_id"] == src_loc["id"]), 0.0)

    # If src_loc has 0, pick a location that has stock
    if src_before < 5.0:
        src_loc = next(l for l in locs if l["id"] == prod["locations_stock"][0]["location_id"])
        dst_loc = next(l for l in locs if l["id"] != src_loc["id"])
        src_before = prod["locations_stock"][0]["quantity"]

    move_qty = 5.0
    transfer_payload = {
        "operation_type": "INTERNAL_TRANSFER",
        "source_location_id": src_loc["id"],
        "destination_location_id": dst_loc["id"],
        "notes": f"Internal transfer: {src_loc['name']} -> {dst_loc['name']}",
        "items": [
            {"product_id": prod["id"], "demanded_qty": move_qty, "done_qty": move_qty}
        ]
    }
    op = client.post("/api/operations", json=transfer_payload).json()
    assert op["operation_type"] == "INTERNAL_TRANSFER"

    # Validate Transfer
    res_val = client.post(f"/api/operations/{op['id']}/validate")
    assert res_val.status_code == 200

    # Invariance check: Company Total Stock MUST REMAIN IDENTICAL
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    assert prod_after["total_stock"] == initial_company_total

    # Source decreased, Destination increased
    src_after = next((l["quantity"] for l in prod_after["locations_stock"] if l["location_id"] == src_loc["id"]), 0.0)
    assert src_after == src_before - move_qty

    # Move History (Stock Ledger) logged
    ledger = client.get(f"/api/ledger?product_id={prod['id']}").json()
    latest_transfer = ledger[0]
    assert latest_transfer["operation_type"] == "INTERNAL_TRANSFER"
    assert latest_transfer["source_location_name"] == src_loc["name"]
    assert latest_transfer["destination_location_name"] == dst_loc["name"]

def test_internal_transfer_edge_cases():
    """Edge Case: Source location equals Destination location must be rejected."""
    locs = client.get("/api/locations?internal_only=true").json()
    same_loc_id = locs[0]["id"]
    prod = client.get("/api/products").json()[0]

    res = client.post("/api/operations", json={
        "operation_type": "INTERNAL_TRANSFER",
        "source_location_id": same_loc_id,
        "destination_location_id": same_loc_id,
        "items": [{"product_id": prod["id"], "demanded_qty": 5.0}]
    })
    assert res.status_code == 400
    assert "cannot be the same" in res.json()["detail"]


# ==============================================================================
# 6. STOCK ADJUSTMENTS (PDF Page 3)
# ==============================================================================

def test_stock_adjustments_reconciliation():
    """
    Fix mismatches between:
    1. Recorded stock
    2. Physical count
    Steps: Select product/location -> Enter counted quantity -> System auto-updates and logs adjustment.
    """
    prod = client.get("/api/products").json()[0]
    loc = client.get("/api/locations?internal_only=true").json()[0]

    # Reconcile to exactly 88.0 units
    target_count = 88.0
    res_adj = client.post("/api/adjustments", json={
        "product_id": prod["id"],
        "location_id": loc["id"],
        "counted_qty": target_count,
        "notes": "Physical inventory cycle count"
    })
    assert res_adj.status_code == 200
    adj_op = res_adj.json()
    assert adj_op["status"] == "DONE"

    # Verify physical quant updated
    prod_after = client.get(f"/api/products/{prod['id']}").json()
    matching_loc = next(l for l in prod_after["locations_stock"] if l["location_id"] == loc["id"])
    assert matching_loc["quantity"] == target_count

    # Verify adjustment in Stock Ledger
    ledger = client.get(f"/api/ledger?product_id={prod['id']}").json()
    assert ledger[0]["operation_type"] == "ADJUSTMENT"
    assert ledger[0]["resulting_balance"] == target_count

def test_stock_adjustment_negative_count_edge_case():
    """Edge Case: Physical counted quantity cannot be negative."""
    prod = client.get("/api/products").json()[0]
    loc = client.get("/api/locations?internal_only=true").json()[0]

    res = client.post("/api/adjustments", json={
        "product_id": prod["id"],
        "location_id": loc["id"],
        "counted_qty": -5.0,
        "notes": "Invalid negative count"
    })
    assert res.status_code == 400
    assert "cannot be negative" in res.json()["detail"]


# ==============================================================================
# 7. DASHBOARD KPIS & DYNAMIC FILTERS (PDF Page 1)
# ==============================================================================

def test_dashboard_kpis_and_dynamic_filters():
    """
    Dashboard KPIs:
    - Total Products in Stock
    - Low Stock / Out of Stock Items
    - Pending Receipts
    - Pending Deliveries
    - Internal Transfers Scheduled
    Dynamic Filters:
    - By document type: Receipts / Delivery / Internal / Adjustments
    - By status: Draft, Waiting, Ready, Done, Canceled
    - By warehouse or location
    - By product category
    """
    res_kpis = client.get("/api/dashboard/kpis")
    assert res_kpis.status_code == 200
    kpis = res_kpis.json()["kpis"]
    assert kpis["total_products_in_stock"] >= 6
    assert "low_stock_items_count" in kpis
    assert "pending_receipts_count" in kpis
    assert "pending_deliveries_count" in kpis
    assert "internal_transfers_scheduled_count" in kpis

    # Filter operations by type: RECEIPT
    res_rec = client.get("/api/operations?operation_type=RECEIPT")
    assert res_rec.status_code == 200
    for op in res_rec.json():
        assert op["operation_type"] == "RECEIPT"

    # Filter operations by status: READY
    res_ready = client.get("/api/operations?status=READY")
    assert res_ready.status_code == 200
    for op in res_ready.json():
        assert op["status"] == "READY"


# ==============================================================================
# 8. MULTI-WAREHOUSE MANAGEMENT (PDF Page 2 & Page 3)
# ==============================================================================

def test_multi_warehouse_support():
    """Multi-warehouse support: create and list facilities and rack locations."""
    # List warehouses
    res_whs = client.get("/api/warehouses")
    assert res_whs.status_code == 200
    assert len(res_whs.json()) >= 2

    # Create 3rd Warehouse with unique code
    uid = uuid.uuid4().hex[:4]
    wh_code = f"WH-N-{uid}"
    res_new_wh = client.post("/api/warehouses", json={
        "code": wh_code,
        "name": f"North Regional Distribution Center {uid}",
        "address": "Highway 45 North Logistics Corridor, Dock 8"
    })
    assert res_new_wh.status_code == 200
    wh3 = res_new_wh.json()

    # Create Rack location in Warehouse 3
    res_loc = client.post("/api/locations", json={
        "warehouse_id": wh3["id"],
        "code": f"LOC-WH3-RACK-{uid}",
        "name": "WH3 Aisle 1 High-Bay Rack",
        "location_type": "INTERNAL"
    })
    assert res_loc.status_code == 200
    assert res_loc.json()["code"] == f"LOC-WH3-RACK-{uid}"


# ==============================================================================
# 9. SIMPLIFIED EXAMPLE FLOW FROM PDF PAGE 3 & 4
# ==============================================================================

def test_simplified_example_flow_from_pdf():
    """
    Step 1: Receive Goods from Vendor: Receive 100 kg Steel -> Stock: +100
    Step 2: Move to production rack: Internal transfer: Main Store -> Production Rack (net total unchanged)
    Step 3: Deliver finished goods: Deliver 20 steel -> Stock: -20
    Step 4: Adjust damaged items: 3 kg steel damaged -> Stock: -3
    Everything logged in the Stock Ledger.
    """
    res_demo = client.post("/api/demo/run-scenario")
    assert res_demo.status_code == 200
    data = res_demo.json()
    assert data["status"] == "success"
    assert len(data["steps"]) == 4

    # Step 1: Vendor intake (+100)
    assert data["steps"][0]["step"] == 1
    assert "+100" in data["steps"][0]["stock_change"]

    # Step 2: Internal move to production rack
    assert data["steps"][1]["step"] == 2
    assert "unchanged" in data["steps"][1]["stock_change"]

    # Step 3: Deliver finished goods (-20)
    assert data["steps"][2]["step"] == 3
    assert "-20" in data["steps"][2]["stock_change"]

    # Step 4: Adjust damaged items (-3)
    assert data["steps"][3]["step"] == 4
    assert "-3" in data["steps"][3]["stock_change"]

    # Verify that each step has a distinct reference logged in the ledger
    ledger_entries = client.get("/api/ledger").json()
    demo_refs = [s["reference"] for s in data["steps"]]
    found_refs = [e["reference_number"] for e in ledger_entries if e["reference_number"] in demo_refs]
    assert len(found_refs) == 4
