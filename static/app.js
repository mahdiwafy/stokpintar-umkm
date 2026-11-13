// Global State
let allItems = [];
let cart = [];
let categories = [];
let currentAuditItem = null;
let selectedReceiptFile = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  loadApiKey();
  loadData();
  setupDropZone();
});

function loadApiKey() {
  const saved = localStorage.getItem("stokpintar_gemini_api_key") || "";
  const input = document.getElementById("inputUserApiKey");
  if (input) input.value = saved;
}

function saveApiKey() {
  const input = document.getElementById("inputUserApiKey");
  const key = input ? input.value.trim() : "";
  localStorage.setItem("stokpintar_gemini_api_key", key);
  showToast(key ? "Kunci Google AI tersimpan!" : "Kunci Google AI dihapus (mode simulasi aktif).", "success");
  closeApiKeyModal();
}

function getStoredApiKey() {
  return localStorage.getItem("stokpintar_gemini_api_key") || "";
}

// Navigation Tabs
function switchTab(tab) {
  const tabs = ["kasir", "stok", "kulakan", "laporan"];
  tabs.forEach(t => {
    const sec = document.getElementById(`section-${t}`);
    const btn = document.getElementById(`tab-${t}`);
    if (t === tab) {
      if (sec) sec.classList.remove("hidden");
      if (btn) {
        btn.classList.add("active-tab");
        btn.classList.remove("text-slate-600", "hover:bg-slate-100");
      }
    } else {
      if (sec) sec.classList.add("hidden");
      if (btn) {
        btn.classList.remove("active-tab");
        btn.classList.add("text-slate-600", "hover:bg-slate-100");
      }
    }
  });

  if (tab === "stok") renderInventoryTable();
  if (tab === "laporan") {
    loadSummary();
    loadRecentTransactions();
  }
}

// Data Fetching
async function loadData() {
  try {
    const [itemsRes, catRes, sumRes] = await Promise.all([
      fetch("/api/items"),
      fetch("/api/items/categories"),
      fetch("/api/transactions/summary")
    ]);

    allItems = await itemsRes.json();
    categories = await catRes.json();
    const summary = await sumRes.json();

    updateHeaderSummary(summary);
    populateCategoryFilters();
    renderPosCatalog();
    renderInventoryTable();
  } catch (err) {
    console.error("Gagal memuat data:", err);
    showToast("Gagal terhubung ke server", "error");
  }
}

