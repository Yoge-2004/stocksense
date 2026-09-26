from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi import HTTPException, status

from app.models import (
    Product, ProductCategory, StockQuant, Location, LocationType,
    StockOperation, OperationType, OperationStatus, OperationItem,
    StockLedgerEntry, User, Warehouse, utcnow
)
from app.schemas import (
    OperationCreate, StockAdjustmentCreate, ProductCreate, ProductUpdate
)

def get_virtual_location(db: Session, loc_type: LocationType) -> Location:
    """Retrieve or create a system virtual location (Vendor, Customer, Adjustment)."""
    loc = db.query(Location).filter(Location.location_type == loc_type).first()
    if not loc:
        code_map = {
            LocationType.VENDOR: "LOC-VIRTUAL-VENDOR",
            LocationType.CUSTOMER: "LOC-VIRTUAL-CUSTOMER",
            LocationType.ADJUSTMENT: "LOC-VIRTUAL-ADJ"
        }
        name_map = {
            LocationType.VENDOR: "Vendors / Suppliers (External)",
            LocationType.CUSTOMER: "Customers / Dispatch (External)",
            LocationType.ADJUSTMENT: "Inventory Discrepancy & Scrap"
        }
        loc = Location(
            warehouse_id=None,
            code=code_map.get(loc_type, f"LOC-{loc_type.value}"),
            name=name_map.get(loc_type, loc_type.value),
            location_type=loc_type
        )
        db.add(loc)
        db.flush()
    return loc

def get_default_internal_location(db: Session) -> Location:
    """Gets the default primary internal warehouse location (e.g. Main Store)."""
    loc = db.query(Location).filter(
        Location.location_type == LocationType.INTERNAL,
        Location.code == "LOC-MAIN-STORE"
    ).first()
    if not loc:
        loc = db.query(Location).filter(Location.location_type == LocationType.INTERNAL).first()
    if not loc:
        # Create a default main store location
        loc = Location(
            warehouse_id=None,
            code="LOC-MAIN-STORE",
            name="Main Store",
            location_type=LocationType.INTERNAL
        )
        db.add(loc)
        db.flush()
    return loc

def generate_reference_number(db: Session, op_type: OperationType) -> str:
    """Generates sequential collision-free reference number e.g. REC-2026-0001."""
    year = datetime.now().year
    prefix_map = {
        OperationType.RECEIPT: "REC",
        OperationType.DELIVERY: "DEL",
        OperationType.INTERNAL_TRANSFER: "INT",
        OperationType.ADJUSTMENT: "ADJ"
    }
    prefix = prefix_map.get(op_type, "OP")
    max_id = db.query(func.max(StockOperation.id)).scalar() or 0
    candidate_num = max_id + 1
    while True:
        ref = f"{prefix}-{year}-{candidate_num:04d}"
        if not db.query(StockOperation).filter(StockOperation.reference_number == ref).first():
            return ref
        candidate_num += 1

def get_or_create_quant(db: Session, product_id: int, location_id: int) -> StockQuant:
    """Finds or creates a StockQuant for product and location."""
    quant = db.query(StockQuant).filter(
        StockQuant.product_id == product_id,
        StockQuant.location_id == location_id
    ).first()
    if not quant:
        quant = StockQuant(
            product_id=product_id,
            location_id=location_id,
            quantity=0.0,
            reserved_qty=0.0
        )
        db.add(quant)
        db.flush()
    return quant

def get_product_stock_summary(db: Session, product: Product) -> Dict[str, Any]:
    """Calculates total stock across internal locations, low stock status, and breakdown per location."""
    internal_types = [LocationType.INTERNAL, LocationType.PRODUCTION]
    quants = db.query(StockQuant).join(Location).filter(
        StockQuant.product_id == product.id,
        Location.location_type.in_(internal_types)
    ).all()

    total_stock = sum(q.quantity for q in quants)
    is_low_stock = total_stock <= product.min_reorder_qty and total_stock > 0
    is_out_of_stock = total_stock <= 0

    locations_detail = []
    for q in quants:
        locations_detail.append({
            "location_id": q.location_id,
            "location_code": q.location.code,
            "location_name": q.location.name,
            "warehouse_name": q.location.warehouse.name if q.location.warehouse else "Central Facility",
            "quantity": q.quantity
        })

    return {
        "total_stock": total_stock,
        "is_low_stock": is_low_stock,
        "is_out_of_stock": is_out_of_stock,
        "locations_stock": locations_detail
    }

