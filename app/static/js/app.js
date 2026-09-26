// StockSense Enterprise Inventory Management System (IMS)
// Professional Odoo-style frontend client logic

const API_BASE = '/api';

const state = {
  currentView: 'overview',
  activeUser: {
    id: 1,
    name: 'Alex Rivera',
    email: 'manager@stocksense.io',
    role: 'Inventory Manager',
    initials: 'AR'
  },
  products: [],
  warehouses: [],
  locations: [],
  categories: [],
  operations: [],
  filters: {
    opType: '',
    opStatus: '',
    opSearch: '',
    prodSearch: '',
    prodCategory: '',
    prodLowStockOnly: false,
    ledgerSearch: '',
    ledgerType: '',
    warehouseId: ''
  }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupModals();
  setupFilters();
  setupActionListeners();

  await loadInitialLookups();
  await refreshCurrentView();
});

// --- Toast System ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `erp-toast toast-border-${type}`;

  const iconSvg = type === 'success' 
    ? '<svg class="icon-svg" style="color: #10b981;" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
    : type === 'error'
    ? '<svg class="icon-svg" style="color: #ef4444;" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
    : '<svg class="icon-svg" style="color: #7c3aed;" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';

  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.2s ease';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

// --- Navigation ---
function setupNavigation() {
  const navLinks = document.querySelectorAll('.nav-link, .nav-tab-btn');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const view = link.getAttribute('data-view');
      const opQuick = link.getAttribute('data-op-quick');
      const focus = link.getAttribute('data-focus');

      navLinks.forEach(l => l.classList.remove('active'));
      link.classList.add('active');

      closeMobileSidebar();

      if (opQuick) {
        filterOperationsView(opQuick);
      } else if (focus === 'stock-loc') {
        switchView('products');
        if (state.products && state.products.length > 0) {
          showStockByLocationModal(state.products[0].id);
        }
      } else if (focus === 'reorder') {
        switchView('products');
        const lowCheck = document.getElementById('prods-low-stock-check');
        if (lowCheck) {
          lowCheck.checked = true;
          state.filters.prodLowStockOnly = true;
          loadProductsGrid();
        }
      } else if (view) {
        switchView(view);
      }
    });
  });

  const brandLogo = document.getElementById('brand-logo');
  if (brandLogo) {
    brandLogo.addEventListener('click', () => {
      navLinks.forEach(l => l.classList.remove('active'));
      const overviewTab = document.getElementById('nav-tab-overview');
      if (overviewTab) overviewTab.classList.add('active');
      closeMobileSidebar();
      switchView('overview');
    });
  }

  // Mobile Drawer Toggle
  const mobileToggle = document.getElementById('btn-mobile-toggle');
  const overlay = document.getElementById('mobile-sidebar-overlay');
  const sidebar = document.getElementById('app-sidebar');

  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
      if (overlay) overlay.classList.toggle('mobile-open');
    });
  }

  if (overlay && sidebar) {
    overlay.addEventListener('click', () => {
      closeMobileSidebar();
    });
  }

  // Theme Switcher Setup
  setupThemeToggle();
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('app-sidebar');
  const overlay = document.getElementById('mobile-sidebar-overlay');
  if (sidebar) sidebar.classList.remove('mobile-open');
  if (overlay) overlay.classList.remove('mobile-open');
}

function setupThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  const themeText = document.getElementById('theme-text');
  const themeIcon = document.getElementById('theme-icon');

  const savedTheme = localStorage.getItem('stocksense-theme') || 'light';
  applyTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
      localStorage.setItem('stocksense-theme', nextTheme);
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (themeText && themeIcon) {
      if (theme === 'dark') {
        themeText.textContent = 'Light';
        themeIcon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
      } else {
        themeText.textContent = 'Dark';
        themeIcon.innerHTML = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>';
      }
    }
  }
}

function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.view-panel').forEach(p => p.style.display = 'none');

  const panel = document.getElementById(`view-${viewName}`);
  if (panel) panel.style.display = 'block';

  const breadcrumbs = {
    'overview': 'Dashboard',
    'operations': 'Operations & Transfers',
    'products': 'Products & Catalog',
    'ledger': 'Move History / Stock Ledger',
    'configuration': 'Warehouse Settings'
  };
  const crumbEl = document.getElementById('breadcrumb-current');
  if (crumbEl) crumbEl.textContent = breadcrumbs[viewName] || 'Dashboard';

  refreshCurrentView();
}

async function refreshCurrentView() {
  if (state.currentView === 'overview') {
    await Promise.all([loadKPIsAndCards(), loadOverviewRecentOps()]);
  } else if (state.currentView === 'operations') {
    await loadOperationsGrid();
  } else if (state.currentView === 'products') {
    await loadProductsGrid();
  } else if (state.currentView === 'ledger') {
    await loadLedgerGrid();
  } else if (state.currentView === 'configuration') {
    renderConfigView();
  }
}

