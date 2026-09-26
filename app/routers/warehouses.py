from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Warehouse, Location, LocationType
from app.schemas import (
    WarehouseCreate, WarehouseResponse, LocationCreate, LocationResponse
)

router = APIRouter(prefix="/api", tags=["Warehouses & Locations"])

@router.get("/warehouses", response_model=List[WarehouseResponse])
def get_warehouses(db: Session = Depends(get_db)):
    """List all warehouses with their assigned locations."""
    return db.query(Warehouse).filter(Warehouse.is_active == True).all()

@router.post("/warehouses", response_model=WarehouseResponse)
def create_warehouse(wh: WarehouseCreate, db: Session = Depends(get_db)):
    """Add a new warehouse."""
    existing = db.query(Warehouse).filter(Warehouse.code == wh.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Warehouse code already exists.")
    warehouse = Warehouse(code=wh.code.strip(), name=wh.name.strip(), address=wh.address)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse

@router.get("/locations", response_model=List[LocationResponse])
def get_locations(
    warehouse_id: Optional[int] = None,
    internal_only: bool = False,
    db: Session = Depends(get_db)
):
    """List inventory locations with optional filtering."""
    query = db.query(Location).filter(Location.is_active == True)
    if warehouse_id:
        query = query.filter(Location.warehouse_id == warehouse_id)
    if internal_only:
        query = query.filter(Location.location_type.in_([LocationType.INTERNAL, LocationType.PRODUCTION]))
    return query.order_by(Location.code).all()

@router.post("/locations", response_model=LocationResponse)
def create_location(loc: LocationCreate, db: Session = Depends(get_db)):
    """Add a new location (e.g. Rack, Shelf, Bin, Production Area)."""
    existing = db.query(Location).filter(Location.code == loc.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location code already exists.")
    location = Location(
        warehouse_id=loc.warehouse_id,
        code=loc.code.strip(),
        name=loc.name.strip(),
        location_type=loc.location_type
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location