def create_product(db: Session, prod_data: ProductCreate) -> Product:
    """Create a new product with optional initial stock and location quant."""
    existing = db.query(Product).filter(Product.sku == prod_data.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{prod_data.sku}' already exists."
        )

    if prod_data.initial_stock and prod_data.initial_stock < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Initial stock cannot be negative.")
    if prod_data.min_reorder_qty < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minimum reorder quantity cannot be negative.")
    if prod_data.cost_price < 0 or prod_data.selling_price < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prices cannot be negative.")

    product = Product(
        sku=prod_data.sku.strip(),
        name=prod_data.name.strip(),
        description=prod_data.description,
        category_id=prod_data.category_id,
        uom=prod_data.uom,
        min_reorder_qty=prod_data.min_reorder_qty,
        max_target_qty=prod_data.max_target_qty,
        cost_price=prod_data.cost_price,
        selling_price=prod_data.selling_price
    )
    db.add(product)
    db.flush()

    # Handle initial stock if provided
    if prod_data.initial_stock and prod_data.initial_stock > 0:
        target_loc_id = prod_data.initial_location_id
        if not target_loc_id:
            default_loc = get_default_internal_location(db)
            target_loc_id = default_loc.id

        quant = get_or_create_quant(db, product.id, target_loc_id)
        quant.quantity += prod_data.initial_stock

        vendor_loc = get_virtual_location(db, LocationType.VENDOR)
        # Log initial stock intake in the stock ledger
        ledger = StockLedgerEntry(
            reference_number=f"INIT-{product.sku}",
            operation_type=OperationType.RECEIPT,
            product_id=product.id,
            source_location_id=vendor_loc.id,
            destination_location_id=target_loc_id,
            quantity_change=prod_data.initial_stock,
            resulting_balance=quant.quantity,
            notes=f"Initial stock creation for {product.name}"
        )
        db.add(ledger)

    db.commit()
    db.refresh(product)
    return product

def create_stock_operation(db: Session, op_data: OperationCreate, user_id: Optional[int] = None) -> StockOperation:
    """Creates a stock operation (Receipt, Delivery, or Internal Transfer)."""
    if not op_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation must contain at least one product item."
        )

    src_id = op_data.source_location_id
    dst_id = op_data.destination_location_id

    # Handle defaults based on operation type
    if op_data.operation_type == OperationType.RECEIPT:
        if not src_id:
            src_id = get_virtual_location(db, LocationType.VENDOR).id
        if not dst_id:
            dst_id = get_default_internal_location(db).id

    elif op_data.operation_type == OperationType.DELIVERY:
        if not src_id:
            src_id = get_default_internal_location(db).id
        if not dst_id:
            dst_id = get_virtual_location(db, LocationType.CUSTOMER).id

    elif op_data.operation_type == OperationType.INTERNAL_TRANSFER:
        if not src_id or not dst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both source and destination locations are required for Internal Transfers."
            )
        if src_id == dst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source and destination locations cannot be the same."
            )

    ref = generate_reference_number(db, op_data.operation_type)

    op = StockOperation(
        reference_number=ref,
        operation_type=op_data.operation_type,
        status=OperationStatus.READY,
        source_location_id=src_id,
        destination_location_id=dst_id,
        partner_name=op_data.partner_name,
        notes=op_data.notes,
        created_by_id=user_id
    )
    db.add(op)
    db.flush()

    for item in op_data.items:
        if item.demanded_qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Demanded quantity must be strictly positive."
            )
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {item.product_id} not found."
            )
        op_item = OperationItem(
            operation_id=op.id,
            product_id=item.product_id,
            demanded_qty=item.demanded_qty,
            done_qty=item.done_qty if item.done_qty else item.demanded_qty
        )
        db.add(op_item)

    db.commit()
    db.refresh(op)
    return op