// --- Lookups ---
async function loadInitialLookups() {
  try {
    const [catsRes, whsRes, locsRes, prodsRes] = await Promise.all([
      fetch(`${API_BASE}/categories`),
      fetch(`${API_BASE}/warehouses`),
      fetch(`${API_BASE}/locations`),
      fetch(`${API_BASE}/products`)
    ]);

    state.categories = await catsRes.json();
    state.warehouses = await whsRes.json();
    state.locations = await locsRes.json();
    state.products = await prodsRes.json();

    populateAllDropdowns();
  } catch (err) {
    console.error('Failed to load lookups:', err);
    showToast('Failed to connect to backend service', 'error');
  }
}

function populateAllDropdowns() {
  // Category dropdowns
  const prodCatSelect = document.getElementById('prods-category-select');
  const newProdCat = document.getElementById('new-prod-category');
  const catOpts = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  if (prodCatSelect) prodCatSelect.innerHTML = '<option value="">All Product Categories</option>' + catOpts;
  if (newProdCat) newProdCat.innerHTML = catOpts;

  // Product dropdowns for transfers
  const newOpProd = document.getElementById('new-op-product');
  const adjProd = document.getElementById('adj-product-select');
  const prodOpts = state.products.map(p => `<option value="${p.id}">${p.name} (${p.sku}) - ${p.uom}</option>`).join('');
  if (newOpProd) newOpProd.innerHTML = prodOpts;
  if (adjProd) adjProd.innerHTML = prodOpts;

  updateNewTransferLocationOptions();
}

function updateNewTransferLocationOptions() {
  const type = document.getElementById('new-op-type-select').value;
  const srcSelect = document.getElementById('new-op-source-loc');
  const dstSelect = document.getElementById('new-op-dest-loc');
  const adjLoc = document.getElementById('adj-location-select');

  const internalLocs = state.locations.filter(l => l.location_type === 'INTERNAL' || l.location_type === 'PRODUCTION');
  const internalOpts = internalLocs.map(l => `<option value="${l.id}">${l.name} (${l.code})</option>`).join('');

  if (adjLoc) adjLoc.innerHTML = internalOpts;

  const partnerGroup = document.getElementById('group-modal-partner');
  const partnerLabel = document.getElementById('label-modal-partner');
  const srcGroup = document.getElementById('group-modal-source');
  const dstGroup = document.getElementById('group-modal-dest');

  if (type === 'RECEIPT') {
    partnerGroup.style.display = 'flex';
    partnerLabel.textContent = 'Supplier / Vendor Partner';
    srcGroup.style.display = 'none';
    dstGroup.style.display = 'flex';
    dstSelect.innerHTML = internalOpts;
  } else if (type === 'DELIVERY') {
    partnerGroup.style.display = 'flex';
    partnerLabel.textContent = 'Customer / Client Name';
    srcGroup.style.display = 'flex';
    dstGroup.style.display = 'none';
    srcSelect.innerHTML = internalOpts;
  } else if (type === 'INTERNAL_TRANSFER') {
    partnerGroup.style.display = 'none';
    srcGroup.style.display = 'flex';
    dstGroup.style.display = 'flex';
    srcSelect.innerHTML = internalOpts;
    dstSelect.innerHTML = internalOpts;
  }
}

