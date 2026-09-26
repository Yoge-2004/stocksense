from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import engine, Base
from app.seed import seed_database
from app.routers import auth, products, warehouses, operations, ledger, dashboard

# Initialize tables
Base.metadata.create_all(bind=engine)

# Auto seed if database is new
try:
    seed_database()
except Exception as e:
    print(f"Seed check: {e}")

app = FastAPI(
    title="StockSense IMS API",
    description="Modular Inventory Management System API powering centralized stock tracking, workflows, and ledger auditing.",
    version="1.0.0"
)

# Enable CORS for local and web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(operations.router)
app.include_router(ledger.router)
app.include_router(dashboard.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "StockSense IMS", "version": "1.0.0"}

# Mount Static Files (Frontend)
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
