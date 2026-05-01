/* global APP_CONFIG */

(function initCartModule(globalScope) {
  const CART_STORAGE_KEY = "blackwhale_cart";
  const ORDER_HISTORY_KEY = "blackwhale_purchase_history";
  const defaultProducts = [
    { id: 1, name: "Notebook", price: 6.99 },
    { id: 2, name: "Pen Set", price: 4.49 },
    { id: 3, name: "Water Bottle", price: 12.99 },
    { id: 4, name: "Desk Lamp", price: 24.95 }
  ];

  const cart = [];
  const config = globalScope.APP_CONFIG || {};
  const mode = config.dataMode || "local";
  const apiBaseUrl = config.apiBaseUrl || "";

  const productGrid = document.getElementById("productGrid");
  const cartList = document.getElementById("cartList");
  const totalItems = document.getElementById("totalItems");
  const totalPrice = document.getElementById("totalPrice");
  const emptyState = document.getElementById("emptyState");
  const clearCartBtn = document.getElementById("clearCartBtn");
  const checkoutBtn = document.getElementById("checkoutBtn");
  const checkoutModal = document.getElementById("checkoutModal");
  const checkoutChoiceView = document.getElementById("checkoutChoiceView");
  const guestCheckoutView = document.getElementById("guestCheckoutView");
  const chooseGuestBtn = document.getElementById("chooseGuestBtn");
  const chooseSignInBtn = document.getElementById("chooseSignInBtn");
  const cancelCheckoutBtn = document.getElementById("cancelCheckoutBtn");
  const backToOptionsBtn = document.getElementById("backToOptionsBtn");
  const placeGuestOrderBtn = document.getElementById("placeGuestOrderBtn");
  const guestEmailInput = document.getElementById("guestEmail");
  const guestPhoneInput = document.getElementById("guestPhone");
  const guestCardInput = document.getElementById("guestCard");

  let products = defaultProducts;

  function saveCart() {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch (error) {
      console.warn("Unable to persist cart.", error);
    }
  }

  function readOrderHistory() {
    try {
      const raw = localStorage.getItem(ORDER_HISTORY_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn("Unable to load order history.", error);
      return [];
    }
  }

  function saveOrderHistory(history) {
    try {
      localStorage.setItem(ORDER_HISTORY_KEY, JSON.stringify(history));
    } catch (error) {
      console.warn("Unable to persist order history.", error);
    }
  }

  function loadCart() {
    try {
      const raw = localStorage.getItem(CART_STORAGE_KEY);
      if (!raw) {
        return;
      }

      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return;
      }

      cart.length = 0;
      parsed.forEach((item) => {
        if (!item || typeof item.id !== "number") {
          return;
        }

        cart.push({
          id: item.id,
          name: item.name,
          price: Number(item.price),
          quantity: Number(item.quantity) || 1
        });
      });
    } catch (error) {
      console.warn("Unable to read persisted cart.", error);
    }
  }

  function money(value) {
    return `$${Number(value).toFixed(2)}`;
  }

  function showCheckoutModal() {
    if (!checkoutModal) {
      return;
    }

    checkoutModal.classList.add("active");
    if (checkoutChoiceView && guestCheckoutView) {
      checkoutChoiceView.style.display = "block";
      guestCheckoutView.style.display = "none";
    }
  }

  function hideCheckoutModal() {
    if (!checkoutModal) {
      return;
    }

    checkoutModal.classList.remove("active");
    if (guestEmailInput) {
      guestEmailInput.value = "";
    }
    if (guestPhoneInput) {
      guestPhoneInput.value = "";
    }
    if (guestCardInput) {
      guestCardInput.value = "";
    }
  }

  function toggleGuestForm(showGuest) {
    if (!checkoutChoiceView || !guestCheckoutView) {
      return;
    }

    checkoutChoiceView.style.display = showGuest ? "none" : "block";
    guestCheckoutView.style.display = showGuest ? "block" : "none";
  }

  function buildOrderRecords(contact) {
    const existingHistory = readOrderHistory();
    const nextOrderId = existingHistory.length + 1;
    const purchaseDate = new Date().toLocaleString();

    return cart.map((item) => {
      return {
        purchaseId: nextOrderId,
        itemId: item.id,
        itemName: item.name,
        quantity: item.quantity,
        unitPrice: item.price,
        totalPrice: item.price * item.quantity,
        buyer: "Guest",
        seller: "Store",
        purchaseDate,
        status: "Completed",
        contact
      };
    });
  }

  async function completeGuestCheckout() {
    const email = guestEmailInput ? guestEmailInput.value.trim() : "";
    const phone = guestPhoneInput ? guestPhoneInput.value.trim() : "";
    const card = guestCardInput ? guestCardInput.value.replace(/\s+/g, "") : "";

    if (cart.length === 0) {
      window.alert("Your cart is empty.");
      return;
    }

    if (!email && !phone) {
      window.alert("Enter an email or phone number for guest checkout.");
      return;
    }

    if (!/^\d{12,19}$/.test(card)) {
      window.alert("Enter a valid card number with 12 to 19 digits.");
      return;
    }

    const contact = {
      email: email || null,
      phone: phone || null,
      cardLast4: card.slice(-4)
    };

    const existingHistory = readOrderHistory();
    const newRecords = buildOrderRecords(contact);
    saveOrderHistory(existingHistory.concat(newRecords));

    if (mode === "api") {
      try {
        await request("/api/checkout", {
          method: "POST",
          body: JSON.stringify({
            checkoutType: "guest",
            contact,
            items: newRecords
          })
        });
      } catch (error) {
        console.warn("Checkout API unavailable. Stored locally.", error);
      }
    }

    await clearCart();
    hideCheckoutModal();
    window.alert("Guest checkout complete.");
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

  async function loadProducts() {
    if (mode !== "api") {
      products = defaultProducts;
      return;
    }

    try {
      const payload = await request("/api/items");
      products = Array.isArray(payload) ? payload : payload.items || defaultProducts;
    } catch (error) {
      products = defaultProducts;
      console.warn("Falling back to local product data.", error);
    }
  }

  function renderProducts() {
    if (!productGrid) {
      return;
    }

    productGrid.innerHTML = "";

    products.forEach((product) => {
      const card = document.createElement("article");
      card.className = "product";
      card.innerHTML = `
        <h3>${product.name}</h3>
        <div class="price">${money(product.price)}</div>
        <button class="add-btn" type="button" data-id="${product.id}">Add to Cart</button>
      `;
      productGrid.appendChild(card);
    });
  }

  async function addToCart(id) {
    const existing = cart.find((item) => item.id === id);

    if (existing) {
      existing.quantity += 1;
    } else {
      const product = products.find((item) => item.id === id);
      if (!product) {
        return;
      }
      cart.push({ ...product, quantity: 1 });
    }

    if (mode === "api") {
      try {
        await request("/api/cart/items", {
          method: "POST",
          body: JSON.stringify({ itemId: id, quantity: 1 })
        });
      } catch (error) {
        console.warn("Cart API sync failed.", error);
      }
    }

    saveCart();
    renderCart();
  }

  function addCartItem(item, quantity = 1) {
    if (!item || typeof item.id !== "number") {
      return;
    }

    const qty = Number(quantity);
    if (!Number.isFinite(qty) || qty <= 0) {
      return;
    }

    const existing = cart.find((entry) => entry.id === item.id);
    if (existing) {
      existing.quantity += qty;
    } else {
      cart.push({
        id: item.id,
        name: item.name,
        price: Number(item.price),
        quantity: qty
      });
    }

    saveCart();
    renderCart();
  }

  async function removeOne(id) {
    const index = cart.findIndex((item) => item.id === id);
    if (index < 0) {
      return;
    }

    cart[index].quantity -= 1;
    if (cart[index].quantity <= 0) {
      cart.splice(index, 1);
    }

    if (mode === "api") {
      try {
        await request(`/api/cart/items/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ quantityDelta: -1 })
        });
      } catch (error) {
        console.warn("Cart API sync failed.", error);
      }
    }

    saveCart();
    renderCart();
  }

  async function clearCart() {
    cart.length = 0;

    if (mode === "api") {
      try {
        await request("/api/cart", { method: "DELETE" });
      } catch (error) {
        console.warn("Cart API clear failed.", error);
      }
    }

    saveCart();
    renderCart();
  }

  function renderCart() {
    if (!cartList || !emptyState || !totalItems || !totalPrice) {
      return;
    }

    cartList.innerHTML = "";

    let count = 0;
    let total = 0;

    cart.forEach((item) => {
      count += item.quantity;
      total += item.price * item.quantity;

      const line = document.createElement("li");
      line.className = "cart-item";
      line.innerHTML = `
        <div>
          <strong>${item.name}</strong>
          <div class="qty">Qty: ${item.quantity}</div>
        </div>
        <div>${money(item.price * item.quantity)}</div>
        <button class="remove-btn" type="button" data-remove-id="${item.id}">-1</button>
      `;
      cartList.appendChild(line);
    });

    emptyState.style.display = cart.length === 0 ? "block" : "none";
    totalItems.textContent = String(count);
    totalPrice.textContent = money(total);

    if (checkoutBtn) {
      checkoutBtn.disabled = cart.length === 0;
    }
  }

  async function bootstrap() {
    await loadProducts();
    loadCart();
    renderProducts();
    renderCart();

    if (productGrid) {
      productGrid.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-id]");
        if (!button) {
          return;
        }
        await addToCart(Number(button.dataset.id));
      });
    }

    if (cartList) {
      cartList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-remove-id]");
        if (!button) {
          return;
        }
        await removeOne(Number(button.dataset.removeId));
      });
    }

    if (clearCartBtn) {
      clearCartBtn.addEventListener("click", () => {
        clearCart();
      });
    }

    if (checkoutBtn) {
      checkoutBtn.addEventListener("click", () => {
        if (cart.length === 0) {
          window.alert("Add items before checkout.");
          return;
        }
        showCheckoutModal();
      });
    }

    if (chooseSignInBtn) {
      chooseSignInBtn.addEventListener("click", () => {
        window.alert("Sign-in checkout is not enabled yet. Use Guest Checkout for now.");
      });
    }

    if (chooseGuestBtn) {
      chooseGuestBtn.addEventListener("click", () => {
        toggleGuestForm(true);
      });
    }

    if (cancelCheckoutBtn) {
      cancelCheckoutBtn.addEventListener("click", () => {
        hideCheckoutModal();
      });
    }

    if (backToOptionsBtn) {
      backToOptionsBtn.addEventListener("click", () => {
        toggleGuestForm(false);
      });
    }

    if (placeGuestOrderBtn) {
      placeGuestOrderBtn.addEventListener("click", () => {
        completeGuestCheckout();
      });
    }

    if (checkoutModal) {
      checkoutModal.addEventListener("click", (event) => {
        if (event.target === checkoutModal) {
          hideCheckoutModal();
        }
      });
    }
  }

  globalScope.CartModule = {
    addCartItem,
    addToCart,
    clearCart,
    removeOne,
    renderCart
  };

  bootstrap();
})(typeof window !== "undefined" ? window : globalThis);
