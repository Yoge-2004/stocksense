from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OperationType, OperationStatus
from app.services.inventory_service import get_dashboard_kpis
from app.routers.operations import get_operations

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard & Analytics"])

@router.get("/kpis")
def get_kpis(
    doc_type: Optional[OperationType] = None,
    status: Optional[OperationStatus] = None,
    warehouse_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Returns live inventory KPIs with dynamic multi-dimensional filtering.
    """
    metrics = get_dashboard_kpis(
        db,
        doc_type=doc_type,
        op_status=status,
        warehouse_id=warehouse_id,
        category_id=category_id
    )
    return metrics
