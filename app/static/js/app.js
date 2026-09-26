// StockSense - Modular Inventory Management System Frontend

const API_BASE = '/api';

// Current State
let state = {
  activeView: 'dashboard',
  currentUser: {
    name: 'Alex Rivera',
    email: 'manager@stocksense.io',
    role: 'Inventory Manager',
    initials: 'AR'
  },
  products: [],
  warehouses: [],
  locations: [],
  categories: [],
  filters: {
    docType: '',
    status: '',
    warehouseId: '',
    categoryId: '',
    searchOps: '',
    searchProd: '',
    searchLedger: '',
    lowStockOnly: false
  }
};

// --- DOM Loaded Init ---
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupModals();
  setupFilters();
  setupActions();

  // Initial Data Fetch
  await loadLookups();
  await refreshDashboard();
});

// --- Toast System ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- Navigation Handling ---
function setupNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const view = item.getAttribute('data-view');
      const opType = item.getAttribute('data-optype');

      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      switchView(view, opType);
    });
  });
}

function switchView(viewName, opTypeFilter = null) {
  state.activeView = viewName;
  document.querySelectorAll('.app-view').forEach(view => view.style.display = 'none');

  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) targetView.style.display = 'flex';

  const titles = {
    'dashboard': 'Inventory Operations Dashboard',
    'products': 'Product Catalog & Location Quantities',
    'operations': 'Operations & Move Processing',
    'ledger': 'Stock Ledger & Complete Move History',
    'settings': 'Warehouse & Location Management'
  };
  document.getElementById('page-title').textContent = titles[viewName] || 'Inventory Dashboard';

  if (viewName === 'dashboard') {
    refreshDashboard();
  } else if (viewName === 'products') {
    loadProducts();
  } else if (viewName === 'operations') {
    if (opTypeFilter !== null) {
      state.filters.docType = opTypeFilter;
      syncFilterChips(opTypeFilter);
    }
    loadOperations();
  } else if (viewName === 'ledger') {
    loadLedger();
  } else if (viewName === 'settings') {
    renderSettingsView();
  }
}

// --- Initial Lookups Loading ---
async function loadLookups() {
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

    populateDropdowns();
  } catch (err) {
    console.error('Error loading lookups:', err);
    showToast('Failed to load initial lookups', 'error');
  }
}

function populateDropdowns() {
  // Category dropdowns
  const catFilter = document.getElementById('filter-category');
  const prodCatFilter = document.getElementById('product-category-filter');
  const prodModalCat = document.getElementById('prod-input-category');

  const catOptions = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  if (catFilter) catFilter.innerHTML = '<option value="">All Categories</option>' + catOptions;
  if (prodCatFilter) prodCatFilter.innerHTML = '<option value="">All Categories</option>' + catOptions;
  if (prodModalCat) prodModalCat.innerHTML = catOptions;

  // Warehouse dropdowns
  const whFilter = document.getElementById('filter-warehouse');
  const whOptions = state.warehouses.map(w => `<option value="${w.id}">${w.name} (${w.code})</option>`).join('');
  if (whFilter) whFilter.innerHTML = '<option value="">All Warehouses</option>' + whOptions;

  // Product dropdowns for operations
  const opProdSelect = document.getElementById('op-input-product');
  const adjProdSelect = document.getElementById('adj-input-product');
  const prodOptions = state.products.map(p => `<option value="${p.id}">${p.name} [${p.sku}] - ${p.uom}</option>`).join('');
  if (opProdSelect) opProdSelect.innerHTML = prodOptions;
  if (adjProdSelect) adjProdSelect.innerHTML = prodOptions;

  // Location dropdowns for operations
  updateOperationLocationDropdowns();
}

