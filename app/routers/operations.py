from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import (
    StockOperation, OperationType, OperationStatus, OperationItem,
    Location, Product, StockLedgerEntry
)
from app.schemas import (
    OperationCreate, OperationResponse, OperationItemResponse,
    StockAdjustmentCreate
)
from app.services.inventory_service import (
    create_stock_operation, validate_operation, step_delivery_order,
    execute_stock_adjustment, get_default_internal_location,
    get_virtual_location, LocationType, get_or_create_quant,
    generate_reference_number
)

router = APIRouter(prefix="/api", tags=["Operations"])

def format_op_response(op: StockOperation) -> OperationResponse:
    items = []
    for item in op.items:
        items.append(OperationItemResponse(
            id=item.id,
            operation_id=item.operation_id,
            product_id=item.product_id,
            demanded_qty=item.demanded_qty,
            done_qty=item.done_qty,
            counted_qty=item.counted_qty,
            product_name=item.product.name if item.product else None,
            product_sku=item.product.sku if item.product else None,
            product_uom=item.product.uom if item.product else None
        ))

    return OperationResponse(
        id=op.id,
        reference_number=op.reference_number,
        operation_type=op.operation_type,
        status=op.status,
        source_location_id=op.source_location_id,
        destination_location_id=op.destination_location_id,
        partner_name=op.partner_name,
        notes=op.notes,
        is_picked=op.is_picked,
        is_packed=op.is_packed,
        source_location_name=op.source_location.name if op.source_location else None,
        destination_location_name=op.destination_location.name if op.destination_location else None,
        created_by_name=op.created_by_user.full_name if op.created_by_user else "System",
        created_at=op.created_at,
        validated_at=op.validated_at,
        items=items
    )