function updateHeaderSummary(summary) {
  const el = document.getElementById("headerTodaySales");
  if (el) el.innerText = formatRupiah(summary.today_sales_revenue);

  const badge = document.getElementById("badgeLowStock");
  if (badge) {
    if (summary.critical_stock_count > 0) {
      badge.innerText = summary.critical_stock_count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  // Update report stats if present
  const rev = document.getElementById("statRevenue");
  if (rev) rev.innerText = formatRupiah(summary.today_sales_revenue);
  const sc = document.getElementById("statSalesCount");
  if (sc) sc.innerText = `${summary.today_sales_count} transaksi lunas`;

  const exp = document.getElementById("statExpense");
  if (exp) exp.innerText = formatRupiah(summary.today_restock_expense);
  const rc = document.getElementById("statRestockCount");
  if (rc) rc.innerText = `${summary.today_restock_count} pengadaan stok`;

  const net = document.getElementById("statNetCash");
  if (net) {
    net.innerText = formatRupiah(summary.net_cashflow_today);
    net.className = summary.net_cashflow_today >= 0 ? "text-lg sm:text-xl font-bold text-emerald-600" : "text-lg sm:text-xl font-bold text-rose-600";
  }

  const crit = document.getElementById("statCriticalStock");
  if (crit) crit.innerText = summary.critical_stock_count;
}

function populateCategoryFilters() {
  const posSelect = document.getElementById("posCategoryFilter");
  if (!posSelect) return;

  const currentVal = posSelect.value;
  posSelect.innerHTML = `<option value="Semua">Semua Kategori</option>`;
  categories.forEach(c => {
    posSelect.innerHTML += `<option value="${c}">${c}</option>`;
  });
  posSelect.value = currentVal || "Semua";
}

// POS Catalog & Cart Logic
function renderPosCatalog() {
  const grid = document.getElementById("posCatalogGrid");
  if (!grid) return;

  const search = (document.getElementById("posSearch")?.value || "").toLowerCase();
  const cat = document.getElementById("posCategoryFilter")?.value || "Semua";

  const filtered = allItems.filter(it => {
    const matchSearch = it.name.toLowerCase().includes(search) || (it.barcode && it.barcode.toLowerCase().includes(search));
    const matchCat = cat === "Semua" || it.category === cat;
    return matchSearch && matchCat;
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="col-span-full py-12 text-center text-xs text-slate-400">Tidak ada barang yang cocok.</div>`;
    return;
  }

  grid.innerHTML = filtered.map(it => {
    const isOut = it.current_stock <= 0;
    const isLow = it.current_stock <= it.min_stock;
    
    let stockBadge = `<span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-md font-bold text-[10px]">${it.current_stock} ${it.unit}</span>`;
    if (isOut) {
      stockBadge = `<span class="px-2 py-0.5 bg-rose-100 text-rose-800 rounded-md font-bold text-[10px]">Habis (0)</span>`;
    } else if (isLow) {
      stockBadge = `<span class="px-2 py-0.5 bg-amber-100 text-amber-800 rounded-md font-bold text-[10px]">Tersisa ${it.current_stock} ${it.unit}</span>`;
    }

    return `
      <div onclick="${isOut ? '' : `addToCart(${it.id})`}" 
           class="pos-card bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between cursor-pointer select-none ${isOut ? 'opacity-60 cursor-not-allowed bg-slate-50' : 'hover:border-brand-500'}">
        <div>
          <div class="flex items-start justify-between gap-1 mb-1">
            <span class="text-[10px] uppercase font-bold text-slate-400 truncate">${it.category}</span>
            ${stockBadge}
          </div>
          <h4 class="text-xs sm:text-sm font-bold text-slate-900 line-clamp-2 leading-tight">${it.name}</h4>
        </div>
        <div class="mt-3 flex items-center justify-between pt-2 border-t border-slate-100">
          <span class="text-xs sm:text-sm font-bold text-brand-700">${formatRupiah(it.selling_price)}</span>
          <button class="w-7 h-7 rounded-lg ${isOut ? 'bg-slate-200 text-slate-400' : 'bg-brand-50 hover:bg-brand-600 hover:text-white text-brand-700'} flex items-center justify-center transition">
            <i class="ph ph-plus font-bold text-sm"></i>
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function addToCart(itemId) {
  const item = allItems.find(it => it.id === itemId);
  if (!item) return;

  const existing = cart.find(c => c.item_id === itemId);
  const currentInCart = existing ? existing.quantity : 0;

  if (currentInCart + 1 > item.current_stock) {
    showToast(`Stok fisik ${item.name} hanya tersisa ${item.current_stock} ${item.unit}!`, "warning");
    return;
  }

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      item_id: item.id,
      name: item.name,
      unit: item.unit,
      price: item.selling_price,
      max_stock: item.current_stock,
      quantity: 1
    });
  }

  renderCart();
}

function updateCartQty(itemId, delta) {
  const entry = cart.find(c => c.item_id === itemId);
  if (!entry) return;

  const newQty = entry.quantity + delta;
  if (newQty <= 0) {
    cart = cart.filter(c => c.item_id !== itemId);
  } else {
    if (newQty > entry.max_stock) {
      showToast(`Maksimal stok tersedia hanya ${entry.max_stock} ${entry.unit}!`, "warning");
      return;
    }
    entry.quantity = newQty;
  }
  renderCart();
}

function clearCart() {
  cart = [];
  renderCart();
}

function renderCart() {
  const container = document.getElementById("cartItemsList");
  const totalItemsEl = document.getElementById("cartTotalItems");
  const totalPriceEl = document.getElementById("cartTotalPrice");
  const btnCheckout = document.getElementById("btnCheckout");

  if (!container) return;

  if (cart.length === 0) {
    container.innerHTML = `<p class="text-center py-8 text-xs text-slate-400">Keranjang masih kosong.<br>Klik barang di katalog untuk menambahkan.</p>`;
    if (totalItemsEl) totalItemsEl.innerText = "0";
    if (totalPriceEl) totalPriceEl.innerText = "Rp 0";
    if (btnCheckout) {
      btnCheckout.disabled = true;
      btnCheckout.innerHTML = `<i class="ph ph-check-circle text-lg"></i><span>Bayar & Potong Stok</span>`;
    }
    return;
  }

  let totalItems = 0;
  let totalPrice = 0;

  container.innerHTML = cart.map(c => {
    const subtotal = c.price * c.quantity;
    totalItems += c.quantity;
    totalPrice += subtotal;

    return `
      <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
        <div class="flex-1 min-w-0 pr-2">
          <p class="font-bold text-slate-900 truncate">${c.name}</p>
          <p class="text-slate-500 text-[11px]">${formatRupiah(c.price)} / ${c.unit}</p>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex items-center border border-slate-300 rounded-lg bg-white overflow-hidden">
            <button onclick="updateCartQty(${c.item_id}, -1)" class="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-slate-100 font-bold">-</button>
            <span class="w-7 text-center font-bold text-slate-900">${c.quantity}</span>
            <button onclick="updateCartQty(${c.item_id}, 1)" class="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-slate-100 font-bold">+</button>
          </div>
          <span class="font-bold text-slate-900 w-16 text-right">${formatRupiah(subtotal)}</span>
        </div>
      </div>
    `;
  }).join("");

  if (totalItemsEl) totalItemsEl.innerText = totalItems;
  if (totalPriceEl) totalPriceEl.innerText = formatRupiah(totalPrice);
  if (btnCheckout) {
    btnCheckout.disabled = false;
    btnCheckout.innerHTML = `<i class="ph ph-check-circle text-lg"></i><span>Bayar (${formatRupiah(totalPrice)}) & Potong Stok</span>`;
  }
}

async function checkoutSale() {
  if (cart.length === 0) return;

  const btn = document.getElementById("btnCheckout");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-spinner animate-spin text-lg"></i><span>Memproses...</span>`;

  try {
    const payload = {
      items: cart.map(c => ({ item_id: c.item_id, quantity: c.quantity, price_per_unit: c.price })),
      notes: "Penjualan Kasir Cepat"
    };

    const res = await fetch("/api/transactions/sale", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Gagal memproses transaksi");
    }

    showToast(`Transaksi Rp ${formatRupiah(data.total_amount)} lunas! Stok berhasil dipotong otomatis.`, "success");
    clearCart();
    await loadData();
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    renderCart();
  }
}

// AI Voice / Natural Sale Parser
async function submitNaturalSale() {
  const input = document.getElementById("aiSaleInput");
  const text = input ? input.value.trim() : "";
  if (!text) return;

  const btn = document.getElementById("btnAiParse");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-spinner animate-spin text-base"></i>`;

  try {
    const apiKey = getStoredApiKey();
    const res = await fetch(`/api/ai/parse-sale-prompt${apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ""}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: text })
    });

    const result = await res.json();
    const recognized = result.data?.recognized_items || [];

    if (recognized.length === 0) {
      showToast("AI tidak menemukan barang yang cocok dari ucapan Anda.", "warning");
      return;
    }

    let addedCount = 0;
    recognized.forEach(rec => {
      const it = allItems.find(i => i.id === rec.item_id);
      if (it) {
        const qty = rec.quantity || 1;
        const existing = cart.find(c => c.item_id === it.id);
        if (existing) {
          existing.quantity = Math.min(existing.quantity + qty, it.current_stock);
        } else {
          cart.push({
            item_id: it.id,
            name: it.name,
            unit: it.unit,
            price: it.selling_price,
            max_stock: it.current_stock,
            quantity: Math.min(qty, it.current_stock)
          });
        }
        addedCount++;
      }
    });

    renderCart();
    input.value = "";
    showToast(`AI berhasil memasukkan ${addedCount} barang ke keranjang!`, "success");
  } catch (err) {
    showToast("Gagal memproses bahasa alami via AI", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph ph-magic-wand text-base"></i><span class="hidden sm:inline">Proses AI</span>`;
  }
}

// Inventory Table & Physical Audit
function renderInventoryTable() {
  const tbody = document.getElementById("inventoryTableBody");
  if (!tbody) return;

  if (allItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">Belum ada barang di database.</td></tr>`;
    return;
  }

  tbody.innerHTML = allItems.map(it => {
    const isOut = it.current_stock <= 0;
    const isLow = it.current_stock <= it.min_stock;

    let badge = `<span class="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full font-bold text-[10px]">Aman</span>`;
    if (isOut) {
      badge = `<span class="px-2.5 py-1 bg-rose-100 text-rose-800 rounded-full font-bold text-[10px]">Habis (0)</span>`;
    } else if (isLow) {
      badge = `<span class="px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full font-bold text-[10px]">Menipis (&le; ${it.min_stock})</span>`;
    }

    return `
      <tr class="hover:bg-slate-50/80 transition">
        <td class="p-3 sm:p-4 font-bold text-slate-900">${it.name}</td>
        <td class="p-3 sm:p-4 text-slate-500">${it.category}</td>
        <td class="p-3 sm:p-4 text-right text-slate-600">${formatRupiah(it.cost_price)}</td>
        <td class="p-3 sm:p-4 text-right font-bold text-brand-700">${formatRupiah(it.selling_price)}</td>
        <td class="p-3 sm:p-4 text-center font-bold ${isLow ? 'text-rose-600' : 'text-slate-800'}">${it.current_stock} <span class="font-normal text-[11px] text-slate-400">${it.unit}</span></td>
        <td class="p-3 sm:p-4 text-center">${badge}</td>
        <td class="p-3 sm:p-4 text-center">
          <button onclick="openAuditModal(${it.id})" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition">
            <i class="ph ph-clipboard-text"></i>
            <span>Audit Fisik</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function openAuditModal(itemId) {
  const item = allItems.find(it => it.id === itemId);
  if (!item) return;

  currentAuditItem = item;
  document.getElementById("auditItemName").innerText = `${item.name} (${item.unit})`;
  document.getElementById("auditOldStock").innerText = `${item.current_stock} ${item.unit}`;
  document.getElementById("auditActualStock").value = item.current_stock;
  document.getElementById("auditNotes").value = "";

  document.getElementById("auditModal").classList.remove("hidden");
}

function closeAuditModal() {
  document.getElementById("auditModal").classList.add("hidden");
  currentAuditItem = null;
}

async function submitStockAdjustment() {
  if (!currentAuditItem) return;

  const actual = parseFloat(document.getElementById("auditActualStock").value);
  const notes = document.getElementById("auditNotes").value.trim() || "Penyesuaian stok berkala";

  if (isNaN(actual) || actual < 0) {
    alert("Jumlah stok fisik harus berupa angka positif!");
    return;
  }

  try {
    const res = await fetch(`/api/items/${currentAuditItem.id}/adjust`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actual_stock: actual, notes: notes })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Gagal menyesuaikan stok");

    showToast(data.message, "success");
    closeAuditModal();
    await loadData();
  } catch (err) {
    alert(err.message);
  }
}

// Add Item Modal
function openAddItemModal() {
  document.getElementById("addItemModal").classList.remove("hidden");
}

function closeAddItemModal() {
  document.getElementById("addItemModal").classList.add("hidden");
}

async function submitNewItem(e) {
  e.preventDefault();
  const name = document.getElementById("newItemName").value.trim();
  const category = document.getElementById("newItemCategory").value.trim() || "Umum";
  const unit = document.getElementById("newItemUnit").value.trim() || "pcs";
  const cost = parseFloat(document.getElementById("newItemCost").value) || 0;
  const price = parseFloat(document.getElementById("newItemPrice").value) || 0;
  const stock = parseFloat(document.getElementById("newItemStock").value) || 0;
  const minStock = parseFloat(document.getElementById("newItemMinStock").value) || 3;

  try {
    const res = await fetch("/api/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, category, unit,
        cost_price: cost,
        selling_price: price,
        current_stock: stock,
        min_stock: minStock
      })
    });

    if (!res.ok) throw new Error("Gagal menyimpan barang baru");
    showToast(`Barang "${name}" berhasil ditambahkan!`, "success");
    closeAddItemModal();
    document.getElementById("formAddItem").reset();
    await loadData();
  } catch (err) {
    alert(err.message);
  }
}

// Dropzone & Receipt OCR (Gemini Vision)
function setupDropZone() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("receiptFileInput");
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleReceiptFile(e.target.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-indigo-100/50");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-indigo-100/50");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-indigo-100/50");
    if (e.dataTransfer.files.length > 0) {
      handleReceiptFile(e.dataTransfer.files[0]);
    }
  });
}

function handleReceiptFile(file) {
  selectedReceiptFile = file;
  document.getElementById("receiptFileName").innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  document.getElementById("receiptPreviewContainer").classList.remove("hidden");
  showToast("Nota siap diproses via Gemini Vision", "info");
}

async function processReceiptAI() {
  if (!selectedReceiptFile) return;

  const btn = document.getElementById("btnProcessReceipt");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-spinner animate-spin"></i><span>Membaca via Gemini...</span>`;

  try {
    const formData = new FormData();
    formData.append("file", selectedReceiptFile);
    const apiKey = getStoredApiKey();
    if (apiKey) formData.append("api_key", apiKey);

    const res = await fetch("/api/ai/parse-receipt", {
      method: "POST",
      body: formData
    });

    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || "Gagal membaca nota");

    const items = result.data?.items || [];
    if (items.length === 0) {
      showToast("Nota terbaca namun tidak ada baris barang yang terdeteksi.", "warning");
      return;
    }

    populateRestockRowsFromAI(items);
    showToast(`Berhasil mengekstrak ${items.length} barang dari nota!`, "success");
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph ph-sparkle"></i><span>Ekstrak Isi Nota</span>`;
  }
}

function populateRestockRowsFromAI(items) {
  const container = document.getElementById("restockRowsContainer");
  if (!container) return;

  container.innerHTML = "";
  items.forEach(it => {
    // Try to match with existing item
    const match = allItems.find(x => x.name.toLowerCase().includes(it.name.toLowerCase()) || it.name.toLowerCase().includes(x.name.toLowerCase()));
    addRestockRow(match ? match.id : null, it.name, it.quantity || 1, it.cost_price || 0);
  });

  recalculateRestockTotal();
}

function addEmptyRestockRow() {
  addRestockRow(null, "", 1, 0);
}

function addRestockRow(selectedItemId, customName, qty, cost) {
  const container = document.getElementById("restockRowsContainer");
  if (!container) return;

  const rowId = "restock-" + Math.random().toString(36).substr(2, 9);
  const options = allItems.map(it => `
    <option value="${it.id}" ${selectedItemId === it.id ? "selected" : ""}>${it.name} (Stok: ${it.current_stock} ${it.unit})</option>
  `).join("");

  const div = document.createElement("div");
  div.id = rowId;
  div.className = "bg-slate-50 p-3 rounded-xl border border-slate-200 grid grid-cols-12 gap-2 items-center text-xs";
  div.innerHTML = `
    <div class="col-span-5">
      <label class="block text-[10px] text-slate-500 font-bold mb-0.5">Barang</label>
      <select class="w-full p-2 bg-white border border-slate-300 rounded-lg outline-none font-semibold restock-item-select" onchange="onRestockSelectChange('${rowId}')">
        <option value="">-- Barang Baru --</option>
        ${options}
      </select>
      <input type="text" class="w-full mt-1 p-2 bg-white border border-slate-300 rounded-lg outline-none restock-item-custom-name ${selectedItemId ? 'hidden' : ''}" placeholder="Nama barang baru" value="${customName || ''}">
    </div>
    <div class="col-span-3">
      <label class="block text-[10px] text-slate-500 font-bold mb-0.5">Jumlah</label>
      <input type="number" min="0.1" step="any" value="${qty}" class="w-full p-2 bg-white border border-slate-300 rounded-lg outline-none font-bold restock-qty" oninput="recalculateRestockTotal()">
    </div>
    <div class="col-span-3">
      <label class="block text-[10px] text-slate-500 font-bold mb-0.5">Harga Beli</label>
      <input type="number" min="0" step="any" value="${cost}" class="w-full p-2 bg-white border border-slate-300 rounded-lg outline-none font-bold restock-cost" oninput="recalculateRestockTotal()">
    </div>
    <div class="col-span-1 text-center pt-3">
      <button onclick="document.getElementById('${rowId}').remove(); recalculateRestockTotal();" class="text-rose-500 hover:text-rose-700"><i class="ph ph-trash text-base"></i></button>
    </div>
  `;

  container.appendChild(div);
  recalculateRestockTotal();
}

function onRestockSelectChange(rowId) {
  const row = document.getElementById(rowId);
  if (!row) return;

  const select = row.querySelector(".restock-item-select");
  const custom = row.querySelector(".restock-item-custom-name");
  const costInput = row.querySelector(".restock-cost");

  if (select.value) {
    custom.classList.add("hidden");
    const it = allItems.find(x => x.id === parseInt(select.value));
    if (it && costInput) costInput.value = it.cost_price;
  } else {
    custom.classList.remove("hidden");
  }

  recalculateRestockTotal();
}

function recalculateRestockTotal() {
  const container = document.getElementById("restockRowsContainer");
  if (!container) return;

  let total = 0;
  const rows = container.children;
  for (let r of rows) {
    const qty = parseFloat(r.querySelector(".restock-qty")?.value) || 0;
    const cost = parseFloat(r.querySelector(".restock-cost")?.value) || 0;
    total += qty * cost;
  }

  const el = document.getElementById("restockTotalCost");
  if (el) el.innerText = formatRupiah(total);
}

async function submitRestock() {
  const container = document.getElementById("restockRowsContainer");
  if (!container || container.children.length === 0) {
    alert("Daftar kulakan kosong! Silakan scan nota atau tambah baris barang.");
    return;
  }

  const items = [];
  for (let r of container.children) {
    const select = r.querySelector(".restock-item-select");
    const custom = r.querySelector(".restock-item-custom-name");
    const qty = parseFloat(r.querySelector(".restock-qty")?.value) || 0;
    const cost = parseFloat(r.querySelector(".restock-cost")?.value) || 0;

    if (qty <= 0) continue;

    if (select.value) {
      items.push({
        item_id: parseInt(select.value),
        quantity: qty,
        cost_price: cost
      });
    } else if (custom && custom.value.trim()) {
      items.push({
        name: custom.value.trim(),
        quantity: qty,
        cost_price: cost
      });
    }
  }

  if (items.length === 0) {
    alert("Mohon isi nama barang dan jumlah kulakan dengan benar.");
    return;
  }

  const btn = document.getElementById("btnSaveRestock");
  btn.disabled = true;

  try {
    const res = await fetch("/api/transactions/restock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, notes: "Kulakan Stok Baru" })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Gagal menyimpan kulakan");

    showToast(`Kulakan berhasil disimpan! Total Rp ${formatRupiah(data.total_expense)}. Stok bertambah.`, "success");
    container.innerHTML = "";
    recalculateRestockTotal();
    await loadData();
    switchTab("stok");
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
  }
}

// AI Stock Advisor
async function fetchStockAdvice() {
  const btn = document.getElementById("btnFetchAdvice");
  const content = document.getElementById("aiAdviceContent");
  if (!btn || !content) return;

  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-spinner animate-spin text-sm"></i><span>Menganalisis...</span>`;

  try {
    const apiKey = getStoredApiKey();
    const res = await fetch(`/api/ai/stock-advice${apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : ""}`);
    const result = await res.json();

    const data = result.data || {};
    let html = "";

    if (data.summary) {
      html += `<p class="font-bold text-emerald-400 mb-2"><i class="ph ph-check-circle inline"></i> ${data.summary}</p>`;
    }

    if (data.urgent_restock && Array.isArray(data.urgent_restock)) {
      html += `<div class="space-y-1.5 my-2">`;
      data.urgent_restock.forEach(ur => {
        html += `
          <div class="bg-white/10 p-2.5 rounded-lg border border-white/10 flex justify-between items-center text-xs">
            <div>
              <span class="font-bold text-white">${ur.item_name}</span>
              <span class="text-rose-300 block text-[11px]">${ur.reason || 'Stok kritis'}</span>
            </div>
            <span class="px-2 py-1 bg-amber-400 text-slate-950 font-bold rounded text-[11px]">Saran Beli: +${ur.suggested_buy_qty}</span>
          </div>
        `;
      });
      html += `</div>`;
    } else if (data.action_items && Array.isArray(data.action_items)) {
      html += `<ul class="list-disc list-inside space-y-1 my-2 text-slate-300">`;
      data.action_items.forEach(a => html += `<li>${a}</li>`);
      html += `</ul>`;
    }

    if (data.estimated_budget) {
      html += `<p class="text-xs text-slate-300 mt-3 pt-2 border-t border-white/10">Estimasi Modal Kulakan yang Disiapkan: <strong class="text-white">${formatRupiah(data.estimated_budget)}</strong></p>`;
    }

    content.innerHTML = html;
  } catch (err) {
    content.innerHTML = `<p class="text-rose-400 text-xs">Gagal mengambil analisis AI: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph ph-arrows-clockwise text-sm"></i><span>Minta Analisis AI</span>`;
  }
}

// Recent Transactions
async function loadRecentTransactions() {
  const container = document.getElementById("recentTxTable");
  if (!container) return;

  try {
    const res = await fetch("/api/transactions?limit=15");
    const list = await res.json();

    if (list.length === 0) {
      container.innerHTML = `<p class="text-center py-6 text-xs text-slate-400">Belum ada riwayat transaksi.</p>`;
      return;
    }

    container.innerHTML = list.map(tx => {
      let typeBadge = `<span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold text-[10px]">PENJUALAN</span>`;
      let amountClass = "text-emerald-700 font-bold";
      let prefix = "+";

      if (tx.type === "restock") {
        typeBadge = `<span class="px-2 py-0.5 bg-rose-100 text-rose-800 rounded font-bold text-[10px]">KULAKAN</span>`;
        amountClass = "text-rose-600 font-bold";
        prefix = "-";
      } else if (tx.type === "adjustment") {
        typeBadge = `<span class="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded font-bold text-[10px]">AUDIT FISIK</span>`;
        amountClass = "text-indigo-600 font-bold";
        prefix = "";
      }

      return `
        <div class="bg-slate-50 p-2.5 rounded-xl border border-slate-200 flex items-center justify-between text-xs">
          <div class="flex items-center gap-2">
            ${typeBadge}
            <div>
              <p class="font-semibold text-slate-900">${tx.notes || '-'}</p>
              <p class="text-[10px] text-slate-400">${tx.created_at}</p>
            </div>
          </div>
          <span class="${amountClass} text-sm">${prefix}${formatRupiah(tx.total_amount)}</span>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Gagal memuat riwayat transaksi:", err);
  }
}

// Modals
function openApiKeyModal() {
  loadApiKey();
  document.getElementById("apiKeyModal")?.classList.remove("hidden");
}

function closeApiKeyModal() {
  document.getElementById("apiKeyModal")?.classList.add("hidden");
}

// Helpers
function formatRupiah(num) {
  if (isNaN(num)) num = 0;
  return "Rp " + Math.round(num).toLocaleString("id-ID");
}

function showToast(msg, type = "info") {
  const toast = document.getElementById("toast");
  if (!toast) return;

  let bg = "bg-slate-900 text-white";
  let icon = "ph-info";
  if (type === "success") {
    bg = "bg-emerald-600 text-white";
    icon = "ph-check-circle";
  } else if (type === "warning") {
    bg = "bg-amber-500 text-white";
    icon = "ph-warning";
  } else if (type === "error") {
    bg = "bg-rose-600 text-white";
    icon = "ph-x-circle";
  }

  toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2 transition transform duration-300 ${bg}`;
  toast.innerHTML = `<i class="ph ${icon} text-lg"></i><span>${msg}</span>`;
  toast.classList.remove("hidden");

  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3500);
}
