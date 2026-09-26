# StockSense - Modular Inventory Management System (IMS)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-D71F00.svg)](https://www.sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

StockSense is a modern, modular **Inventory Management System (IMS)** designed to digitize and streamline stock-related operations within a business. It replaces manual registers, Excel spreadsheets, and scattered tracking methods with a centralized, real-time, easy-to-use web application with rich aesthetics.

---

## 📌 Problem Statement & Objectives
- **Centralized Stock Control**: Real-time visibility into quantities, warehouses, and rack-level locations.
- **Error Reduction**: Automated double-entry stock ledger guaranteeing inventory balance consistency.
- **Workflow Automation**: Support for standard operations (Receipts, Deliveries, Internal Transfers, and Stock Adjustments).
- **Auditability**: Complete chronological move history tracking every movement, reference doc, and actor.

---

## 👥 Target Users & Personas
- **Inventory Managers**: Manage incoming vendor receipts, customer delivery orders, reordering rules, and low-stock alerts.
- **Warehouse Staff**: Execute picking, packing, shelving, inter-warehouse/rack transfers, and physical stock count adjustments.

---

## 🚀 Core Features & Capabilities

### 1. Authentication & Security
- User registration and login with secure authentication tokens.
- OTP-based password reset simulation.
- Role-based views (Inventory Manager vs Warehouse Staff).

### 2. Live Inventory Dashboard
- **KPI Metrics**:
  - Total Products in Stock
  - Low Stock / Out of Stock alerts
  - Pending Receipts count
  - Pending Deliveries count
  - Scheduled Internal Transfers count
- **Dynamic Multi-Dimensional Filters**:
  - By Document Type: Receipts, Delivery Orders, Internal Transfers, Adjustments
  - By Status: Draft, Waiting, Ready, Done, Canceled
  - By Warehouse & Location
  - By Product Category

### 3. Product & Catalog Management
- Product creation with SKU, Name, Category, Unit of Measure (UOM), and optional initial stock.
- Real-time stock availability breakdown per warehouse and rack location.
- Automated reordering rules and low stock alert thresholds.

### 4. Operations Lifecycle

| Operation | Flow | Stock Impact |
| :--- | :--- | :--- |
| **Receipts** | Vendor delivery $\rightarrow$ Input qty $\rightarrow$ Validate | Stock increases automatically in target location (`+Qty`) |
| **Delivery Orders** | Customer order $\rightarrow$ Pick $\rightarrow$ Pack $\rightarrow$ Validate | Stock decreases automatically from source location (`-Qty`) |
| **Internal Transfers** | Move inside company (e.g. Main Store $\rightarrow$ Production Floor) | Total stock unchanged; location balances updated |
| **Stock Adjustments** | Physical count vs recorded system stock reconciliation | System auto-calculates difference and records adjustment |

### 5. Move History (Stock Ledger)
Every inventory transaction creates an immutable ledger entry recording:
- Timestamp
- Reference Document Number (e.g. `REC-2026-001`, `DEL-2026-001`, `INT-2026-001`, `ADJ-2026-001`)
- Product & SKU
- Source Location $\rightarrow$ Destination Location
- Quantity Changed & Resulting Balance
- User / Operator

### 6. Multi-Warehouse & Locations
- Support for multiple warehouses (e.g., Main Warehouse, Central Logistics, Production Facility).
- Support for internal sub-locations (Racks, Bins, Production Floor, Shelves).

---

## 🛠️ Technology Stack
- **Backend**: Python 3, FastAPI, SQLAlchemy ORM, Pydantic v2, SQLite.
- **Frontend**: Responsive Single-Page Application (SPA) with Vanilla CSS (Glassmorphism, Dark Mode, Micro-animations, Inter font) and SVG/Lucide iconography.
- **API Documentation**: Automatic interactive OpenAPI / Swagger UI at `/docs`.

---

## 💻 Quick Start & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/Yoge-2004/stocksense.git
cd stocksense

# Create virtual environment and activate
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access the web application at: [http://localhost:8000](http://localhost:8000)  
Interactive API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🌿 Git Branching Strategy
- `main`: Production-ready release.
- `feature/database-and-models`: SQLAlchemy models, SQLite configuration, and database seeding.
- `feature/api-operations-and-ledger`: FastAPI REST endpoints, business services, and ledger engine.
- `feature/frontend-ui-and-dashboard`: Premium responsive UI, KPI dashboards, interactive modals, and workflows.

---

## 👤 Author
Developed by **Yogeshwaran M (Yoge-2004)** for Hackathon 2026.
