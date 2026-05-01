/* global APP_CONFIG */

(function initInventoryModule(globalScope) {
  const CART_STORAGE_KEY = "blackwhale_cart";
  const ORDER_HISTORY_KEY = "blackwhale_purchase_history";

  const localInventoryItems = [
    {
      id: 101,
      name: "Wireless Headphones",
      price: 79.99,
      quantity: 5,
      category: "Electronics",
      description: "High-quality wireless headphones with noise cancellation",
      seller: "TechStore",
      rating: 4.5
    },
    {
      id: 102,
      name: "USB-C Cable",
      price: 12.99,
      quantity: 20,
      category: "Electronics",
      description: "Durable 6ft USB-C charging cable",
      seller: "CableWorld",
      rating: 4.8
    },
    {
      id: 103,
      name: "Laptop Stand",
      price: 34.99,
      quantity: 8,
      category: "Office",
      description: "Adjustable aluminum laptop stand",
      seller: "OfficeGear",
      rating: 4.3
    },
    {
      id: 104,
      name: "Mechanical Keyboard",
      price: 89.99,
      quantity: 3,
      category: "Electronics",
      description: "RGB mechanical keyboard with mechanical switches",
      seller: "PeripheralPro",
      rating: 4.7
    },
    {
      id: 105,
      name: "Phone Stand",
      price: 15.99,
      quantity: 12,
      category: "Accessories",
      description: "Adjustable phone stand for desk",
      seller: "AccessoryHub",
      rating: 4.2
    }
  ];

  const config = globalScope.APP_CONFIG || {};
  const mode = config.dataMode || "local";
  const apiBaseUrl = config.apiBaseUrl || "";

  let inventoryItems = [...localInventoryItems];
  let purchaseHistory = [];

  const currentFilter = {
    category: "all",
    maxPrice: 1000,
    minRating: 0,
    searchTerm: ""
  };

  let currentSort = "name";

  function formatPrice(value) {
    return `$${Number(value).toFixed(2)}`;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  async function request(path, options = {}) {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    return response.json();
  }

  function readSharedPurchaseHistory() {
    try {
      const raw = localStorage.getItem(ORDER_HISTORY_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn("Unable to load purchase history.", error);
      return [];
    }
  }

  function saveSharedPurchaseHistory(history) {
    try {
      localStorage.setItem(ORDER_HISTORY_KEY, JSON.stringify(history));
    } catch (error) {
      console.warn("Unable to save purchase history.", error);
    }
  }

  function syncPurchaseToSharedCart(item, quantity) {
    if (!item || typeof item.id !== "number") {
      return;
    }

    const qty = Number(quantity);
    if (!Number.isFinite(qty) || qty <= 0) {
      return;
    }

    if (globalScope.CartModule && typeof globalScope.CartModule.addCartItem === "function") {
      globalScope.CartModule.addCartItem(item, qty);
      return;
    }

    try {
      const raw = localStorage.getItem(CART_STORAGE_KEY);
      const cart = raw ? JSON.parse(raw) : [];
      const normalized = Array.isArray(cart) ? cart : [];

      const existing = normalized.find((entry) => entry.id === item.id);
      if (existing) {
        existing.quantity = Number(existing.quantity || 0) + qty;
      } else {
        normalized.push({
          id: item.id,
          name: item.name,
          price: Number(item.price),
          quantity: qty
        });
      }

      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(normalized));
    } catch (error) {
      console.warn("Unable to sync purchase to shared cart.", error);
    }
  }

  function applyFilters(items, filters = null) {
    if (!filters) {
      return [...items];
    }

    return items.filter((item) => {
      const categoryMatch = !filters.category || filters.category === "all" || item.category === filters.category;
      const priceMatch = item.price <= (filters.maxPrice || 1000);
      const ratingMatch = item.rating >= (filters.minRating || 0);
      const searchMatch = !filters.searchTerm
        || item.name.toLowerCase().includes(filters.searchTerm.toLowerCase())
        || item.description.toLowerCase().includes(filters.searchTerm.toLowerCase())
        || item.seller.toLowerCase().includes(filters.searchTerm.toLowerCase());

      return categoryMatch && priceMatch && ratingMatch && searchMatch;
    });
  }

  function sortItems(items, sortBy = "name") {
    const sorted = [...items];

    switch (sortBy) {
      case "price-low":
        sorted.sort((a, b) => a.price - b.price);
        break;
      case "price-high":
        sorted.sort((a, b) => b.price - a.price);
        break;
      case "rating":
        sorted.sort((a, b) => b.rating - a.rating);
        break;
      case "quantity":
        sorted.sort((a, b) => b.quantity - a.quantity);
        break;
      case "name":
      default:
        sorted.sort((a, b) => a.name.localeCompare(b.name));
    }

    return sorted;
  }

  async function loadRemoteState() {
    if (mode !== "api") {
      inventoryItems = [...localInventoryItems];
      purchaseHistory = readSharedPurchaseHistory();
      return;
    }

    try {
      const [itemsPayload, purchasePayload] = await Promise.all([
        request("/api/items"),
        request("/api/purchases")
      ]);

      inventoryItems = Array.isArray(itemsPayload) ? itemsPayload : (itemsPayload.items || []);
      purchaseHistory = Array.isArray(purchasePayload) ? purchasePayload : (purchasePayload.purchases || []);
    } catch (error) {
      inventoryItems = [...localInventoryItems];
      purchaseHistory = readSharedPurchaseHistory();
      console.warn("Falling back to local inventory data.", error);
    }
  }

  function getInventory(filters = null) {
    return applyFilters(inventoryItems, filters);
  }

  function getItemById(id) {
    return inventoryItems.find((item) => item.id === id) || null;
  }

  async function addItem(itemData) {
    if (mode === "api") {
      const created = await request("/api/items", {
        method: "POST",
        body: JSON.stringify(itemData)
      });
      await loadRemoteState();
      return created;
    }

    const newId = Math.max(...inventoryItems.map((item) => item.id), 0) + 1;
    const newItem = {
      id: newId,
      name: itemData.name,
      price: itemData.price,
      quantity: itemData.quantity || 1,
      category: itemData.category || "General",
      description: itemData.description || "",
      seller: itemData.seller || "Unknown",
      rating: itemData.rating || 4.0
    };

    inventoryItems.push(newItem);
    return newItem;
  }

  async function updateItem(id, updates) {
    if (mode === "api") {
      const updated = await request(`/api/items/${id}`, {
        method: "PATCH",
        body: JSON.stringify(updates)
      });
      await loadRemoteState();
      return updated;
    }

    const item = getItemById(id);
    if (!item) {
      return null;
    }

    Object.assign(item, updates);
    return item;
  }

  async function removeItem(id) {
    if (mode === "api") {
      await request(`/api/items/${id}`, { method: "DELETE" });
      await loadRemoteState();
      return true;
    }

    const index = inventoryItems.findIndex((item) => item.id === id);
    if (index < 0) {
      return false;
    }

    inventoryItems.splice(index, 1);
    return true;
  }

  async function purchaseItem(itemId, quantity, buyerName = "Guest") {
    const qty = Number(quantity);
    const item = getItemById(itemId);

    if (!item || item.quantity < qty || qty <= 0) {
      return null;
    }

    if (mode === "api") {
      await request(`/api/items/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ quantity: item.quantity - qty })
      });
    }

    item.quantity -= qty;
    syncPurchaseToSharedCart(item, qty);

    return {
      itemId,
      quantity: qty,
      buyer: buyerName,
      status: "AddedToCart"
    };
  }

  function getPurchaseHistory(filter = null) {
    if (mode !== "api") {
      purchaseHistory = readSharedPurchaseHistory();
    }

    if (!filter) {
      return [...purchaseHistory];
    }

    return purchaseHistory.filter((purchase) => purchase.buyer === filter || purchase.seller === filter);
  }

  async function clearPurchaseHistory() {
    if (mode === "api") {
      try {
        await request("/api/purchases", { method: "DELETE" });
      } catch (error) {
        console.warn("Unable to clear remote purchase history.", error);
      }
    }

    purchaseHistory = [];
    saveSharedPurchaseHistory(purchaseHistory);
    return true;
  }

  function getItemsByCategory(category) {
    return inventoryItems.filter((item) => item.category === category);
  }

  function getCategories() {
    const categories = [...new Set(inventoryItems.map((item) => item.category))];
    return ["all", ...categories];
  }

  function searchItems(searchTerm) {
    const term = (searchTerm || "").toLowerCase();
    return inventoryItems.filter((item) => {
      return item.name.toLowerCase().includes(term)
        || item.description.toLowerCase().includes(term)
        || item.seller.toLowerCase().includes(term);
    });
  }

  async function getInventoryStats() {
    if (mode !== "api") {
      purchaseHistory = readSharedPurchaseHistory();
    }

    if (mode === "api") {
      try {
        return await request("/api/inventory/stats");
      } catch (error) {
        console.warn("Stats endpoint unavailable. Using local calculation.", error);
      }
    }

    const totalItems = inventoryItems.reduce((sum, item) => sum + item.quantity, 0);
    const totalValue = inventoryItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const averagePrice = inventoryItems.length > 0
      ? inventoryItems.reduce((sum, item) => sum + item.price, 0) / inventoryItems.length
      : 0;

    return {
      totalUniqueItems: inventoryItems.length,
      totalItemsInStock: totalItems,
      inventoryValue: totalValue,
      averagePrice,
      totalSales: purchaseHistory.length,
      totalRevenue: purchaseHistory.reduce((sum, purchase) => sum + Number(purchase.totalPrice || 0), 0)
    };
  }

  function renderInventory(containerId, items = null) {
    const container = document.getElementById(containerId);
    if (!container) {
      return;
    }

    const sourceItems = items || sortItems(getInventory(currentFilter), currentSort);
    container.innerHTML = "";

    if (sourceItems.length === 0) {
      container.innerHTML = "<p class='empty-state'>No items found.</p>";
      return;
    }

    sourceItems.forEach((item) => {
      const card = document.createElement("article");
      card.className = "inventory-card";
      card.innerHTML = `
        <div class="item-image"></div>
        <h3>${item.name}</h3>
        <p class="seller">By ${item.seller}</p>
        <div class="rating">Rating ${item.rating} (${item.quantity > 0 ? "In Stock" : "Out of Stock"})</div>
        <p class="description">${item.description}</p>
        <div class="price">${formatPrice(item.price)}</div>
        <div class="stock">Available: ${item.quantity}</div>
        <button class="buy-btn" type="button" data-item-id="${item.id}" ${item.quantity === 0 ? "disabled" : ""}>
          ${item.quantity > 0 ? "Add To Cart" : "Out of Stock"}
        </button>
      `;
      container.appendChild(card);
    });
  }

  function renderPurchaseHistory(containerId, history = null) {
    const container = document.getElementById(containerId);
    if (!container) {
      return;
    }

    const historyRows = history || getPurchaseHistory();
    container.innerHTML = "";

    if (historyRows.length === 0) {
      container.innerHTML = "<tr><td colspan='8' class='empty-state'>No purchases yet.</td></tr>";
      return;
    }

    historyRows.forEach((purchase) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${purchase.purchaseId || "-"}</td>
        <td>${purchase.itemName || "-"}</td>
        <td>${purchase.quantity || "-"}</td>
        <td>${formatPrice(Number(purchase.unitPrice || 0))}</td>
        <td>${formatPrice(Number(purchase.totalPrice || 0))}</td>
        <td>${purchase.buyer || "Guest"}</td>
        <td>${purchase.seller || "Store"}</td>
        <td>${purchase.purchaseDate || "-"}</td>
      `;
      container.appendChild(row);
    });
  }

  function setCurrentFilter(nextFilter = {}) {
    Object.assign(currentFilter, nextFilter);
  }

  function setCurrentSort(sortBy) {
    currentSort = sortBy;
  }

  async function initializeInventory() {
    await loadRemoteState();
    return {
      inventory: clone(inventoryItems),
      purchases: clone(purchaseHistory)
    };
  }

  const api = {
    addItem,
    clearPurchaseHistory,
    formatPrice,
    getCategories,
    getCurrentFilter: () => clone(currentFilter),
    getCurrentSort: () => currentSort,
    getInventory,
    getInventoryStats,
    getItemById,
    getItemsByCategory,
    getPurchaseHistory,
    initializeInventory,
    purchaseItem,
    removeItem,
    renderInventory,
    renderPurchaseHistory,
    searchItems,
    setCurrentFilter,
    setCurrentSort,
    sortItems,
    updateItem
  };

  Object.assign(globalScope, api);

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