function updateOperationLocationDropdowns() {
  const opType = document.getElementById('op-input-type').value;
  const srcSelect = document.getElementById('op-input-source-loc');
  const dstSelect = document.getElementById('op-input-dest-loc');
  const adjLocSelect = document.getElementById('adj-input-location');

  const internalLocs = state.locations.filter(l => l.location_type === 'INTERNAL' || l.location_type === 'PRODUCTION');
  const vendorLocs = state.locations.filter(l => l.location_type === 'VENDOR');
  const customerLocs = state.locations.filter(l => l.location_type === 'CUSTOMER');

  const internalOptions = internalLocs.map(l => `<option value="${l.id}">${l.name} (${l.code})</option>`).join('');
  const vendorOptions = vendorLocs.map(l => `<option value="${l.id}">${l.name}</option>`).join('');
  const customerOptions = customerLocs.map(l => `<option value="${l.id}">${l.name}</option>`).join('');

  if (adjLocSelect) adjLocSelect.innerHTML = internalOptions;

  if (opType === 'RECEIPT') {
    document.getElementById('group-source-loc').style.display = 'none';
    document.getElementById('group-dest-loc').style.display = 'block';
    document.getElementById('group-partner').style.display = 'block';
    document.getElementById('label-partner').textContent = 'Supplier / Vendor Partner';
    dstSelect.innerHTML = internalOptions;
  } else if (opType === 'DELIVERY') {
    document.getElementById('group-source-loc').style.display = 'block';
    document.getElementById('group-dest-loc').style.display = 'none';
    document.getElementById('group-partner').style.display = 'block';
    document.getElementById('label-partner').textContent = 'Customer / Client Name';
    srcSelect.innerHTML = internalOptions;
  } else if (opType === 'INTERNAL_TRANSFER') {
    document.getElementById('group-source-loc').style.display = 'block';
    document.getElementById('group-dest-loc').style.display = 'block';
    document.getElementById('group-partner').style.display = 'none';
    srcSelect.innerHTML = internalOptions;
    dstSelect.innerHTML = internalOptions;
  }
}

// --- Dashboard & KPIs ---
async function refreshDashboard() {
  await Promise.all([
    loadKPIs(),
    loadOperations()
  ]);
}

async function loadKPIs() {
  try {
    let url = `${API_BASE}/dashboard/kpis?`;
    if (state.filters.docType) url += `doc_type=${state.filters.docType}&`;
    if (state.filters.status) url += `status=${state.filters.status}&`;
    if (state.filters.warehouseId) url += `warehouse_id=${state.filters.warehouseId}&`;
    if (state.filters.categoryId) url += `category_id=${state.filters.categoryId}&`;

    const res = await fetch(url);
    const data = await res.json();
    const kpis = data.kpis;

    document.getElementById('kpi-total-products').textContent = kpis.total_products_in_stock;
    document.getElementById('kpi-low-stock').textContent = kpis.low_stock_items_count + kpis.out_of_stock_items_count;
    document.getElementById('kpi-pending-receipts').textContent = kpis.pending_receipts_count;
    document.getElementById('kpi-pending-deliveries').textContent = kpis.pending_deliveries_count;
    document.getElementById('kpi-pending-transfers').textContent = kpis.internal_transfers_scheduled_count;

    document.getElementById('sidebar-products-badge').textContent = kpis.total_products_in_stock;
    const totalPending = kpis.pending_receipts_count + kpis.pending_deliveries_count + kpis.internal_transfers_scheduled_count;
    document.getElementById('sidebar-pending-badge').textContent = totalPending;
  } catch (err) {
    console.error('Error fetching KPIs:', err);
  }
}