// --- Overview: KPI Strip & Kanban Cards ---
async function loadKPIsAndCards() {
  try {
    const [kpiRes, opsRes] = await Promise.all([
      fetch(`${API_BASE}/dashboard/kpis`),
      fetch(`${API_BASE}/operations`)
    ]);

    const kpiData = await kpiRes.json();
    const ops = await opsRes.json();
    state.operations = ops;

    const k = kpiData.kpis;
    document.getElementById('metric-total-prods').textContent = k.total_products_in_stock;
    document.getElementById('metric-low-stock').textContent = k.low_stock_items_count + k.out_of_stock_items_count;
    document.getElementById('metric-pending-inbound').textContent = `${k.pending_receipts_count} Orders`;
    document.getElementById('metric-scheduled-ops').textContent = `${k.internal_transfers_scheduled_count + k.pending_deliveries_count} Scheduled`;

    // Process Kanban Cards
    const receipts = ops.filter(o => o.operation_type === 'RECEIPT');
    const pendingReceipts = receipts.filter(o => o.status !== 'DONE' && o.status !== 'CANCELED');
    const doneReceipts = receipts.filter(o => o.status === 'DONE');
    document.getElementById('card-receipts-count').textContent = pendingReceipts.length;
    document.getElementById('card-receipts-ready').textContent = `${pendingReceipts.filter(o => o.status === 'READY').length} Operations`;
    document.getElementById('card-receipts-done').textContent = `${doneReceipts.length} Validated`;

    const deliveries = ops.filter(o => o.operation_type === 'DELIVERY');
    const pendingDeliveries = deliveries.filter(o => o.status !== 'DONE' && o.status !== 'CANCELED');
    document.getElementById('card-deliveries-count').textContent = pendingDeliveries.length;
    document.getElementById('card-deliveries-waiting').textContent = `${pendingDeliveries.filter(o => o.status === 'WAITING' || !o.is_picked).length} Orders`;
    document.getElementById('card-deliveries-ready').textContent = `${pendingDeliveries.filter(o => o.is_packed || o.status === 'READY').length} Orders`;

    const transfers = ops.filter(o => o.operation_type === 'INTERNAL_TRANSFER');
    const pendingTransfers = transfers.filter(o => o.status !== 'DONE' && o.status !== 'CANCELED');
    document.getElementById('card-transfers-count').textContent = pendingTransfers.length;
    document.getElementById('card-transfers-scheduled').textContent = `${pendingTransfers.length} Moves`;
    document.getElementById('card-transfers-done').textContent = `${transfers.filter(o => o.status === 'DONE').length} Completed`;

    const adjustments = ops.filter(o => o.operation_type === 'ADJUSTMENT');
    document.getElementById('card-adjustments-count').textContent = adjustments.length;

    // Update Left Sidebar notification badges
    const badgeReceipts = document.getElementById('badge-receipts-count');
    if (badgeReceipts) badgeReceipts.textContent = pendingReceipts.length;
    const badgeDeliveries = document.getElementById('badge-deliveries-count');
    if (badgeDeliveries) badgeDeliveries.textContent = pendingDeliveries.length;
    const badgeLowStock = document.getElementById('badge-low-stock-count');
    if (badgeLowStock) badgeLowStock.textContent = k.low_stock_items_count + k.out_of_stock_items_count;
  } catch (err) {
    console.error('Error loading KPIs:', err);
  }
}