def validate_operation(db: Session, operation_id: int, user_id: Optional[int] = None) -> StockOperation:
    """
    Validates an operation and executes real-time stock balance updates + double-entry ledger logging.
    """
    op = db.query(StockOperation).filter(StockOperation.id == operation_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found.")

    if op.status == OperationStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation has already been validated and completed."
        )
    if op.status == OperationStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot validate a canceled operation."
        )

    # 1. RECEIPT: Increases stock at destination location
    if op.operation_type == OperationType.RECEIPT:
        for item in op.items:
            qty_to_add = item.done_qty if item.done_qty > 0 else item.demanded_qty
            item.done_qty = qty_to_add

            quant = get_or_create_quant(db, item.product_id, op.destination_location_id)
            quant.quantity += qty_to_add

            # Add to Stock Ledger
            ledger = StockLedgerEntry(
                reference_number=op.reference_number,
                operation_type=OperationType.RECEIPT,
                product_id=item.product_id,
                source_location_id=op.source_location_id,
                destination_location_id=op.destination_location_id,
                quantity_change=qty_to_add,
                resulting_balance=quant.quantity,
                created_by_id=user_id or op.created_by_id,
                notes=f"Receipt from {op.partner_name or 'Supplier'} validated"
            )
            db.add(ledger)

    # 2. DELIVERY: Decreases stock from source location
    elif op.operation_type == OperationType.DELIVERY:
        # First verify stock availability
        for item in op.items:
            qty_to_remove = item.done_qty if item.done_qty > 0 else item.demanded_qty
            quant = get_or_create_quant(db, item.product_id, op.source_location_id)
            if quant.quantity < qty_to_remove:
                product_name = item.product.name if item.product else f"Product ID {item.product_id}"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{product_name}'. Available: {quant.quantity}, Requested: {qty_to_remove}."
                )

        # Deduct stock and write ledger entries
        for item in op.items:
            qty_to_remove = item.done_qty if item.done_qty > 0 else item.demanded_qty
            item.done_qty = qty_to_remove

            quant = get_or_create_quant(db, item.product_id, op.source_location_id)
            quant.quantity -= qty_to_remove

            ledger = StockLedgerEntry(
                reference_number=op.reference_number,
                operation_type=OperationType.DELIVERY,
                product_id=item.product_id,
                source_location_id=op.source_location_id,
                destination_location_id=op.destination_location_id,
                quantity_change=-qty_to_remove,
                resulting_balance=quant.quantity,
                created_by_id=user_id or op.created_by_id,
                notes=f"Delivery to {op.partner_name or 'Customer'} dispatched"
            )
            db.add(ledger)

        op.is_picked = True
        op.is_packed = True

    # 3. INTERNAL TRANSFER: Moves stock between locations (overall company stock unchanged)
    elif op.operation_type == OperationType.INTERNAL_TRANSFER:
        # Verify source stock
        for item in op.items:
            qty_to_move = item.done_qty if item.done_qty > 0 else item.demanded_qty
            src_quant = get_or_create_quant(db, item.product_id, op.source_location_id)
            if src_quant.quantity < qty_to_move:
                product_name = item.product.name if item.product else f"Product ID {item.product_id}"
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock in source location for '{product_name}'. Available: {src_quant.quantity}, Moving: {qty_to_move}."
                )

        for item in op.items:
            qty_to_move = item.done_qty if item.done_qty > 0 else item.demanded_qty
            item.done_qty = qty_to_move

            src_quant = get_or_create_quant(db, item.product_id, op.source_location_id)
            dst_quant = get_or_create_quant(db, item.product_id, op.destination_location_id)

            src_quant.quantity -= qty_to_move
            dst_quant.quantity += qty_to_move

            ledger = StockLedgerEntry(
                reference_number=op.reference_number,
                operation_type=OperationType.INTERNAL_TRANSFER,
                product_id=item.product_id,
                source_location_id=op.source_location_id,
                destination_location_id=op.destination_location_id,
                quantity_change=qty_to_move,
                resulting_balance=dst_quant.quantity,
                created_by_id=user_id or op.created_by_id,
                notes=f"Internal transfer from {op.source_location.name} to {op.destination_location.name}"
            )
            db.add(ledger)

    op.status = OperationStatus.DONE
    op.validated_at = utcnow()
    db.commit()
    db.refresh(op)
    return op

