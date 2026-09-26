from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StockLedgerEntry, OperationType
from app.schemas import StockLedgerResponse

router = APIRouter(prefix="/api/ledger", tags=["Move History (Stock Ledger)"])

@router.get("", response_model=List[StockLedgerResponse])
def get_stock_ledger(
    product_id: Optional[int] = None,
    operation_type: Optional[OperationType] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    Retrieve chronological audit trail of all inventory movements.
    Tracks timestamps, reference docs, source/dest locations, quantity changes, and balances.
    """
    query = db.query(StockLedgerEntry)

    if product_id:
        query = query.filter(StockLedgerEntry.product_id == product_id)
    if operation_type:
        query = query.filter(StockLedgerEntry.operation_type == operation_type)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (StockLedgerEntry.reference_number.ilike(s)) |
            (StockLedgerEntry.notes.ilike(s))
        )

    entries = query.order_by(StockLedgerEntry.id.desc()).limit(limit).all()

    results = []
    for entry in entries:
        results.append(StockLedgerResponse(
            id=entry.id,
            timestamp=entry.timestamp,
            reference_number=entry.reference_number,
            operation_type=entry.operation_type,
            product_id=entry.product_id,
            product_name=entry.product.name if entry.product else None,
            product_sku=entry.product.sku if entry.product else None,
            product_uom=entry.product.uom if entry.product else None,
            source_location_name=entry.source_location.name if entry.source_location else "External / Initial",
            destination_location_name=entry.destination_location.name if entry.destination_location else "External / Scrap",
            quantity_change=entry.quantity_change,
            resulting_balance=entry.resulting_balance,
            created_by_name=entry.created_by_user.full_name if entry.created_by_user else "System Admin",
            notes=entry.notes
        ))

    return results
