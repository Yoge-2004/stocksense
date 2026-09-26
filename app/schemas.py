from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models import UserRole, LocationType, OperationType, OperationStatus

# --- Auth Schemas ---
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: Optional[UserRole] = UserRole.WAREHOUSE_STAFF

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

class OTPRequest(BaseModel):
    email: str

class OTPVerifyReset(BaseModel):
    email: str
    otp_code: str
    new_password: str

# --- Warehouse & Location Schemas ---
class WarehouseBase(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    is_active: bool = True

class WarehouseCreate(WarehouseBase):
    pass

class LocationBase(BaseModel):
    warehouse_id: Optional[int] = None
    code: str
    name: str
    location_type: LocationType = LocationType.INTERNAL
    is_active: bool = True

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class WarehouseResponse(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    locations: List[LocationResponse] = []

# --- Product & Category Schemas ---
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    uom: str = "units"
    min_reorder_qty: float = 10.0
    max_target_qty: float = 100.0
    cost_price: float = 0.0
    selling_price: float = 0.0

class ProductCreate(ProductBase):
    initial_stock: Optional[float] = 0.0
    initial_location_id: Optional[int] = None

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    uom: Optional[str] = None
    min_reorder_qty: Optional[float] = None
    max_target_qty: Optional[float] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    is_active: Optional[bool] = None

class StockQuantDetail(BaseModel):
    location_id: int
    location_code: str
    location_name: str
    warehouse_name: Optional[str] = None
    quantity: float

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    category_name: Optional[str] = None
    total_stock: float = 0.0
    is_low_stock: bool = False
    is_out_of_stock: bool = False
    locations_stock: List[StockQuantDetail] = []

# --- Operations Schemas ---
class OperationItemBase(BaseModel):
    product_id: int
    demanded_qty: float
    done_qty: Optional[float] = 0.0
    counted_qty: Optional[float] = None

class OperationItemCreate(OperationItemBase):
    pass

class OperationItemResponse(OperationItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_uom: Optional[str] = None

class OperationBase(BaseModel):
    operation_type: OperationType
    source_location_id: Optional[int] = None
    destination_location_id: Optional[int] = None
    partner_name: Optional[str] = None
    notes: Optional[str] = None

class OperationCreate(OperationBase):
    items: List[OperationItemCreate]

class StockAdjustmentCreate(BaseModel):
    product_id: int
    location_id: int
    counted_qty: float
    notes: Optional[str] = "Physical inventory count adjustment"

class OperationResponse(OperationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_number: str
    status: OperationStatus
    is_picked: bool
    is_packed: bool
    source_location_name: Optional[str] = None
    destination_location_name: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    items: List[OperationItemResponse] = []

# --- Stock Ledger Schemas ---
class StockLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    reference_number: str
    operation_type: OperationType
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_uom: Optional[str] = None
    source_location_name: Optional[str] = None
    destination_location_name: Optional[str] = None
    quantity_change: float
    resulting_balance: float
    created_by_name: Optional[str] = None
    notes: Optional[str] = None

# --- Dashboard & KPI Schemas ---
class DashboardKPIs(BaseModel):
    total_products_in_stock: int
    low_stock_items_count: int
    out_of_stock_items_count: int
    pending_receipts_count: int
    pending_deliveries_count: int
    internal_transfers_scheduled_count: int

class StockCategoryBreakdown(BaseModel):
    category_name: str
    item_count: int
    total_quantity: float

class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKPIs
    category_breakdown: List[StockCategoryBreakdown]
    recent_operations: List[OperationResponse]
    low_stock_alerts: List[ProductResponse]
