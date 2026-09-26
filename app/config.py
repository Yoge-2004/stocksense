import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/stocksense.db")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "stocksense-super-secret-production-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# System Defaults
DEFAULT_WAREHOUSE_CODE = "WH-MAIN"
DEFAULT_WAREHOUSE_NAME = "Main Central Warehouse"