// --- Operations Queue ---
async function loadOperations() {
  try {
    let url = `${API_BASE}/operations?`;
    if (state.filters.docType) url += `operation_type=${state.filters.docType}&`;
    if (state.filters.status) url += `status=${state.filters.status}&`;
    if (state.filters.searchOps) url += `search=${encodeURIComponent(state.filters.searchOps)}&`;

    const res = await fetch(url);
    const ops = await res.json();

    const tbody = document.getElementById('operations-table-body');
    if (!ops || ops.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">No operations match the selected criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = ops.map(op => {
      const typeBadgeClass = {
        'RECEIPT': 'badge-receipt',
        'DELIVERY': 'badge-delivery',
        'INTERNAL_TRANSFER': 'badge-internal',
        'ADJUSTMENT': 'badge-adjustment'
      }[op.operation_type] || '';

      const statusBadgeClass = {
        'DRAFT': 'badge-draft',
        'WAITING': 'badge-waiting',
        'READY': 'badge-ready',
        'DONE': 'badge-done',
        'CANCELED': 'badge-canceled'
      }[op.status] || '';

      const itemsSummary = op.items.map(i => `${i.product_name || i.product_sku}: ${i.done_qty || i.demanded_qty} ${i.product_uom || ''}`).join(', ');

      // Action buttons based on type and status
      let actionButtons = '';
      if (op.status !== 'DONE' && op.status !== 'CANCELED') {
        if (op.operation_type === 'DELIVERY') {
          if (!op.is_picked) {
            actionButtons += `<button class="btn btn-secondary btn-sm" onclick="handleDeliveryPick(${op.id})">🔍 Pick Items</button> `;
          } else if (!op.is_packed) {
            actionButtons += `<button class="btn btn-secondary btn-sm" onclick="handleDeliveryPack(${op.id})">📦 Pack Items</button> `;
          }
        }
        actionButtons += `<button class="btn btn-primary btn-sm" onclick="handleValidateOperation(${op.id})">✓ Validate</button> `;
        actionButtons += `<button class="btn btn-secondary btn-sm" onclick="handleCancelOperation(${op.id})">✕</button>`;
      } else {
        actionButtons = `<span style="font-size: 0.8rem; color: var(--text-muted);">Completed</span>`;
      }

      return `
        <tr>
          <td><strong style="color: #c7d2fe;">${op.reference_number}</strong></td>
          <td><span class="badge-type ${typeBadgeClass}">${op.operation_type.replace('_', ' ')}</span></td>
          <td><span class="badge-status ${statusBadgeClass}">${op.status}</span></td>
          <td>${op.source_location_name || 'External / Vendor'}</td>
          <td>${op.destination_location_name || 'External / Customer'}</td>
          <td>${op.partner_name || op.notes || '-'}</td>
          <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${itemsSummary}">${itemsSummary}</td>
          <td>${actionButtons}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading operations:', err);
  }
}

// --- Product Catalog View ---
async function loadProducts() {
  try {
    let url = `${API_BASE}/products?`;
    if (state.filters.searchProd) url += `search=${encodeURIComponent(state.filters.searchProd)}&`;
    if (state.filters.categoryId) url += `category_id=${state.filters.categoryId}&`;
    if (state.filters.lowStockOnly) url += `low_stock_only=true&`;

    const res = await fetch(url);
    state.products = await res.json();

    const tbody = document.getElementById('products-table-body');
    if (!state.products || state.products.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 30px;">No products found matching filters.</td></tr>';
      return;
    }

    tbody.innerHTML = state.products.map(p => {
      let healthBadge = `<span class="badge-status badge-done">Optimal</span>`;
      if (p.is_out_of_stock) {
        healthBadge = `<span class="badge-status badge-canceled">Out of Stock</span>`;
      } else if (p.is_low_stock) {
        healthBadge = `<span class="badge-status badge-waiting">Low Stock Alert</span>`;
      }

      return `
        <tr>
          <td><code style="color: #818cf8; background: rgba(99,102,241,0.1); padding: 2px 6px; border-radius: 4px;">${p.sku}</code></td>
          <td><strong>${p.name}</strong></td>
          <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${p.category_name}</span></td>
          <td><span style="font-size: 1.1rem; font-weight: 700; color: ${p.total_stock <= 0 ? '#ef4444' : '#f8fafc'};">${p.total_stock}</span></td>
          <td><span style="color: var(--text-muted);">${p.uom}</span></td>
          <td><span style="color: var(--text-secondary);">${p.min_reorder_qty} ${p.uom}</span></td>
          <td>${healthBadge}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="showStockLocationsModal(${p.id})">📍 Stock per Location</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading products:', err);
  }
}

// --- Stock Ledger (Move History) View ---
async function loadLedger() {
  try {
    let url = `${API_BASE}/ledger?`;
    const type = document.getElementById('ledger-type-filter').value;
    const search = document.getElementById('search-ledger').value;
    if (type) url += `operation_type=${type}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;

    const res = await fetch(url);
    const entries = await res.json();

    const tbody = document.getElementById('ledger-table-body');
    if (!entries || entries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 30px;">Stock ledger is currently empty.</td></tr>';
      return;
    }

    tbody.innerHTML = entries.map(entry => {
      const date = new Date(entry.timestamp).toLocaleString();
      const isPositive = entry.quantity_change > 0;
      const changeColor = isPositive ? 'var(--color-success)' : 'var(--color-danger)';
      const changeText = isPositive ? `+${entry.quantity_change}` : `${entry.quantity_change}`;

      return `
        <tr>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${date}</td>
          <td><strong style="color: #a5b4fc;">${entry.reference_number}</strong></td>
          <td><span class="badge-type badge-${entry.operation_type.toLowerCase()}">${entry.operation_type}</span></td>
          <td><strong>${entry.product_name || 'Product'}</strong></td>
          <td>${entry.source_location_name || '-'}</td>
          <td>${entry.destination_location_name || '-'}</td>
          <td><strong style="color: ${changeColor};">${changeText} ${entry.product_uom || ''}</strong></td>
          <td><strong>${entry.resulting_balance} ${entry.product_uom || ''}</strong></td>
          <td style="font-size: 0.8rem; color: var(--text-secondary);">${entry.created_by_name || 'System'}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${entry.notes || '-'}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading ledger:', err);
  }
}

// --- Settings & Multi-Warehouse View ---
async function renderSettingsView() {
  const whContainer = document.getElementById('warehouses-list-container');
  const locContainer = document.getElementById('locations-list-container');

  whContainer.innerHTML = state.warehouses.map(w => `
    <div style="background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 12px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <strong style="color: #f8fafc; font-size: 1rem;">${w.name}</strong>
        <code style="color: #818cf8; background: rgba(99,102,241,0.15); padding: 2px 8px; border-radius: 4px;">${w.code}</code>
      </div>
      <p style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px;">${w.address || 'Standard Facility'}</p>
    </div>
  `).join('');

  locContainer.innerHTML = state.locations.map(l => `
    <div style="background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong style="color: #f8fafc;">${l.name}</strong>
        <div style="font-size: 0.76rem; color: var(--text-muted);">${l.code}</div>
      </div>
      <span class="badge" style="background: rgba(255,255,255,0.06); color: #cbd5e1; font-size: 0.72rem;">${l.location_type}</span>
    </div>
  `).join('');
}

// --- Action Handlers ---
async function handleValidateOperation(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/validate`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Validation failed');
    }
    showToast(`Operation validated successfully! Stock balance and ledger updated.`, 'success');
    await refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDeliveryPick(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/pick`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to pick items');
    showToast('Items picked successfully from warehouse shelves.', 'success');
    await loadOperations();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDeliveryPack(opId) {
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/pack`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to pack items');
    showToast('Items packed and ready for shipping validation.', 'success');
    await loadOperations();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleCancelOperation(opId) {
  if (!confirm('Are you sure you want to cancel this operation?')) return;
  try {
    const res = await fetch(`${API_BASE}/operations/${opId}/cancel`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to cancel');
    showToast('Operation canceled.', 'info');
    await refreshDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function showStockLocationsModal(productId) {
  const prod = state.products.find(p => p.id === productId);
  if (!prod) return;

  document.getElementById('modal-stock-loc-title').textContent = `Stock Distribution: ${prod.name} (${prod.sku})`;
  const body = document.getElementById('modal-stock-loc-body');

  if (!prod.locations_stock || prod.locations_stock.length === 0) {
    body.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No physical stock recorded in internal warehouse locations.</p>';
  } else {
    body.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Warehouse</th>
            <th>Location / Bay</th>
            <th>Available Quantity</th>
          </tr>
        </thead>
        <tbody>
          ${prod.locations_stock.map(loc => `
            <tr>
              <td><strong>${loc.warehouse_name || 'Main Warehouse'}</strong></td>
              <td>${loc.location_name} (<code>${loc.location_code}</code>)</td>
              <td><strong style="color: #34d399; font-size: 1.1rem;">${loc.quantity} ${prod.uom}</strong></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  document.getElementById('modal-stock-locations').classList.add('active');
}

// --- Filters Setup ---
function setupFilters() {
  // Operation type chips
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.filters.docType = chip.getAttribute('data-filter-type');
      loadOperations();
      loadKPIs();
    });
  });

  // Status filter
  document.getElementById('filter-status').addEventListener('change', (e) => {
    state.filters.status = e.target.value;
    loadOperations();
    loadKPIs();
  });

  // Warehouse filter
  document.getElementById('filter-warehouse').addEventListener('change', (e) => {
    state.filters.warehouseId = e.target.value;
    loadKPIs();
  });

  // Category filter
  document.getElementById('filter-category').addEventListener('change', (e) => {
    state.filters.categoryId = e.target.value;
    loadKPIs();
  });

  // Live search operations
  document.getElementById('search-operations').addEventListener('input', (e) => {
    state.filters.searchOps = e.target.value;
    loadOperations();
  });

  // Products filters
  document.getElementById('search-products').addEventListener('input', (e) => {
    state.filters.searchProd = e.target.value;
    loadProducts();
  });
  document.getElementById('product-category-filter').addEventListener('change', (e) => {
    state.filters.categoryId = e.target.value;
    loadProducts();
  });
  document.getElementById('check-low-stock-only').addEventListener('change', (e) => {
    state.filters.lowStockOnly = e.target.checked;
    loadProducts();
  });

  // Ledger filters
  document.getElementById('search-ledger').addEventListener('input', loadLedger);
  document.getElementById('ledger-type-filter').addEventListener('change', loadLedger);
  document.getElementById('btn-refresh-ledger').addEventListener('click', loadLedger);
  document.getElementById('btn-refresh-operations').addEventListener('click', loadOperations);
}