@router.get("/operations", response_model=List[OperationResponse])
def get_operations(
    operation_type: Optional[OperationType] = None,
    status: Optional[OperationStatus] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List operations with dynamic multi-dimensional filters."""
    query = db.query(StockOperation)

    if operation_type:
        query = query.filter(StockOperation.operation_type == operation_type)
    if status:
        query = query.filter(StockOperation.status == status)
    if location_id:
        query = query.filter(
            or_(
                StockOperation.source_location_id == location_id,
                StockOperation.destination_location_id == location_id
            )
        )
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                StockOperation.reference_number.ilike(s),
                StockOperation.partner_name.ilike(s),
                StockOperation.notes.ilike(s)
            )
        )

    ops = query.order_by(StockOperation.id.desc()).all()
    return [format_op_response(op) for op in ops]

@router.get("/operations/{op_id}", response_model=OperationResponse)
def get_operation(op_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a single operation."""
    op = db.query(StockOperation).filter(StockOperation.id == op_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    return format_op_response(op)

@router.post("/operations", response_model=OperationResponse)
def create_operation_endpoint(op_data: OperationCreate, db: Session = Depends(get_db)):
    """Create a new operation (Receipt, Delivery, or Internal Transfer)."""
    op = create_stock_operation(db, op_data)
    return format_op_response(op)

@router.post("/operations/{op_id}/pick", response_model=OperationResponse)
def pick_delivery_endpoint(op_id: int, db: Session = Depends(get_db)):
    """Step 1 for Delivery Order: Pick items from shelves/warehouse."""
    op = step_delivery_order(db, op_id, "pick")
    return format_op_response(op)

@router.post("/operations/{op_id}/pack", response_model=OperationResponse)
def pack_delivery_endpoint(op_id: int, db: Session = Depends(get_db)):
    """Step 2 for Delivery Order: Pack items ready for shipping."""
    op = step_delivery_order(db, op_id, "pack")
    return format_op_response(op)

@router.post("/operations/{op_id}/validate", response_model=OperationResponse)
def validate_operation_endpoint(op_id: int, db: Session = Depends(get_db)):
    """
    Validate operation: Automatically increases/decreases stock and records to Stock Ledger.
    """
    op = validate_operation(db, op_id)
    return format_op_response(op)

@router.post("/operations/{op_id}/cancel", response_model=OperationResponse)
def cancel_operation_endpoint(op_id: int, db: Session = Depends(get_db)):
    """Cancel a draft or ready operation."""
    op = db.query(StockOperation).filter(StockOperation.id == op_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found.")
    if op.status == OperationStatus.DONE:
        raise HTTPException(status_code=400, detail="Cannot cancel an already completed operation.")

    op.status = OperationStatus.CANCELED
    db.commit()
    db.refresh(op)
    return format_op_response(op)

@router.post("/adjustments", response_model=OperationResponse)
def stock_adjustment_endpoint(adj_data: StockAdjustmentCreate, db: Session = Depends(get_db)):
    """
    Fix mismatches between recorded stock and physical count.
    Updates stock balance and logs to Stock Ledger.
    """
    op = execute_stock_adjustment(db, adj_data)
    return format_op_response(op)

@router.post("/demo/run-scenario")
def run_problem_statement_demo(db: Session = Depends(get_db)):
    """
    Executes the 4-step simplified scenario from the Problem Statement:
    Step 1: Receive 100 kg Steel from Vendor (Stock: +100)
    Step 2: Move to production rack (Main Store -> Production Rack, total stock unchanged)
    Step 3: Deliver finished goods (Deliver 20 steel -> Stock: -20)
    Step 4: Adjust damaged items (3 kg steel damaged -> Stock: -3)
    Everything logged in the Stock Ledger.
    """
    # 1. Identify or create Steel Rods product
    prod = db.query(Product).filter(Product.sku == "RAW-STL-001").first()
    if not prod:
        prod = db.query(Product).first()

    # Identify locations
    loc_main = db.query(Location).filter(Location.code == "LOC-MAIN-STORE").first() or get_default_internal_location(db)
    loc_prod = db.query(Location).filter(Location.code == "LOC-PROD-FLOOR").first()
    if not loc_prod:
        loc_prod = Location(code="LOC-PROD-FLOOR", name="Production Floor / Rack", location_type=LocationType.PRODUCTION)
        db.add(loc_prod)
        db.flush()

    loc_vendor = get_virtual_location(db, LocationType.VENDOR)
    loc_cust = get_virtual_location(db, LocationType.CUSTOMER)

    steps_log = []

    # --- Step 1: Receive 100 kg Steel from Vendor ---
    op1 = StockOperation(
        reference_number=generate_reference_number(db, OperationType.RECEIPT),
        operation_type=OperationType.RECEIPT,
        status=OperationStatus.READY,
        source_location_id=loc_vendor.id,
        destination_location_id=loc_main.id,
        partner_name="Demo Metal Vendor Ltd",
        notes="Step 1: Receive 100 kg Steel from Vendor"
    )
    db.add(op1)
    db.flush()
    db.add(OperationItem(operation_id=op1.id, product_id=prod.id, demanded_qty=100.0, done_qty=100.0))
    db.flush()
    validate_operation(db, op1.id)
    steps_log.append({
        "step": 1,
        "title": "Receive Goods from Vendor",
        "action": f"Received 100 {prod.uom} of {prod.name}",
        "stock_change": "+100",
        "location": loc_main.name,
        "reference": op1.reference_number
    })

    # --- Step 2: Internal transfer: Main Store -> Production Rack ---
    op2 = StockOperation(
        reference_number=generate_reference_number(db, OperationType.INTERNAL_TRANSFER),
        operation_type=OperationType.INTERNAL_TRANSFER,
        status=OperationStatus.READY,
        source_location_id=loc_main.id,
        destination_location_id=loc_prod.id,
        notes="Step 2: Move to production rack (Main Store -> Production Floor)"
    )
    db.add(op2)
    db.flush()
    db.add(OperationItem(operation_id=op2.id, product_id=prod.id, demanded_qty=50.0, done_qty=50.0))
    db.flush()
    validate_operation(db, op2.id)
    steps_log.append({
        "step": 2,
        "title": "Move to Production Rack",
        "action": f"Internal transfer: {loc_main.name} -> {loc_prod.name} (50 {prod.uom})",
        "stock_change": "Total unchanged (50 moved to Production Rack)",
        "reference": op2.reference_number
    })

    # --- Step 3: Deliver finished goods (Deliver 20 steel) ---
    op3 = StockOperation(
        reference_number=generate_reference_number(db, OperationType.DELIVERY),
        operation_type=OperationType.DELIVERY,
        status=OperationStatus.READY,
        source_location_id=loc_prod.id,
        destination_location_id=loc_cust.id,
        partner_name="Demo Industrial Client Corp",
        notes="Step 3: Deliver finished goods (20 units/kg)",
        is_picked=True,
        is_packed=True
    )
    db.add(op3)
    db.flush()
    db.add(OperationItem(operation_id=op3.id, product_id=prod.id, demanded_qty=20.0, done_qty=20.0))
    db.flush()
    validate_operation(db, op3.id)
    steps_log.append({
        "step": 3,
        "title": "Deliver Finished Goods",
        "action": f"Delivered 20 {prod.uom} of {prod.name} to client",
        "stock_change": "-20",
        "location": loc_prod.name,
        "reference": op3.reference_number
    })

    # --- Step 4: Adjust damaged items (3 kg damaged) ---
    # Current stock in production rack after -20 was 30. Damaged 3 => count is 27.
    q_prod = get_or_create_quant(db, prod.id, loc_prod.id)
    new_count = max(0.0, q_prod.quantity - 3.0)
    adj_req = StockAdjustmentCreate(
        product_id=prod.id,
        location_id=loc_prod.id,
        counted_qty=new_count,
        notes="Step 4: 3 kg damaged steel in production scrap adjustment"
    )
    op4 = execute_stock_adjustment(db, adj_req)
    steps_log.append({
        "step": 4,
        "title": "Adjust Damaged Items",
        "action": f"3 {prod.uom} damaged items registered in physical count reconciliation",
        "stock_change": "-3",
        "location": loc_prod.name,
        "reference": op4.reference_number
    })

    return {
        "status": "success",
        "message": "Complete 4-Step Problem Statement Demo Lifecycle Executed Successfully!",
        "steps": steps_log
    }
