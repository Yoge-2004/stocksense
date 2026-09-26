import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    INVENTORY_MANAGER = "Inventory Manager"
    WAREHOUSE_STAFF = "Warehouse Staff"
    ADMIN = "Admin"

class LocationType(str, enum.Enum):
    INTERNAL = "INTERNAL"          # Physical warehouse internal location (Rack, Shelf, Floor)
    VENDOR = "VENDOR"              # Virtual location representing external suppliers
    CUSTOMER = "CUSTOMER"          # Virtual location representing customers
    PRODUCTION = "PRODUCTION"      # Production / Manufacturing floor
    ADJUSTMENT = "ADJUSTMENT"      # Virtual location for inventory loss/gains

class OperationType(str, enum.Enum):
    RECEIPT = "RECEIPT"                      # Incoming stock from vendor
    DELIVERY = "DELIVERY"                    # Outgoing stock to customer
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"  # Move between internal locations/warehouses
    ADJUSTMENT = "ADJUSTMENT"                # Physical count reconciliation

class OperationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    READY = "READY"
    DONE = "DONE"
    CANCELED = "CANCELED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.WAREHOUSE_STAFF, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    operations = relationship("StockOperation", back_populates="created_by_user")
    ledger_entries = relationship("StockLedgerEntry", back_populates="created_by_user")
    otps = relationship("PasswordResetOTP", back_populates="user", cascade="all, delete-orphan")

class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="otps")

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    locations = relationship("Location", back_populates="warehouse", cascade="all, delete-orphan")

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    code = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    location_type = Column(SQLEnum(LocationType), default=LocationType.INTERNAL, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    warehouse = relationship("Warehouse", back_populates="locations")
    quants = relationship("StockQuant", back_populates="location")

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(120), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True)
    uom = Column(String(20), default="units", nullable=False)  # Unit of Measure: units, kg, m, boxes, etc.
    min_reorder_qty = Column(Float, default=10.0, nullable=False)  # Reordering rule threshold
    max_target_qty = Column(Float, default=100.0, nullable=False)
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category = relationship("ProductCategory", back_populates="products")
    quants = relationship("StockQuant", back_populates="product", cascade="all, delete-orphan")
    ledger_entries = relationship("StockLedgerEntry", back_populates="product")

class StockQuant(Base):
    """Represents the on-hand physical stock quantity of a product in a specific location."""
    __tablename__ = "stock_quants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, default=0.0, nullable=False)
    reserved_qty = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_product_location"),
    )

    product = relationship("Product", back_populates="quants")
    location = relationship("Location", back_populates="quants")

class StockOperation(Base):
    """Operations: Receipts, Deliveries, Internal Transfers, and Inventory Adjustments."""
    __tablename__ = "stock_operations"

    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    status = Column(SQLEnum(OperationStatus), default=OperationStatus.DRAFT, nullable=False, index=True)
    source_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    partner_name = Column(String(120), nullable=True)  # Vendor name for receipt, Customer for delivery
    notes = Column(Text, nullable=True)
    is_picked = Column(Boolean, default=False)  # Delivery order picking phase
    is_packed = Column(Boolean, default=False)  # Delivery order packing phase
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    validated_at = Column(DateTime(timezone=True), nullable=True)

    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    created_by_user = relationship("User", back_populates="operations")
    items = relationship("OperationItem", back_populates="operation", cascade="all, delete-orphan")

class OperationItem(Base):
    __tablename__ = "operation_items"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(Integer, ForeignKey("stock_operations.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    demanded_qty = Column(Float, default=0.0, nullable=False)
    done_qty = Column(Float, default=0.0, nullable=False)
    counted_qty = Column(Float, nullable=True)  # For stock adjustments: physical counted amount

    operation = relationship("StockOperation", back_populates="items")
    product = relationship("Product")

class StockLedgerEntry(Base):
    """Stock Ledger / Move History: Immutable audit trail of every stock transition."""
    __tablename__ = "stock_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    reference_number = Column(String(50), index=True, nullable=False)
    operation_type = Column(SQLEnum(OperationType), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    source_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    destination_location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    quantity_change = Column(Float, nullable=False)  # Positive for increment, negative for decrement
    resulting_balance = Column(Float, nullable=False)  # Balance at relevant location
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(255), nullable=True)

    product = relationship("Product", back_populates="ledger_entries")
    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    created_by_user = relationship("User", back_populates="ledger_entries")
