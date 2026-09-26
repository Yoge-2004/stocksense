"""
StockSense - End-to-End Frontend UI & Interaction Test Suite
Uses Playwright to test actual browser rendering, DOM interactions,
modal lifecycles, theme toggles, mobile responsiveness, and frontend-backend data flows.
"""

import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        yield context
        browser.close()


def test_dashboard_renders_live_kpis_and_kanban(browser_context):
    """Verify Dashboard renders KPIs, operational Kanban cards, and recent queue from backend."""
    page = browser_context.new_page()
    page.goto(BASE_URL)
    
    # Wait for async KPI fetch to populate
    expect(page.locator("#metric-total-prods")).not_to_have_text("--")
    total_prods = page.inner_text("#metric-total-prods")
    assert int(total_prods) >= 0

    pending_inbound = page.inner_text("#metric-pending-inbound")
    assert "Orders" in pending_inbound

    # Verify Kanban cards rendered
    expect(page.locator(".kanban-operation-card")).to_have_count(4)
    expect(page.locator("#card-receipts-count")).to_be_visible()
    expect(page.locator("#card-deliveries-count")).to_be_visible()

    # Verify recent queue table rows
    rows = page.locator("#overview-recent-ops-body tr")
    assert rows.count() > 0

    page.close()


def test_sidebar_navigation_and_operations_filtering(browser_context):
    """Test switching tabs in the Left Sidebar and verifying operation sub-type filtering."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # 1. Click Receipts in Sidebar
    page.click("#nav-tab-receipts")
    page.wait_for_selector("#view-operations", state="visible")
    expect(page.locator("#view-overview")).to_be_hidden()
    expect(page.locator('[data-op-filter="RECEIPT"]')).to_have_class("filter-tab-pill active")

    # 2. Click Delivery Orders
    page.click("#nav-tab-deliveries")
    expect(page.locator('[data-op-filter="DELIVERY"]')).to_have_class("filter-tab-pill active")

    # 3. Click Internal Transfers
    page.click("#nav-tab-transfers")
    expect(page.locator('[data-op-filter="INTERNAL_TRANSFER"]')).to_have_class("filter-tab-pill active")

    # 4. Click Inventory Adjustment
    page.click("#nav-tab-adjustments")
    expect(page.locator('[data-op-filter="ADJUSTMENT"]')).to_have_class("filter-tab-pill active")

    # 5. Click Products
    page.click("#nav-tab-products")
    page.wait_for_selector("#view-products", state="visible")
    expect(page.locator("#view-operations")).to_be_hidden()
    expect(page.locator("#products-table-body tr")).not_to_have_count(0)

    # 6. Click Move History
    page.click("#nav-tab-ledger")
    page.wait_for_selector("#view-ledger", state="visible")
    expect(page.locator("#view-products")).to_be_hidden()
    expect(page.locator("#ledger-table-body tr")).not_to_have_count(0)

    # 7. Click Settings
    page.click("#nav-tab-config")
    page.wait_for_selector("#view-configuration", state="visible")
    expect(page.locator("#config-warehouses-list")).to_be_visible()
    expect(page.locator("#config-locations-list")).to_be_visible()

    # 8. Return to Dashboard
    page.click("#nav-tab-overview")
    page.wait_for_selector("#view-overview", state="visible")
    expect(page.locator("#view-configuration")).to_be_hidden()

    page.close()


def test_stock_by_location_modal(browser_context):
    """Test clicking 'Stock per Location' opens the modal and lists warehouse storage locations."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    page.click("#nav-tab-stock-loc")
    page.wait_for_selector("#modal-stock-by-location.active")

    # Verify modal title and content
    modal_title = page.inner_text("#stock-loc-modal-title")
    assert "Stock Availability" in modal_title

    # Close modal
    page.click("#modal-stock-by-location [data-close-modal]")
    expect(page.locator("#modal-stock-by-location")).not_to_have_class("active")

    page.close()