def step_delivery_order(db: Session, operation_id: int, step: str) -> StockOperation:
    """Updates delivery order picking or packing status."""
    op = db.query(StockOperation).filter(StockOperation.id == operation_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found.")
    if op.operation_type != OperationType.DELIVERY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Step action only applies to Delivery Orders.")
    if op.status == OperationStatus.DONE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter an already completed delivery order.")
    if op.status == OperationStatus.CANCELED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot alter a canceled delivery order.")

    if step == "pick":
        op.is_picked = True
        op.status = OperationStatus.WAITING
    elif step == "pack":
        op.is_packed = True
        op.status = OperationStatus.READY
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid delivery step. Choose 'pick' or 'pack'.")

    db.commit()
    db.refresh(op)
    return op

def execute_stock_adjustment(
    db: Session,
    adj_data: StockAdjustmentCreate,
    user_id: Optional[int] = None
) -> StockOperation:
    """
    Executes a stock adjustment:
    - Compares recorded quantity with counted physical quantity.
    - Updates stock quant to the physical count.
    - Logs the adjustment in Stock Ledger.
    """
    if adj_data.counted_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Physical counted stock quantity cannot be negative."
        )

    prod = db.query(Product).filter(Product.id == adj_data.product_id).first()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    loc = db.query(Location).filter(Location.id == adj_data.location_id).first()
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")

    quant = get_or_create_quant(db, adj_data.product_id, adj_data.location_id)
    recorded_qty = quant.quantity
    counted_qty = adj_data.counted_qty
    difference = counted_qty - recorded_qty

    ref = generate_reference_number(db, OperationType.ADJUSTMENT)
    adj_virtual_loc = get_virtual_location(db, LocationType.ADJUSTMENT)

    # Determine virtual move direction
    if difference >= 0:
        src_id = adj_virtual_loc.id
        dst_id = loc.id
    else:
        src_id = loc.id
        dst_id = adj_virtual_loc.id

    op = StockOperation(
        reference_number=ref,
        operation_type=OperationType.ADJUSTMENT,
        status=OperationStatus.DONE,
        source_location_id=src_id,
        destination_location_id=dst_id,
        notes=adj_data.notes or f"Physical count adjustment: {recorded_qty} -> {counted_qty} (diff: {difference:+.2f})",
        created_by_id=user_id,
        validated_at=utcnow()
    )
    db.add(op)
    db.flush()

    item = OperationItem(
        operation_id=op.id,
        product_id=prod.id,
        demanded_qty=abs(difference),
        done_qty=difference,
        counted_qty=counted_qty
    )
    db.add(item)

    # Update quant to counted quantity
    quant.quantity = counted_qty

    # Record in ledger
    ledger = StockLedgerEntry(
        reference_number=ref,
        operation_type=OperationType.ADJUSTMENT,
        product_id=prod.id,
        source_location_id=src_id,
        destination_location_id=dst_id,
        quantity_change=difference,
        resulting_balance=counted_qty,
        created_by_id=user_id,
        notes=f"Stock adjustment for {prod.name}: recorded={recorded_qty}, counted={counted_qty}"
    )
    db.add(ledger)

    db.commit()
    db.refresh(op)
    return op

def get_dashboard_kpis(
    db: Session,
    doc_type: Optional[OperationType] = None,
    op_status: Optional[OperationStatus] = None,
    warehouse_id: Optional[int] = None,
    category_id: Optional[int] = None
) -> Dict[str, Any]:
    """Calculates all 5 Dashboard KPIs and analytics with dynamic filters."""
    # 1. Total Products
    prod_query = db.query(Product).filter(Product.is_active == True)
    if category_id:
        prod_query = prod_query.filter(Product.category_id == category_id)
    total_products = prod_query.count()

    # 2. Low Stock & Out of Stock counts
    all_products = prod_query.all()
    low_stock_count = 0
    out_of_stock_count = 0
    low_stock_list = []

    for p in all_products:
        summary = get_product_stock_summary(db, p)
        if summary["is_out_of_stock"]:
            out_of_stock_count += 1
            low_stock_list.append(p)
        elif summary["is_low_stock"]:
            low_stock_count += 1
            low_stock_list.append(p)

    # Operations query
    ops_base = db.query(StockOperation)
    if doc_type:
        ops_base = ops_base.filter(StockOperation.operation_type == doc_type)
    if op_status:
        ops_base = ops_base.filter(StockOperation.status == op_status)

    pending_statuses = [OperationStatus.DRAFT, OperationStatus.WAITING, OperationStatus.READY]

    # 3. Pending Receipts
    pending_receipts = db.query(StockOperation).filter(
        StockOperation.operation_type == OperationType.RECEIPT,
        StockOperation.status.in_(pending_statuses)
    ).count()

    # 4. Pending Deliveries
    pending_deliveries = db.query(StockOperation).filter(
        StockOperation.operation_type == OperationType.DELIVERY,
        StockOperation.status.in_(pending_statuses)
    ).count()

    # 5. Scheduled Internal Transfers
    pending_transfers = db.query(StockOperation).filter(
        StockOperation.operation_type == OperationType.INTERNAL_TRANSFER,
        StockOperation.status.in_(pending_statuses)
    ).count()

    # Category breakdown for charts
    categories = db.query(ProductCategory).all()
    breakdown = []
    for cat in categories:
        cat_products = db.query(Product).filter(Product.category_id == cat.id, Product.is_active == True).all()
        cat_total_qty = 0.0
        for cp in cat_products:
            summ = get_product_stock_summary(db, cp)
            cat_total_qty += summ["total_stock"]
        breakdown.append({
            "category_name": cat.name,
            "item_count": len(cat_products),
            "total_quantity": round(cat_total_qty, 2)
        })

    return {
        "kpis": {
            "total_products_in_stock": total_products,
            "low_stock_items_count": low_stock_count,
            "out_of_stock_items_count": out_of_stock_count,
            "pending_receipts_count": pending_receipts,
            "pending_deliveries_count": pending_deliveries,
            "internal_transfers_scheduled_count": pending_transfers
        },
        "category_breakdown": breakdown,
        "low_stock_alerts_count": len(low_stock_list)
    }