function syncFilterChips(opType) {
  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach(chip => {
    if (chip.getAttribute('data-filter-type') === opType) {
      chip.classList.add('active');
    } else {
      chip.classList.remove('active');
    }
  });
}

// --- Modals Setup & Form Submissions ---
function setupModals() {
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
    });
  });

  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  });

  // Form: Create Operation
  document.getElementById('form-create-operation').addEventListener('submit', async (e) => {
    e.preventDefault();
    const type = document.getElementById('op-input-type').value;
    const partner = document.getElementById('op-input-partner').value;
    const srcId = document.getElementById('op-input-source-loc').value;
    const dstId = document.getElementById('op-input-dest-loc').value;
    const prodId = parseInt(document.getElementById('op-input-product').value);
    const qty = parseFloat(document.getElementById('op-input-qty').value);
    const notes = document.getElementById('op-input-notes').value;

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
        throw new Error(err.detail || 'Failed to create operation');
      }
      showToast('Operation created successfully!', 'success');
      document.getElementById('modal-create-operation').classList.remove('active');
      e.target.reset();
      await refreshDashboard();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Form: Stock Adjustment
  document.getElementById('form-stock-adjustment').addEventListener('submit', async (e) => {
    e.preventDefault();
    const prodId = parseInt(document.getElementById('adj-input-product').value);
    const locId = parseInt(document.getElementById('adj-input-location').value);
    const count = parseFloat(document.getElementById('adj-input-count').value);
    const notes = document.getElementById('adj-input-notes').value;

    try {
      const res = await fetch(`${API_BASE}/adjustments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: prodId, location_id: locId, counted_qty: count, notes: notes })
      });
      if (!res.ok) throw new Error('Adjustment failed');
      showToast('Physical count adjustment applied and logged to ledger!', 'success');
      document.getElementById('modal-stock-adjustment').classList.remove('active');
      await refreshDashboard();
      await loadProducts();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Form: New Product
  document.getElementById('form-new-product').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      sku: document.getElementById('prod-input-sku').value,
      name: document.getElementById('prod-input-name').value,
      category_id: parseInt(document.getElementById('prod-input-category').value),
      uom: document.getElementById('prod-input-uom').value,
      min_reorder_qty: parseFloat(document.getElementById('prod-input-min').value),
      initial_stock: parseFloat(document.getElementById('prod-input-stock').value) || 0,
      description: document.getElementById('prod-input-desc').value
    };

    try {
      const res = await fetch(`${API_BASE}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create product');
      }
      showToast(`Product '${payload.name}' registered successfully!`, 'success');
      document.getElementById('modal-new-product').classList.remove('active');
      e.target.reset();
      await loadLookups();
      await loadProducts();
      await loadKPIs();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  document.getElementById('op-input-type').addEventListener('change', updateOperationLocationDropdowns);
}

// --- Action Buttons ---
function setupActions() {
  document.getElementById('btn-quick-create-op').addEventListener('click', () => {
    document.getElementById('modal-create-operation').classList.add('active');
  });

  document.getElementById('btn-quick-adjust').addEventListener('click', () => {
    document.getElementById('modal-stock-adjustment').classList.add('active');
  });

  document.getElementById('btn-modal-new-product').addEventListener('click', () => {
    document.getElementById('modal-new-product').classList.add('active');
  });

  document.getElementById('btn-profile-card').addEventListener('click', () => {
    document.getElementById('modal-profile').classList.add('active');
  });

  // Persona Switcher
  document.getElementById('btn-switch-manager').addEventListener('click', () => {
    setPersona('Alex Rivera', 'manager@stocksense.io', 'Inventory Manager', 'AR');
  });
  document.getElementById('btn-switch-staff').addEventListener('click', () => {
    setPersona('Sam Morgan', 'staff@stocksense.io', 'Warehouse Staff', 'SM');
  });

  // OTP Simulation
  document.getElementById('btn-request-otp').addEventListener('click', async () => {
    const email = document.getElementById('otp-input-email').value;
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      });
      const data = await res.json();
      document.getElementById('otp-verify-section').style.display = 'flex';
      document.getElementById('otp-display-message').innerHTML = `<strong>OTP Sent:</strong> Code <code>${data.simulated_otp}</code> generated for testing.`;
      document.getElementById('otp-input-code').value = data.simulated_otp;
      showToast(`OTP Code generated: ${data.simulated_otp}`, 'info');
    } catch (err) {
      showToast('Error generating OTP', 'error');
    }
  });

  document.getElementById('btn-confirm-otp').addEventListener('click', async () => {
    const email = document.getElementById('otp-input-email').value;
    const code = document.getElementById('otp-input-code').value;
    const newpass = document.getElementById('otp-input-newpass').value;

    if (!code || !newpass) {
      showToast('Please enter both OTP code and new password', 'error');
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, otp_code: code, new_password: newpass })
      });
      if (!res.ok) throw new Error('Failed to reset password');
      showToast('Password reset verified and updated successfully!', 'success');
      document.getElementById('modal-profile').classList.remove('active');
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // 4-Step Problem Statement Demo Flow
  document.getElementById('btn-run-demo-scenario').addEventListener('click', runDemoScenario);
  document.getElementById('btn-close-demo-card').addEventListener('click', () => {
    document.getElementById('demo-flow-card').style.display = 'none';
  });
}

