from datetime import datetime, timezone, timedelta
from app.database import SessionLocal, engine, Base
from app.models import (
    User, UserRole, Warehouse, Location, LocationType,
    ProductCategory, Product, StockQuant,
    StockOperation, OperationType, OperationStatus, OperationItem,
    StockLedgerEntry
)
from app.security import hash_password

def seed_database():
    """Initializes tables and seeds initial realistic dataset matching problem statement."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already contains records. Skipping seed.")
            return

        print("Seeding StockSense database...")

        # 1. Users
        manager = User(
            username="manager",
            email="manager@stocksense.io",
            full_name="Alex Rivera",
            hashed_password=hash_password("password123"),
            role=UserRole.INVENTORY_MANAGER,
            is_active=True
        )
        staff = User(
            username="staff",
            email="staff@stocksense.io",
            full_name="Sam Morgan",
            hashed_password=hash_password("password123"),
            role=UserRole.WAREHOUSE_STAFF,
            is_active=True
        )
        admin = User(
            username="admin",
            email="admin@stocksense.io",
            full_name="Yogeshwaran M (Admin)",
            hashed_password=hash_password("password123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add_all([manager, staff, admin])
        db.flush()

        # 2. Warehouses
        wh_main = Warehouse(
            code="WH-MAIN",
            name="Main Warehouse",
            address="Industrial Zone Sector 4, Bay 12",
            is_active=True
        )
        wh_sec = Warehouse(
            code="WH-LOG2",
            name="Warehouse 2 (Logistics Hub)",
            address="Freight Cargo Terminal East, Gate 3",
            is_active=True
        )
        db.add_all([wh_main, wh_sec])
        db.flush()

        # 3. Locations
        loc_main_store = Location(
            warehouse_id=wh_main.id,
            code="LOC-MAIN-STORE",
            name="Main Store",
            location_type=LocationType.INTERNAL
        )
        loc_prod_floor = Location(
            warehouse_id=wh_main.id,
            code="LOC-PROD-FLOOR",
            name="Production Floor / Rack",
            location_type=LocationType.PRODUCTION
        )
        loc_rack_a = Location(
            warehouse_id=wh_main.id,
            code="LOC-RACK-A",
            name="Rack A",
            location_type=LocationType.INTERNAL
        )
        loc_rack_b = Location(
            warehouse_id=wh_main.id,
            code="LOC-RACK-B",
            name="Rack B",
            location_type=LocationType.INTERNAL
        )
        loc_wh2_bay = Location(
            warehouse_id=wh_sec.id,
            code="LOC-WH2-BAY1",
            name="Warehouse 2 Bay 1",
            location_type=LocationType.INTERNAL
        )

        # Virtual Locations
        loc_vendor = Location(
            warehouse_id=None,
            code="LOC-VIRTUAL-VENDOR",
            name="Vendors / Suppliers (External)",
            location_type=LocationType.VENDOR
        )
        loc_customer = Location(
            warehouse_id=None,
            code="LOC-VIRTUAL-CUSTOMER",
            name="Customers / Dispatch (External)",
            location_type=LocationType.CUSTOMER
        )
        loc_adjustment = Location(
            warehouse_id=None,
            code="LOC-VIRTUAL-ADJ",
            name="Inventory Scraps & Adjustments",
            location_type=LocationType.ADJUSTMENT
        )

        db.add_all([
            loc_main_store, loc_prod_floor, loc_rack_a, loc_rack_b,
            loc_wh2_bay, loc_vendor, loc_customer, loc_adjustment
        ])
        db.flush()

        # 4. Product Categories
        cat_raw = ProductCategory(name="Raw Materials", description="Metals, sheets, structural inputs")
        cat_finished = ProductCategory(name="Finished Goods", description="Manufactured and ready-for-sale goods")
        cat_fasteners = ProductCategory(name="Fasteners & Hardware", description="Bolts, nuts, brackets and fittings")
        cat_electronics = ProductCategory(name="Warehouse Electronics", description="Sensors, gateways, tracking beacons")

        db.add_all([cat_raw, cat_finished, cat_fasteners, cat_electronics])
        db.flush()

        # 5. Products (Matching problem statement examples)
        prod_steel = Product(
            sku="RAW-STL-001",
            name="Steel Rods (High Tensile)",
            description="10mm x 6m structural grade steel rods",
            category_id=cat_raw.id,
            uom="kg",
            min_reorder_qty=50.0,
            max_target_qty=500.0,
            cost_price=3.50,
            selling_price=5.20
        )
        prod_chairs = Product(
            sku="FG-CHR-002",
            name="Ergonomic Workstation Chairs",
            description="Adjustable mesh office chairs with lumbar support",
            category_id=cat_finished.id,
            uom="units",
            min_reorder_qty=15.0,
            max_target_qty=100.0,
            cost_price=45.00,
            selling_price=85.00
        )
        prod_frames = Product(
            sku="FG-FRM-003",
            name="Steel Frames",
            description="Welded modular steel chassis frames",
            category_id=cat_finished.id,
            uom="units",
            min_reorder_qty=20.0,
            max_target_qty=200.0,
            cost_price=18.00,
            selling_price=32.00
        )
        prod_fasteners = Product(
            sku="FST-BLT-004",
            name="Industrial Bolts & Fasteners (M8)",
            description="Pack of 100 zinc-plated grade 8.8 bolts",
            category_id=cat_fasteners.id,
            uom="boxes",
            min_reorder_qty=25.0,  # Below threshold to show LOW STOCK warning
            max_target_qty=150.0,
            cost_price=8.00,
            selling_price=14.00
        )
        prod_aluminum = Product(
            sku="RAW-ALU-005",
            name="Aluminum Sheets (2mm)",
            description="Corrosion resistant 4x8 ft aluminum sheet",
            category_id=cat_raw.id,
            uom="m2",
            min_reorder_qty=30.0,  # 0 stock to show OUT OF STOCK warning
            max_target_qty=250.0,
            cost_price=22.00,
            selling_price=38.00
        )
        prod_sensors = Product(
            sku="ELC-SNS-006",
            name="IoT Warehouse Environmental Sensors",
            description="BLE temperature, humidity and vibration tracker",
            category_id=cat_electronics.id,
            uom="units",
            min_reorder_qty=10.0,
            max_target_qty=100.0,
            cost_price=15.00,
            selling_price=29.00
        )

        db.add_all([prod_steel, prod_chairs, prod_frames, prod_fasteners, prod_aluminum, prod_sensors])
        db.flush()

        # 6. Initial Stock Quants & Ledger History
        # Steel in Main Store (100 kg)
        q1 = StockQuant(product_id=prod_steel.id, location_id=loc_main_store.id, quantity=100.0)
        # Chairs in Main Store (35 units)
        q2 = StockQuant(product_id=prod_chairs.id, location_id=loc_main_store.id, quantity=35.0)
        # Steel frames in Main Store (45 units)
        q3 = StockQuant(product_id=prod_frames.id, location_id=loc_main_store.id, quantity=45.0)
        # Fasteners in Rack A (8 boxes - LOW STOCK alert triggers)
        q4 = StockQuant(product_id=prod_fasteners.id, location_id=loc_rack_a.id, quantity=8.0)
        # Aluminum Sheets (0 stock - OUT OF STOCK alert triggers)
        q5 = StockQuant(product_id=prod_aluminum.id, location_id=loc_main_store.id, quantity=0.0)
        # Sensors in Rack B (50 units)
        q6 = StockQuant(product_id=prod_sensors.id, location_id=loc_rack_b.id, quantity=50.0)

        db.add_all([q1, q2, q3, q4, q5, q6])
        db.flush()

        # Initial Ledger Entries
        now = datetime.now(timezone.utc)
        ledger_init_1 = StockLedgerEntry(
            timestamp=now - timedelta(days=2),
            reference_number="REC-2026-0000",
            operation_type=OperationType.RECEIPT,
            product_id=prod_steel.id,
            source_location_id=loc_vendor.id,
            destination_location_id=loc_main_store.id,
            quantity_change=100.0,
            resulting_balance=100.0,
            created_by_id=manager.id,
            notes="Initial vendor receipt of 100 kg Steel from MetalCorp"
        )
        ledger_init_2 = StockLedgerEntry(
            timestamp=now - timedelta(days=1),
            reference_number="REC-2026-0001",
            operation_type=OperationType.RECEIPT,
            product_id=prod_chairs.id,
            source_location_id=loc_vendor.id,
            destination_location_id=loc_main_store.id,
            quantity_change=35.0,
            resulting_balance=35.0,
            created_by_id=manager.id,
            notes="Initial stock intake - Ergonomic Chairs"
        )
        db.add_all([ledger_init_1, ledger_init_2])

        # 7. Sample Pending Operations (to populate Dashboard KPIs)
        # Pending Receipt
        op_rec = StockOperation(
            reference_number="REC-2026-0002",
            operation_type=OperationType.RECEIPT,
            status=OperationStatus.READY,
            source_location_id=loc_vendor.id,
            destination_location_id=loc_main_store.id,
            partner_name="Apex Metallurgical Supplies Ltd",
            notes="Incoming batch of 50 units steel rods for production",
            created_by_id=manager.id
        )
        db.add(op_rec)
        db.flush()

        item_rec = OperationItem(
            operation_id=op_rec.id,
            product_id=prod_steel.id,
            demanded_qty=50.0,
            done_qty=50.0
        )
        db.add(item_rec)

        # Pending Delivery Order
        op_del = StockOperation(
            reference_number="DEL-2026-0001",
            operation_type=OperationType.DELIVERY,
            status=OperationStatus.WAITING,
            source_location_id=loc_main_store.id,
            destination_location_id=loc_customer.id,
            partner_name="Apex Workspaces Inc.",
            notes="Customer sales order for 10 ergonomic chairs",
            created_by_id=manager.id,
            is_picked=False,
            is_packed=False
        )
        db.add(op_del)
        db.flush()

        item_del = OperationItem(
            operation_id=op_del.id,
            product_id=prod_chairs.id,
            demanded_qty=10.0,
            done_qty=0.0
        )
        db.add(item_del)

        # Scheduled Internal Transfer
        op_trans = StockOperation(
            reference_number="INT-2026-0001",
            operation_type=OperationType.INTERNAL_TRANSFER,
            status=OperationStatus.READY,
            source_location_id=loc_main_store.id,
            destination_location_id=loc_prod_floor.id,
            notes="Transfer steel rods from Main Store to Production Rack for fabrication",
            created_by_id=staff.id
        )
        db.add(op_trans)
        db.flush()

        item_trans = OperationItem(
            operation_id=op_trans.id,
            product_id=prod_steel.id,
            demanded_qty=25.0,
            done_qty=25.0
        )
        db.add(item_trans)

        db.commit()
        print("StockSense database successfully initialized and seeded with rich dataset.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
