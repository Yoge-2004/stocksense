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

## 🧪 Comprehensive Automated Testing (33 Tests: API + Spec + UI)

StockSense includes an exhaustive pytest automated test suite (**33 tests**) directly verifying all backend business logic, PDF edge cases, and real browser end-to-end user interactions using Playwright:

```bash
# Run the complete test suite (API integration + PDF specifications + Playwright UI)
PYTHONPATH=. pytest tests/ -v
```

### Verified Test Matrix:
1. **User Authentication & Personas (`test_user_personas_and_login`)**: Manager vs Warehouse Staff session verification, profile endpoint, invalid password handling.
2. **User Registration & Constraints (`test_user_registration_and_edge_cases`)**: User sign-up, duplicate username rejection, duplicate email rejection.
3. **OTP Password Reset (`test_otp_password_reset_and_edge_cases`)**: OTP generation, verification, password update, expired OTP rejection, replay attack prevention.
4. **Product Lifecycle & Constraints (`test_product_lifecycle_and_edge_cases`)**: SKU uniqueness, negative stock/price input rejection, multi-location stock calculation.
5. **Reordering Rules & Low Stock (`test_reordering_rules_and_low_stock_alerts`)**: Automated low-stock warning threshold triggering and out-of-stock tracking.
6. **Receipts Full Workflow (`test_receipt_full_workflow`)**: Vendor intake, receipt creation, validation, `+Qty` stock increment, and Stock Ledger auditing.
7. **Delivery Orders Workflow (`test_delivery_order_workflow_and_stock_reduction`)**: Sales dispatches, picking, packing, validation, `-Qty` stock reduction, and ledger auditing.
8. **Delivery Insufficient Stock Edge Case (`test_delivery_order_insufficient_stock_edge_case`)**: Validation rejection when stock is inadequate.
9. **Internal Transfers & Invariance (`test_internal_transfer_and_stock_invariance`)**: Movement between Main Store and Production Floor; company-wide stock invariance verification.
10. **Internal Transfer Edge Cases (`test_internal_transfer_edge_cases`)**: Identical source and destination rejection; transfer with zero or missing stock rejection.
11. **Stock Adjustments Reconciliation (`test_stock_adjustments_reconciliation`)**: Physical inventory counts reconciliation, positive/negative variance adjustments, scrap loss logging.
12. **Negative Count Rejection Edge Case (`test_stock_adjustment_negative_count_edge_case`)**: Negative physical count input rejection.
13. **Dashboard KPIs & Dynamic Filters (`test_dashboard_kpis_and_dynamic_filters`)**: Validation of all 5 KPI metrics and 4-dimensional filtering (type, status, warehouse, category).
14. **Multi-Warehouse Support (`test_multi_warehouse_support`)**: Facilities and location rack/shelf hierarchy management.
15. **PDF Page 4 Walkthrough Scenario (`test_simplified_example_flow_from_pdf`)**: End-to-end 4-step execution (100kg steel received $\rightarrow$ internal transfer to production $\rightarrow$ deliver 20kg $\rightarrow$ adjust 3kg damaged).
16. **Playwright UI Dashboard Live KPIs (`test_dashboard_renders_live_kpis_and_kanban`)**: End-to-end browser test verifying asynchronous KPI population, 4 Kanban operation cards, and recent operational queue.
17. **Playwright UI Sidebar Navigation (`test_sidebar_navigation_and_operations_filtering`)**: Verifies tab switching, sub-operation filters (Receipts, Deliveries, Transfers, Adjustments), and active navigation classes.
18. **Playwright UI Stock per Location Modal (`test_stock_by_location_modal`)**: Verifies modal opening, table rendering of warehouse locations, and modal closing.
19. **Playwright UI Theme Switching (`test_theme_toggle_interaction`)**: Verifies light $\leftrightarrow$ dark mode DOM `data-theme` attribute toggling and icon/label transitions.
20. **Playwright UI User Profile & Persona Switch (`test_user_profile_modal_and_persona_switch`)**: Verifies left sidebar profile menu opening, switching between Alex Rivera (Manager) and Sam Morgan (Staff), and OTP token simulation.
21. **Playwright UI Mobile Responsive Drawer (`test_mobile_drawer_navigation`)**: Verifies viewport resizing to mobile (375x667), hamburger toggle button, and `.mobile-sidebar-overlay` backdrop drawer control.
22. **Playwright UI Transfer Creation (`test_create_transfer_from_ui`)**: End-to-end transfer submission through modal and toast verification.
23. **Playwright UI Physical Inventory Adjustment (`test_physical_inventory_adjustment_from_ui`)**: Submits physical stock count from UI and checks ledger synchronization.
24. **Playwright UI Problem Statement Scenario Execution (`test_case_study_scenario_execution_from_ui`)**: Executes full 4-step flow via UI button and verifies automatic transition to Move History ledger.

---

## 📐 Coding Design Principles Adherence

The StockSense architecture is engineered strictly adhering to industry design principles:

- **Single Responsibility Principle (SRP)**:
  - `models.py`: Database entities and relations.
  - `schemas.py`: Pydantic input/output validation contracts.
  - `services/inventory_service.py`: Stock quant math, transaction management, and validation logic.
  - `routers/`: Clean HTTP REST controller endpoints.
  - `database.py`: Thread-safe database engine and session dependency injection.
- **Open/Closed Principle (OCP)**:
  - Polymorphic operation types (`OperationType`: RECEIPT, DELIVERY, INTERNAL_TRANSFER, ADJUSTMENT) and location types (`INTERNAL`, `VENDOR`, `CUSTOMER`, `SCRAP`) extensible without mutating existing ledger engines.
- **Liskov Substitution Principle (LSP)**:
  - All operation lifecycle actions adhere to a uniform double-entry contract generating balanced, immutable `StockLedgerEntry` audit records.
- **Interface Segregation Principle (ISP)**:
  - Fine-grained Pydantic schemas separating mutation payloads from client read projections (`ProductCreate` vs `ProductResponse`, `OperationCreate` vs `OperationResponse`).
- **Dependency Inversion Principle (DIP)**:
  - Routers depend on database abstractions via FastAPI's `Depends(get_db)`, eliminating global session coupling and facilitating mockable test environments.
- **DRY & KISS**:
  - Centralized collision-free reference generator, reusable stock quant updater, and request sequence counter guards eliminating frontend race conditions.
- **Double-Entry Accounting & Immutability**:
  - Guaranteed inventory conservation: stock cannot appear or disappear without an immutable ledger audit entry.

---

## 🌿 Git Branching Strategy
- `main`: Production-ready release.
- `feature/database-and-models`: SQLAlchemy models, SQLite configuration, and database seeding.
- `feature/api-operations-and-ledger`: FastAPI REST endpoints, business services, and ledger engine.
- `feature/frontend-ui-and-dashboard`: Responsive UI, KPI dashboards, interactive modals, and workflows.
- `feature/responsive-odoo-theme-and-tests`: Authentic Odoo ERP design system and complete automated API test suite.
- `feature/ui-playwright-testing-and-principles`: Playwright automated browser E2E test suite, race condition elimination, light-mode contrast fix, and coding design principles compliance.


---

## 👤 Author
Developed by **Yogeshwaran M (Yoge-2004)** for Hackathon 2026.

