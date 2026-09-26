from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, ProductCategory, StockQuant, Location
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    CategoryCreate, CategoryResponse, StockQuantDetail
)
from app.services.inventory_service import (
    create_product, get_product_stock_summary
)

router = APIRouter(prefix="/api", tags=["Products & Catalog"])

@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """List all product categories."""
    return db.query(ProductCategory).order_by(ProductCategory.name).all()

@router.post("/categories", response_model=CategoryResponse)
def create_category(cat: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new product category."""
    existing = db.query(ProductCategory).filter(ProductCategory.name == cat.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists.")
    category = ProductCategory(name=cat.name.strip(), description=cat.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db)
):
    """List products with real-time stock balances, SKU search, and filters."""
    query = db.query(Product).filter(Product.is_active == True)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Product.name.ilike(s)) | (Product.sku.ilike(s)))

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.order_by(Product.name).all()
    results = []

    for p in products:
        summary = get_product_stock_summary(db, p)
        if low_stock_only and not (summary["is_low_stock"] or summary["is_out_of_stock"]):
            continue

        resp = ProductResponse(
            id=p.id,
            sku=p.sku,
            name=p.name,
            description=p.description,
            category_id=p.category_id,
            category_name=p.category.name if p.category else "Uncategorized",
            uom=p.uom,
            min_reorder_qty=p.min_reorder_qty,
            max_target_qty=p.max_target_qty,
            cost_price=p.cost_price,
            selling_price=p.selling_price,
            is_active=p.is_active,
            created_at=p.created_at,
            total_stock=summary["total_stock"],
            is_low_stock=summary["is_low_stock"],
            is_out_of_stock=summary["is_out_of_stock"],
            locations_stock=[StockQuantDetail(**loc) for loc in summary["locations_stock"]]
        )
        results.append(resp)

    return results

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Retrieve details and stock distribution of a single product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    summary = get_product_stock_summary(db, product)
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name if product.category else "Uncategorized",
        uom=product.uom,
        min_reorder_qty=product.min_reorder_qty,
        max_target_qty=product.max_target_qty,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        is_active=product.is_active,
        created_at=product.created_at,
        total_stock=summary["total_stock"],
        is_low_stock=summary["is_low_stock"],
        is_out_of_stock=summary["is_out_of_stock"],
        locations_stock=[StockQuantDetail(**loc) for loc in summary["locations_stock"]]
    )

@router.post("/products", response_model=ProductResponse)
def create_new_product(prod_data: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product with optional initial stock intake."""
    product = create_product(db, prod_data)
    summary = get_product_stock_summary(db, product)

    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name if product.category else "Uncategorized",
        uom=product.uom,
        min_reorder_qty=product.min_reorder_qty,
        max_target_qty=product.max_target_qty,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        is_active=product.is_active,
        created_at=product.created_at,
        total_stock=summary["total_stock"],
        is_low_stock=summary["is_low_stock"],
        is_out_of_stock=summary["is_out_of_stock"],
        locations_stock=[StockQuantDetail(**loc) for loc in summary["locations_stock"]]
    )

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product_details(product_id: int, update_data: ProductUpdate, db: Session = Depends(get_db)):
    """Update product information and reordering rules."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    for field, val in update_data.model_dump(exclude_unset=True).items():
        setattr(product, field, val)

    db.commit()
    db.refresh(product)
    summary = get_product_stock_summary(db, product)

    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name if product.category else "Uncategorized",
        uom=product.uom,
        min_reorder_qty=product.min_reorder_qty,
        max_target_qty=product.max_target_qty,
        cost_price=product.cost_price,
        selling_price=product.selling_price,
        is_active=product.is_active,
        created_at=product.created_at,
        total_stock=summary["total_stock"],
        is_low_stock=summary["is_low_stock"],
        is_out_of_stock=summary["is_out_of_stock"],
        locations_stock=[StockQuantDetail(**loc) for loc in summary["locations_stock"]]
    )