async function loadOverviewRecentOps() {
  const tbody = document.getElementById('overview-recent-ops-body');
  try {
    const res = await fetch(`${API_BASE}/operations?limit=5`);
    const ops = await res.json();

    if (!ops || ops.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-dim);">No active operations queued.</td></tr>';
      return;
    }

    tbody.innerHTML = ops.slice(0, 6).map(op => {
      const pillClass = getStatusPillClass(op.status);
      const typeTag = getTypeTag(op.operation_type);

      return `
        <tr>
          <td><span class="ref-code" onclick="openOperationDetailModal(${op.id})" style="cursor: pointer; text-decoration: underline;">${op.reference_number}</span></td>
          <td>${typeTag}</td>
          <td>${op.source_location_name || 'Vendors (External)'}</td>
          <td>${op.destination_location_name || 'Customers (External)'}</td>
          <td>${op.partner_name || op.notes || '-'}</td>
          <td><span class="erp-status-pill ${pillClass}">${formatStatus(op.status)}</span></td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="openOperationDetailModal(${op.id})">Open</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading recent ops:', err);
  }
}

// --- Operations List View ---
async function loadOperationsGrid() {
  const tbody = document.getElementById('operations-table-body');
  try {
    let url = `${API_BASE}/operations?`;
    if (state.filters.opType) url += `operation_type=${state.filters.opType}&`;
    if (state.filters.opStatus) url += `status=${state.filters.opStatus}&`;
    if (state.filters.opSearch) url += `search=${encodeURIComponent(state.filters.opSearch)}&`;

    const res = await fetch(url);
    const ops = await res.json();
    state.operations = ops;

    if (!ops || ops.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 30px; color: var(--text-dim);">No operations found for current filters.</td></tr>';
      return;
    }

    tbody.innerHTML = ops.map(op => {
      const pillClass = getStatusPillClass(op.status);
      const typeTag = getTypeTag(op.operation_type);
      const itemsText = op.items.map(i => `${i.product_name || i.product_sku}: ${i.done_qty || i.demanded_qty} ${i.product_uom || ''}`).join(', ');
      const dateStr = new Date(op.created_at).toLocaleDateString();

      let actionsHtml = `<button class="btn btn-secondary btn-sm" onclick="openOperationDetailModal(${op.id})">View</button> `;
      if (op.status !== 'DONE' && op.status !== 'CANCELED') {
        actionsHtml += `<button class="btn btn-primary btn-sm" onclick="executeValidateOpDirect(${op.id})">Validate</button>`;
      }

      return `
        <tr>
          <td><span class="ref-code" onclick="openOperationDetailModal(${op.id})" style="cursor: pointer;">${op.reference_number}</span></td>
          <td>${typeTag}</td>
          <td>${dateStr}</td>
          <td>${op.source_location_name || 'External'}</td>
          <td>${op.destination_location_name || 'External'}</td>
          <td>${op.partner_name || op.notes || '-'}</td>
          <td style="max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${itemsText}">${itemsText}</td>
          <td><span class="erp-status-pill ${pillClass}">${formatStatus(op.status)}</span></td>
          <td>${actionsHtml}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading operations grid:', err);
  }
}

// --- Products Grid ---
async function loadProductsGrid() {
  const tbody = document.getElementById('products-table-body');
  try {
    let url = `${API_BASE}/products?`;
    if (state.filters.prodSearch) url += `search=${encodeURIComponent(state.filters.prodSearch)}&`;
    if (state.filters.prodCategory) url += `category_id=${state.filters.prodCategory}&`;
    if (state.filters.prodLowStockOnly) url += `low_stock_only=true&`;

    const res = await fetch(url);
    const prods = await res.json();
    state.products = prods;

    if (!prods || prods.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 30px; color: var(--text-dim);">No products match filter settings.</td></tr>';
      return;
    }

    tbody.innerHTML = prods.map(p => {
      let statusPill = `<span class="erp-status-pill status-done">Normal</span>`;
      if (p.is_out_of_stock) {
        statusPill = `<span class="erp-status-pill status-canceled">Out of Stock</span>`;
      } else if (p.is_low_stock) {
        statusPill = `<span class="erp-status-pill status-waiting">Low Stock Warning</span>`;
      }

      const stockColor = p.total_stock <= 0 ? '#ef4444' : '#fff';

      return `
        <tr>
          <td><code class="ref-code">${p.sku}</code></td>
          <td><strong style="color: #fff;">${p.name}</strong></td>
          <td>${p.category_name}</td>
          <td style="text-align: right; font-weight: 700; font-size: 1.05rem; color: ${stockColor}; font-variant-numeric: tabular-nums;">${p.total_stock}</td>
          <td>${p.uom}</td>
          <td style="text-align: right; color: var(--text-dim); font-variant-numeric: tabular-nums;">${p.min_reorder_qty} ${p.uom}</td>
          <td>${statusPill}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="showStockByLocationModal(${p.id})">Stock by Location</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading products:', err);
  }
}

// --- Move History (Stock Ledger) ---
async function loadLedgerGrid() {
  const tbody = document.getElementById('ledger-table-body');
  try {
    let url = `${API_BASE}/ledger?`;
    if (state.filters.ledgerType) url += `operation_type=${state.filters.ledgerType}&`;
    if (state.filters.ledgerSearch) url += `search=${encodeURIComponent(state.filters.ledgerSearch)}&`;

    const res = await fetch(url);
    const entries = await res.json();

    if (!entries || entries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 30px; color: var(--text-dim);">No movements recorded in stock ledger.</td></tr>';
      return;
    }

    tbody.innerHTML = entries.map(e => {
      const dt = new Date(e.timestamp);
      const formattedDate = `${dt.toLocaleDateString()} ${dt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
      const isPositive = e.quantity_change > 0;
      const qtyClass = isPositive ? 'color: #34d399;' : 'color: #f87171;';
      const qtySign = isPositive ? `+${e.quantity_change}` : `${e.quantity_change}`;

      return `
        <tr>
          <td style="font-size: 0.8rem; color: var(--text-dim);">${formattedDate}</td>
          <td><span class="ref-code">${e.reference_number}</span></td>
          <td>${getTypeTag(e.operation_type)}</td>
          <td><strong style="color: #fff;">${e.product_name}</strong><span class="product-sku">${e.product_sku}</span></td>
          <td>${e.source_location_name || 'Vendors (External)'}</td>
          <td>${e.destination_location_name || 'Scrap / Loss'}</td>
          <td style="text-align: right; font-weight: 600; ${qtyClass} font-variant-numeric: tabular-nums;">${qtySign} ${e.product_uom}</td>
          <td style="text-align: right; font-weight: 600; color: #fff; font-variant-numeric: tabular-nums;">${e.resulting_balance} ${e.product_uom}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${e.created_by_name || 'System Operator'}</td>
          <td style="font-size: 0.8rem; color: var(--text-dim);">${e.notes || '-'}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading ledger:', err);
  }
}

// --- Configuration View ---
function renderConfigView() {
  const whList = document.getElementById('config-warehouses-list');
  const locList = document.getElementById('config-locations-list');

  whList.innerHTML = state.warehouses.map(w => `
    <div style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 12px 14px; margin-bottom: 10px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <strong style="color: #fff; font-size: 0.92rem;">${w.name}</strong>
        <span class="ref-code">${w.code}</span>
      </div>
      <div style="font-size: 0.78rem; color: var(--text-dim); margin-top: 4px;">${w.address || 'Standard Warehouse Facility'}</div>
    </div>
  `).join('');

  locList.innerHTML = state.locations.map(l => `
    <div style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong style="color: #fff; font-size: 0.86rem;">${l.name}</strong>
        <span class="product-sku">${l.code}</span>
      </div>
      <span class="type-tag" style="background: var(--bg-elevated); color: var(--text-muted);">${l.location_type}</span>
    </div>
  `).join('');
}

// --- Operation Detail Modal (Odoo-Style Validation) ---
async function openOperationDetailModal(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}`);
    const op = await res.json();

    document.getElementById('detail-modal-ref').textContent = op.reference_number;
    document.getElementById('detail-modal-type-tag').className = `type-tag type-${op.operation_type.toLowerCase()}`;
    document.getElementById('detail-modal-type-tag').textContent = op.operation_type.replace('_', ' ');

    // Status pipeline highlight
    const stages = ['draft', 'waiting', 'ready', 'done'];
    const currentStage = op.status.toLowerCase();
    stages.forEach(s => {
      const el = document.getElementById(`pipe-${s}`);
      el.className = 'pipeline-stage';
      if (s === currentStage) el.classList.add('active');
    });
    if (op.status === 'DONE') {
      document.getElementById('pipe-draft').classList.add('completed');
      document.getElementById('pipe-waiting').classList.add('completed');
      document.getElementById('pipe-ready').classList.add('completed');
      document.getElementById('pipe-done').classList.add('active');
    }

    document.getElementById('detail-partner-name').textContent = op.partner_name || 'Internal Warehouse Transfer';
    document.getElementById('detail-responsible-user').textContent = op.created_by_name || 'Alex Rivera (Inventory Manager)';
    document.getElementById('detail-source-loc').textContent = op.source_location_name || 'Vendors (External)';
    document.getElementById('detail-dest-loc').textContent = op.destination_location_name || 'Customers (External)';
    document.getElementById('detail-notes').textContent = op.notes || 'None specified.';

    const linesBody = document.getElementById('detail-lines-body');
    linesBody.innerHTML = op.items.map(item => `
      <tr>
        <td><strong style="color: #fff;">${item.product_name}</strong><span class="product-sku">${item.product_sku}</span></td>
        <td style="text-align: right; font-variant-numeric: tabular-nums;">${item.demanded_qty}</td>
        <td style="text-align: right; font-weight: 600; color: #34d399; font-variant-numeric: tabular-nums;">${item.done_qty || (op.status === 'DONE' ? item.demanded_qty : 0)}</td>
        <td>${item.product_uom}</td>
      </tr>
    `).join('');

    const btnGroup = document.getElementById('detail-action-buttons-group');
    btnGroup.innerHTML = '';

    if (op.status !== 'DONE' && op.status !== 'CANCELED') {
      if (op.operation_type === 'DELIVERY') {
        if (!op.is_picked) {
          btnGroup.innerHTML += `<button class="btn btn-secondary" onclick="pickDeliveryOrder(${op.id})">Pick Items</button>`;
        } else if (!op.is_packed) {
          btnGroup.innerHTML += `<button class="btn btn-secondary" onclick="packDeliveryOrder(${op.id})">Pack Items</button>`;
        }
      }

      btnGroup.innerHTML += `<button class="btn btn-primary" onclick="validateOpFromModal(${op.id})">Validate Transfer</button>`;
      btnGroup.innerHTML += `<button class="btn btn-secondary" onclick="cancelOpFromModal(${op.id})">Cancel</button>`;
    }

    document.getElementById('modal-op-detail').classList.add('active');
  } catch (err) {
    console.error('Failed to open operation details:', err);
    showToast('Failed to open operation details', 'error');
  }
}

async function validateOpFromModal(opId) {
  await executeValidateOpDirect(opId);
  document.getElementById('modal-op-detail').classList.remove('active');
}

async function cancelOpFromModal(opId) {
  if (!confirm('Are you sure you want to cancel this transfer order?')) return;
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/cancel`, { method: 'POST' });
    if (!res.ok) throw new Error('Cancellation failed');
    showToast('Operation status set to Canceled.', 'info');
    document.getElementById('modal-op-detail').classList.remove('active');
    await refreshCurrentView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function pickDeliveryOrder(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/pick`, { method: 'POST' });
    if (!res.ok) throw new Error('Picking update failed');
    showToast('Warehouse picking completed. Items verified on cart.', 'success');
    await openOperationDetailModal(opId);
    await refreshCurrentView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function packDeliveryOrder(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/pack`, { method: 'POST' });
    if (!res.ok) throw new Error('Packing update failed');
    showToast('Packing completed. Parcel labeled and ready for dispatch.', 'success');
    await openOperationDetailModal(opId);
    await refreshCurrentView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function executeValidateOpDirect(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/validate`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Validation failed');
    }
    showToast('Transfer validated successfully. Stock quants & ledger updated.', 'success');
    await refreshCurrentView();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Stock By Location Modal ---
function showStockByLocationModal(productId) {
  const prod = state.products.find(p => p.id === productId);
  if (!prod) return;

  document.getElementById('stock-loc-modal-title').textContent = `Stock Availability: ${prod.name} (${prod.sku})`;
  const container = document.getElementById('stock-loc-modal-content');

  if (!prod.locations_stock || prod.locations_stock.length === 0) {
    container.innerHTML = '<p style="text-align: center; color: var(--text-dim); padding: 20px;">No on-hand stock recorded in internal warehouse locations.</p>';
  } else {
    container.innerHTML = `
      <table class="erp-data-table" style="border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);">
        <thead>
          <tr>
            <th>Warehouse</th>
            <th>Location / Rack Bay</th>
            <th style="text-align: right;">On Hand Quantity</th>
          </tr>
        </thead>
        <tbody>
          ${prod.locations_stock.map(loc => `
            <tr>
              <td><strong style="color: #fff;">${loc.warehouse_name || 'Main Warehouse'}</strong></td>
              <td>${loc.location_name} (<code>${loc.location_code}</code>)</td>
              <td style="text-align: right; font-weight: 700; color: #34d399; font-size: 1.05rem; font-variant-numeric: tabular-nums;">
                ${loc.quantity} ${prod.uom}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  document.getElementById('modal-stock-by-location').classList.add('active');
}

// --- Filters Setup ---
function setupFilters() {
  document.querySelectorAll('[data-op-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-op-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.filters.opType = btn.getAttribute('data-op-filter');
      loadOperationsGrid();
    });
  });

  const statusSelect = document.getElementById('ops-status-select');
  if (statusSelect) {
    statusSelect.addEventListener('change', (e) => {
      state.filters.opStatus = e.target.value;
      loadOperationsGrid();
    });
  }

  const opsSearch = document.getElementById('ops-search-input');
  if (opsSearch) {
    opsSearch.addEventListener('input', (e) => {
      state.filters.opSearch = e.target.value;
      loadOperationsGrid();
    });
  }

  const prodsSearch = document.getElementById('prods-search-input');
  if (prodsSearch) {
    prodsSearch.addEventListener('input', (e) => {
      state.filters.prodSearch = e.target.value;
      loadProductsGrid();
    });
  }

  const prodsCat = document.getElementById('prods-category-select');
  if (prodsCat) {
    prodsCat.addEventListener('change', (e) => {
      state.filters.prodCategory = e.target.value;
      loadProductsGrid();
    });
  }

  const prodsLow = document.getElementById('prods-low-stock-check');
  if (prodsLow) {
    prodsLow.addEventListener('change', (e) => {
      state.filters.prodLowStockOnly = e.target.checked;
      loadProductsGrid();
    });
  }

  const ledgerSearch = document.getElementById('ledger-search-input');
  if (ledgerSearch) {
    ledgerSearch.addEventListener('input', (e) => {
      state.filters.ledgerSearch = e.target.value;
      loadLedgerGrid();
    });
  }

  const ledgerType = document.getElementById('ledger-type-select');
  if (ledgerType) {
    ledgerType.addEventListener('change', (e) => {
      state.filters.ledgerType = e.target.value;
      loadLedgerGrid();
    });
  }

  document.getElementById('new-op-type-select').addEventListener('change', updateNewTransferLocationOptions);
}

function filterOperationsView(opType) {
  document.querySelectorAll('.nav-link, .nav-tab-btn').forEach(t => t.classList.remove('active'));
  const activeNav = document.querySelector(`[data-op-quick="${opType}"]`) || document.getElementById('nav-tab-operations');
  if (activeNav) activeNav.classList.add('active');
  switchView('operations');

  state.filters.opType = opType;
  document.querySelectorAll('[data-op-filter]').forEach(b => {
    if (b.getAttribute('data-op-filter') === opType) {
      b.classList.add('active');
    } else {
      b.classList.remove('active');
    }
  });
  loadOperationsGrid();
}

function openNewOpModalWithType(opType) {
  document.getElementById('new-op-type-select').value = opType;
  updateNewTransferLocationOptions();
  document.getElementById('modal-create-transfer').classList.add('active');
}

// --- Action Listeners & Modals ---
function setupModals() {
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.erp-modal-backdrop').forEach(m => m.classList.remove('active'));
    });
  });

  document.querySelectorAll('.erp-modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) backdrop.classList.remove('active');
    });
  });
}