def test_theme_toggle_interaction(browser_context):
    """Test Light to Dark mode toggle and DOM attribute updating."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # Default is light
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#theme-text")).to_have_text("Dark")

    # Toggle to Dark
    page.click("#theme-toggle-btn")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("#theme-text")).to_have_text("Light")

    # Toggle back to Light
    page.click("#theme-toggle-btn")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#theme-text")).to_have_text("Dark")

    page.close()


def test_user_profile_modal_and_persona_switch(browser_context):
    """Test opening User Profile from left sidebar bottom, persona switching, and OTP token request."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # Open profile modal from Left Sidebar bottom footer
    page.click("#btn-sidebar-profile")
    page.wait_for_selector("#modal-user-profile.active")

    # Verify initial manager
    expect(page.locator("#profile-modal-name")).to_have_text("Alex Rivera")
    expect(page.locator("#profile-modal-role")).to_have_text("Inventory Manager")

    # Switch persona to Warehouse Staff
    page.click("#btn-switch-to-staff")
    expect(page.locator("#profile-modal-name")).to_have_text("Sam Morgan")
    expect(page.locator("#profile-modal-role")).to_have_text("Warehouse Staff")
    expect(page.locator("#user-header-name")).to_have_text("Sam Morgan")

    # Request OTP token
    page.click("#btn-send-profile-otp")
    page.wait_for_selector("#profile-otp-reset-panel", state="visible")
    otp_code = page.input_value("#profile-otp-code-input")
    assert len(otp_code) == 6

    # Close modal
    page.click("#modal-user-profile [data-close-modal]")
    expect(page.locator("#modal-user-profile")).not_to_have_class("active")

    page.close()


def test_mobile_drawer_navigation(browser_context):
    """Test responsiveness on mobile viewport (375x667), hamburger button, and drawer overlay."""
    page = browser_context.new_page()
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(BASE_URL)

    sidebar = page.locator("#app-sidebar")
    overlay = page.locator("#mobile-sidebar-overlay")

    # Sidebar should not have mobile-open initially
    expect(sidebar).not_to_have_class("mobile-open")
    expect(overlay).not_to_have_class("mobile-open")

    # Click hamburger toggle
    page.click("#btn-mobile-toggle")
    expect(sidebar).to_have_class("sidebar mobile-open")
    expect(overlay).to_have_class("mobile-sidebar-overlay mobile-open")

    # Click overlay to close
    overlay.click()
    expect(sidebar).not_to_have_class("mobile-open")
    expect(overlay).not_to_have_class("mobile-open")

    page.close()


def test_create_transfer_from_ui(browser_context):
    """Test full transfer creation workflow via the UI modal dialog."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # Click New Transfer button in header
    page.click("#btn-open-create-modal")
    page.wait_for_selector("#modal-create-transfer.active")

    # Fill form
    page.select_option("#new-op-type-select", "RECEIPT")
    page.fill("#new-op-partner", "Apex Automation Suppliers")
    page.fill("#new-op-qty", "15")
    page.fill("#new-op-notes", "UI Playwright Automated Inbound Delivery")

    # Submit
    page.click('#form-create-transfer button[type="submit"]')

    # Verify Toast notification
    expect(page.locator(".erp-toast-pill, .erp-toast")).to_contain_text("Stock transfer created in Draft status.")
    expect(page.locator("#modal-create-transfer")).not_to_have_class("active")

    page.close()


def test_physical_inventory_adjustment_from_ui(browser_context):
    """Test physical stock reconciliation count dialog and ledger sync from UI."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # Open adjustment modal from Kanban card
    page.click("#btn-card-record-count")
    page.wait_for_selector("#modal-physical-count.active")

    # Fill count
    page.fill("#adj-counted-qty", "42.5")
    page.fill("#adj-reason-notes", "UI Playwright Physical Count Verification")

    # Submit
    page.click('#form-physical-count button[type="submit"]')

    # Verify toast confirmation
    expect(page.locator(".erp-toast-pill, .erp-toast")).to_contain_text("reconciled & logged to ledger")
    expect(page.locator("#modal-physical-count")).not_to_have_class("active")

    page.close()


def test_case_study_scenario_execution_from_ui(browser_context):
    """Test executing the 4-step problem statement flow from the UI and verifying ledger audit trail."""
    page = browser_context.new_page()
    page.goto(BASE_URL)

    # Click Case Study button
    page.click("#btn-run-case-study")
    page.wait_for_selector("#modal-case-study.active")

    # Verify all 4 steps are shown in dialog
    expect(page.locator("#cs-step-1")).to_be_visible()
    expect(page.locator("#cs-step-2")).to_be_visible()
    expect(page.locator("#cs-step-3")).to_be_visible()
    expect(page.locator("#cs-step-4")).to_be_visible()

    # Click Execute Full Flow
    page.click("#btn-execute-case-study")

    # Verify success toast
    expect(page.locator(".erp-toast-pill, .erp-toast")).to_contain_text("Problem statement case study flow completed successfully!")

    # Verify automatic transition to Move History (Stock Ledger)
    expect(page.locator("#view-ledger")).to_be_visible()
    expect(page.locator("#ledger-table-body tr")).not_to_have_count(0)

    page.close()