function setPersona(name, email, role, initials) {
  state.currentUser = { name, email, role, initials };
  document.getElementById('user-display-name').textContent = name;
  document.getElementById('user-display-role').textContent = role;
  document.getElementById('avatar-initials').textContent = initials;
  document.getElementById('modal-profile-name').textContent = name;
  document.getElementById('modal-profile-email').textContent = email;
  document.getElementById('modal-profile-role').textContent = role;
  document.getElementById('modal-profile-avatar').textContent = initials;
  showToast(`Switched active user to ${name} (${role})`, 'info');
}

async function runDemoScenario() {
  const card = document.getElementById('demo-flow-card');
  card.style.display = 'flex';

  const steps = [1, 2, 3, 4];
  steps.forEach(s => {
    const el = document.getElementById(`flow-step-${s}`);
    el.classList.remove('completed', 'active');
  });

  showToast('Starting 4-Step Problem Statement Lifecycle...', 'info');

  try {
    const res = await fetch(`${API_BASE}/demo/run-scenario`, { method: 'POST' });
    const data = await res.json();

    // Animate steps
    for (let i = 0; i < data.steps.length; i++) {
      const stepData = data.steps[i];
      const stepEl = document.getElementById(`flow-step-${i + 1}`);
      stepEl.classList.add('active');
      await new Promise(r => setTimeout(r, 600));
      stepEl.classList.remove('active');
      stepEl.classList.add('completed');
      showToast(`Step ${stepData.step}: ${stepData.action} (${stepData.stock_change})`, 'success');
    }

    await refreshDashboard();
    await loadProducts();
    await loadLedger();

    showToast('Demo lifecycle finished! Check Move History (Ledger) to view the complete audit log.', 'success');
  } catch (err) {
    showToast('Failed to run demo scenario: ' + err.message, 'error');
  }
}