function setupActionListeners() {
  // Open Create Transfer Modal
  const openCreateBtn = document.getElementById('btn-open-create-modal');
  if (openCreateBtn) {
    openCreateBtn.addEventListener('click', () => {
      document.getElementById('modal-create-transfer').classList.add('active');
    });
  }

  // Open Physical Count Modal
  const subheaderAdj = document.getElementById('btn-subheader-adjust');
  if (subheaderAdj) {
    subheaderAdj.addEventListener('click', () => {
      document.getElementById('modal-physical-count').classList.add('active');
    });
  }
  const cardRecordCount = document.getElementById('btn-card-record-count');
  if (cardRecordCount) {
    cardRecordCount.addEventListener('click', () => {
      document.getElementById('modal-physical-count').classList.add('active');
    });
  }

  // Open Create Product Modal
  const addProdBtn = document.getElementById('btn-add-product-modal');
  if (addProdBtn) {
    addProdBtn.addEventListener('click', () => {
      document.getElementById('modal-create-product').classList.add('active');
    });
  }

  // Refresh
  const refreshBtn = document.getElementById('btn-subheader-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      refreshCurrentView();
      showToast('Data refreshed from server.', 'info');
    });
  }

  // Case Study Dialog
  const runCaseStudyBtn = document.getElementById('btn-run-case-study');
  if (runCaseStudyBtn) {
    runCaseStudyBtn.addEventListener('click', () => {
      document.getElementById('modal-case-study').classList.add('active');
    });
  }

  const execCaseStudyBtn = document.getElementById('btn-execute-case-study');
  if (execCaseStudyBtn) {
    execCaseStudyBtn.addEventListener('click', executeCaseStudyFlow);
  }

  // User Profile
  const profileOpenHandler = () => {
    document.getElementById('modal-user-profile').classList.add('active');
  };
  const userProfileBtn = document.getElementById('btn-user-profile');
  if (userProfileBtn) userProfileBtn.addEventListener('click', profileOpenHandler);
  const sidebarProfileBtn = document.getElementById('btn-sidebar-profile');
  if (sidebarProfileBtn) sidebarProfileBtn.addEventListener('click', profileOpenHandler);

  const switchToManagerBtn = document.getElementById('btn-switch-to-manager');
  if (switchToManagerBtn) {
    switchToManagerBtn.addEventListener('click', () => {
      setActiveUser('Alex Rivera', 'manager@stocksense.io', 'Inventory Manager', 'AR');
    });
  }
  const switchToStaffBtn = document.getElementById('btn-switch-to-staff');
  if (switchToStaffBtn) {
    switchToStaffBtn.addEventListener('click', () => {
      setActiveUser('Sam Morgan', 'staff@stocksense.io', 'Warehouse Staff', 'SM');
    });
  }

  // OTP Simulation
  document.getElementById('btn-send-profile-otp').addEventListener('click', async () => {
    const email = document.getElementById('profile-otp-email').value;
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      document.getElementById('profile-otp-reset-panel').style.display = 'flex';
      document.getElementById('profile-otp-feedback').textContent = `OTP Token generated: ${data.simulated_otp}`;
      document.getElementById('profile-otp-code-input').value = data.simulated_otp;
      showToast(`One-time password: ${data.simulated_otp}`, 'info');
    } catch (err) {
      showToast('Error requesting OTP', 'error');
    }
  });

  document.getElementById('btn-confirm-profile-reset').addEventListener('click', async () => {
    const email = document.getElementById('profile-otp-email').value;
    const code = document.getElementById('profile-otp-code-input').value;
    const newpass = document.getElementById('profile-otp-new-password').value;

    if (!code || !newpass) {
      showToast('Please provide both OTP token and new password', 'error');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp_code: code, new_password: newpass })
      });
      if (!res.ok) throw new Error('Verification failed');
      showToast('Password credentials updated successfully.', 'success');
      document.getElementById('modal-user-profile').classList.remove('active');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Form: Create Transfer
  document.getElementById('form-create-transfer').addEventListener('submit', async (e) => {
    e.preventDefault();
    const type = document.getElementById('new-op-type-select').value;
    const partner = document.getElementById('new-op-partner').value;
    const srcId = document.getElementById('new-op-source-loc').value;
    const dstId = document.getElementById('new-op-dest-loc').value;
    const prodId = parseInt(document.getElementById('new-op-product').value);
    const qty = parseFloat(document.getElementById('new-op-qty').value);
    const notes = document.getElementById('new-op-notes').value;

    const payload = {
      operation_type: type,
      partner_name: partner,
      source_location_id: srcId ? parseInt(srcId) : null,
      destination_location_id: dstId ? parseInt(dstId) : null,
      notes: notes,
      items: [{ product_id: prodId, demanded_qty: qty, done_qty: qty }]
    };

    try {
      const res = await fetch(`${API_BASE}/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Creation failed');
      }
      showToast('Stock transfer created in Draft status.', 'success');
      document.getElementById('modal-create-transfer').classList.remove('active');
      e.target.reset();
      await refreshCurrentView();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Form: Physical Count (Stock Adjustment)
  document.getElementById('form-physical-count').addEventListener('submit', async (e) => {
    e.preventDefault();
    const prodId = parseInt(document.getElementById('adj-product-select').value);
    const locId = parseInt(document.getElementById('adj-location-select').value);
    const counted = parseFloat(document.getElementById('adj-counted-qty').value);
    const notes = document.getElementById('adj-reason-notes').value;

    try {
      const res = await fetch(`${API_BASE}/adjustments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: prodId, location_id: locId, counted_qty: counted, notes })
      });
      if (!res.ok) throw new Error('Adjustment update failed');
      showToast('Physical count adjustment reconciled & logged to ledger.', 'success');
      document.getElementById('modal-physical-count').classList.remove('active');
      await refreshCurrentView();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Form: Create Product
  document.getElementById('form-create-product').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      sku: document.getElementById('new-prod-sku').value,
      name: document.getElementById('new-prod-name').value,
      category_id: parseInt(document.getElementById('new-prod-category').value),
      uom: document.getElementById('new-prod-uom').value,
      min_reorder_qty: parseFloat(document.getElementById('new-prod-min-qty').value),
      initial_stock: parseFloat(document.getElementById('new-prod-initial-stock').value) || 0,
      description: document.getElementById('new-prod-desc').value
    };

    try {
      const res = await fetch(`${API_BASE}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Product registration failed');
      }
      showToast(`Product record '${payload.name}' registered.`, 'success');
      document.getElementById('modal-create-product').classList.remove('active');
      e.target.reset();
      await loadInitialLookups();
      await refreshCurrentView();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

function setActiveUser(name, email, role, initials) {
  state.activeUser = { name, email, role, initials };
  const userHeader = document.getElementById('user-header-name');
  if (userHeader) userHeader.textContent = name;
  const userRole = document.getElementById('user-header-role');
  if (userRole) userRole.textContent = role;
  const avatarEl = document.getElementById('user-avatar-initials');
  if (avatarEl) avatarEl.textContent = initials;
  const profileName = document.getElementById('profile-modal-name');
  if (profileName) profileName.textContent = name;
  const profileEmail = document.getElementById('profile-modal-email');
  if (profileEmail) profileEmail.textContent = email;
  const profileRole = document.getElementById('profile-modal-role');
  if (profileRole) profileRole.textContent = role;
  const otpEmail = document.getElementById('profile-otp-email');
  if (otpEmail) otpEmail.value = email;
  showToast(`Active persona: ${name} (${role})`, 'info');
}

async function executeCaseStudyFlow() {
  const btn = document.getElementById('btn-execute-case-study');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Executing...';
  }

  try {
    const res = await fetch(`${API_BASE}/demo/run-scenario`, { method: 'POST' });
    const data = await res.json();

    document.getElementById('modal-case-study').classList.remove('active');
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Execute Full Flow';
    }

    showToast('Problem statement case study flow completed successfully!', 'success');

    // Switch to Move History (Stock Ledger) view to view the audit log
    document.querySelectorAll('.nav-link, .nav-tab-btn').forEach(t => t.classList.remove('active'));
    const ledgerTab = document.getElementById('nav-tab-ledger');
    if (ledgerTab) ledgerTab.classList.add('active');
    switchView('ledger');
  } catch (err) {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Execute Full Flow';
    }
    showToast('Failed to execute case study: ' + err.message, 'error');
  }
}

// --- Helpers ---
function formatStatus(status) {
  const map = {
    'DRAFT': 'Draft',
    'WAITING': 'Waiting Availability',
    'READY': 'Ready',
    'DONE': 'Done',
    'CANCELED': 'Canceled'
  };
  return map[status] || status;
}

function getStatusPillClass(status) {
  const map = {
    'DRAFT': 'status-draft',
    'WAITING': 'status-waiting',
    'READY': 'status-ready',
    'DONE': 'status-done',
    'CANCELED': 'status-canceled'
  };
  return map[status] || 'status-draft';
}

function getTypeTag(type) {
  const map = {
    'RECEIPT': '<span class="type-tag type-receipt">Receipt</span>',
    'DELIVERY': '<span class="type-tag type-delivery">Delivery</span>',
    'INTERNAL_TRANSFER': '<span class="type-tag type-internal">Internal</span>',
    'ADJUSTMENT': '<span class="type-tag type-adjustment">Adjustment</span>'
  };
  return map[type] || type;
}
