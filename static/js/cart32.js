// ============================================
// سبد خرید با APIهای /order/ - نسخه نهایی
// ============================================

let cart = [];
let nextProductId = 4;

const CartAPI = {
    add: async (productId, quantity = 1) => {
        const response = await fetch(`/order/cart/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
        });
        return response.json();
    },
    remove: async (productId) => {
        const response = await fetch(`/order/cart/remove/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ product_id: productId })
        });
        return response.json();
    },
    update: async (productId, quantity) => {
        const response = await fetch(`/order/cart/update/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
        });
        return response.json();
    },
    clear: async () => {
        const response = await fetch(`/order/cart/clear/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        });
        return response.json();
    },
    getData: async () => {
        const response = await fetch(`/order/cart/data/`);
        return response.json();
    }
};

// تابع ایجاد سفارش و هدایت به checkout
// تابع ایجاد سفارش و هدایت به checkout با دیباگ
async function createOrderAndRedirect() {
    console.log("===== createOrderAndRedirect CALLED =====");

    try {
        const checkoutBtn = document.getElementById('finalCheckoutBtn');
        if (!checkoutBtn) {
            console.error("finalCheckoutBtn not found!");
            return;
        }

        const originalText = checkoutBtn.innerHTML;
        checkoutBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> در حال ایجاد سفارش...';
        checkoutBtn.disabled = true;

        // اول تست کن ببین ویو تست کار می‌کند یا نه
        console.log("Sending request to test endpoint...");
        const testResponse = await fetch('/order/test/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const testResult = await testResponse.json();
        console.log("Test response:", testResult);

        if (testResult.success) {
            console.log("Test view works! Now trying real order creation...");

            // حالا درخواست واقعی
            const response = await fetch('/order/create/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            console.log("Response status:", response.status);
            console.log("Response headers:", response.headers);

            const result = await response.json();
            console.log("Order creation response:", result);

            if (result.success && result.order_id) {
                console.log("Order created successfully, redirecting to:", `/order/checkout/${result.order_id}/`);
                window.location.href = `/order/checkout/${result.order_id}/`;
            } else {
                console.error("Order creation failed:", result.message);
                showNotification(result.message || 'خطا در ایجاد سفارش', 'error');
                checkoutBtn.innerHTML = originalText;
                checkoutBtn.disabled = false;
            }
        } else {
            console.error("Test view failed:", testResult);
            showNotification('خطا در ارتباط با سرور', 'error');
            checkoutBtn.innerHTML = originalText;
            checkoutBtn.disabled = false;
        }

    } catch (error) {
        console.error('خطا در createOrderAndRedirect:', error);
        showNotification('خطا در ارتباط با سرور: ' + error.message, 'error');
        const checkoutBtn = document.getElementById('finalCheckoutBtn');
        if (checkoutBtn) {
            checkoutBtn.innerHTML = '<i class="fas fa-check-circle"></i> ثبت سفارش و پرداخت';
            checkoutBtn.disabled = false;
        }
    }
}

// بارگذاری سبد خرید از API
async function loadCartFromAPI() {
    try {
        const result = await CartAPI.getData();
        if (result.success && result.items) {
            cart = result.items.map(item => ({
                id: item.product_id,
                name: item.name,
                price: parseFloat(item.price),
                priceStr: item.price_display,
                meter: "متر مربع",
                code: item.code || "PRO-" + item.product_id,
                brand: item.brand || "برند",
                guarantee: "۱۲ ماه",
                img: item.image,
                qty: item.quantity,
                slug: item.slug,
                has_discount: item.has_discount,
                original_price: item.original_price,
                original_price_display: item.original_price_display
            }));
            if (cart.length > 0) {
                nextProductId = Math.max(...cart.map(i => i.id), 0) + 1;
            }
        }
        renderCart();
    } catch (error) {
        console.error('خطا در بارگذاری سبد خرید:', error);
    }
}

// رندر سبد خرید
function renderCart() {
    const container = document.getElementById('cartItemsList');
    if (!container) return;

    if (!cart || cart.length === 0) {
        container.innerHTML = `<div class="empty-cart"><i class="fas fa-shopping-bag"></i><p>سبد خرید شما خالی است</p><small>محصولات مورد نظر خود را اضافه کنید</small></div>`;
        const cartCountElem = document.getElementById('cartCount');
        if (cartCountElem) cartCountElem.innerText = '0';
        return;
    }

    const totalAmount = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const totalAmountStr = totalAmount.toLocaleString('fa-IR');

    container.innerHTML = `
        ${cart.map(item => `
            <div class="cart-item" data-id="${item.id}">
                <img src="${item.img}" class="cart-item-image" onerror="this.src='/media/images/placeholder.jpg'">
                <div class="cart-item-details">
                    <div class="cart-item-title">${escapeHtml(item.name)}</div>
                    <div class="cart-item-specs">
                        <span><i class="fas fa-ruler-combined"></i> ${item.meter}</span>
                        <span><i class="fas fa-barcode"></i> ${item.code}</span>
                        <span><i class="fas fa-trademark"></i> ${item.brand}</span>
                        <span><i class="fas fa-shield-alt"></i> ${item.guarantee}</span>
                    </div>
                    <div class="cart-item-price">
                        ${item.has_discount ? `<span class="original-price-cart">${item.original_price_display} تومان</span>` : ''}
                        <span class="final-price-cart">${item.priceStr} تومان</span>
                    </div>
                    <div class="cart-quantity-control">
                        <button class="qty-btn" onclick="changeQuantity(${item.id}, -1)">−</button>
                        <span class="cart-item-qty">${item.qty}</span>
                        <button class="qty-btn" onclick="changeQuantity(${item.id}, 1)">+</button>
                    </div>
                </div>
                <div class="cart-item-actions">
                    <div class="icon-action" onclick="showItemDetails(${item.id})" title="مشاهده جزئیات"><i class="fas fa-info-circle"></i></div>
                    <div class="icon-action" onclick="removeItem(${item.id})" title="حذف کالا"><i class="fas fa-trash-alt"></i></div>
                </div>
            </div>
        `).join('')}
        <div class="cart-footer">
            <div class="cart-total-row"><span>جمع کل:</span><span class="cart-total-amount">${totalAmountStr} تومان</span></div>
            <button class="clear-cart-btn" onclick="clearCart()"><i class="fas fa-trash-alt"></i> حذف همه کالاها</button>
            <button class="checkout-btn" id="finalCheckoutBtn"><i class="fas fa-check-circle"></i> ثبت سفارش و پرداخت</button>
        </div>
    `;

    const totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
    const cartCountElem = document.getElementById('cartCount');
    if (cartCountElem) cartCountElem.innerText = totalQty;

    // اتصال دکمه ثبت سفارش
    const finalCheckoutBtn = document.getElementById('finalCheckoutBtn');
    if (finalCheckoutBtn) {
        finalCheckoutBtn.onclick = createOrderAndRedirect;
    }
}

// توابع عملیات سبد خرید
window.changeQuantity = async function(productId, delta) {
    const index = cart.findIndex(item => item.id === productId);
    if (index !== -1) {
        const newQty = cart[index].qty + delta;
        if (newQty >= 1) {
            const result = await CartAPI.update(productId, newQty);
            if (result.success) {
                cart[index].qty = newQty;
                renderCart();
                showNotification('تعداد محصول به‌روزرسانی شد', 'success');
            } else {
                showNotification(result.message || 'خطا در به‌روزرسانی', 'error');
            }
        } else {
            await removeItem(productId);
        }
    }
};

window.removeItem = async function(productId) {
    if (confirm('آیا از حذف این کالا مطمئن هستید؟')) {
        const result = await CartAPI.remove(productId);
        if (result.success) {
            cart = cart.filter(item => item.id !== productId);
            renderCart();
            showNotification('کالا از سبد خرید حذف شد', 'info');
        } else {
            showNotification(result.message || 'خطا در حذف', 'error');
        }
    }
};

window.clearCart = async function() {
    if (cart.length > 0 && confirm('آیا از حذف همه کالاها مطمئن هستید؟')) {
        const result = await CartAPI.clear();
        if (result.success) {
            cart = [];
            renderCart();
            showNotification('سبد خرید خالی شد', 'info');
        } else {
            showNotification(result.message || 'خطا در خالی کردن سبد', 'error');
        }
    }
};

window.showItemDetails = function(productId) {
    const item = cart.find(i => i.id === productId);
    if (item) {
        alert(`🛍 مشخصات محصول:\n\nنام: ${item.name}\nکد: ${item.code}\nبرند: ${item.brand}\nمتراژ: ${item.meter}\nگارانتی: ${item.guarantee}\nقیمت واحد: ${item.priceStr} تومان\nتعداد: ${item.qty}\nجمع: ${(item.price * item.qty).toLocaleString()} تومان`);
    }
};

window.addToCartById = async function(productId, quantity = 1, showPanel = true) {
    try {
        const result = await CartAPI.add(productId, quantity);
        if (result.success) {
            await loadCartFromAPI();
            showNotification(result.message, 'success');
            if (showPanel) {
                const cartPanel = document.getElementById('cartPanel');
                if (cartPanel) cartPanel.classList.add('open');
            }
            return true;
        } else {
            showNotification(result.message || 'خطا در افزودن محصول', 'error');
            return false;
        }
    } catch (error) {
        showNotification('خطا در ارتباط با سرور', 'error');
        return false;
    }
};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'success') {
    const notif = document.createElement('div');
    const colors = { success: '#10B981', error: '#EF4444', info: '#3B82F6' };
    notif.style.cssText = `
        position: fixed; bottom: 20px; right: 20px;
        background: ${colors[type] || colors.success}; color: white;
        padding: 12px 24px; border-radius: 12px; z-index: 100000;
        font-weight: 600; box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease; direction: rtl;
    `;
    notif.innerHTML = message;
    document.body.appendChild(notif);
    setTimeout(() => notif.remove(), 2500);
}

function getCsrfToken() {
    const cookieValue = document.cookie.match('(^|; )csrftoken=([^;]*)');
    return cookieValue ? cookieValue[2] : '';
}

// مقداردهی اولیه
document.addEventListener('DOMContentLoaded', async () => {
    await loadCartFromAPI();

    const cartIcon = document.getElementById('cartIcon');
    const cartPanel = document.getElementById('cartPanel');
    const closeCart = document.getElementById('closeCart');

    if (cartIcon) {
        cartIcon.onclick = () => {
            if (cartPanel) cartPanel.classList.add('open');
            renderCart();
        };
    }

    if (closeCart) {
        closeCart.onclick = () => {
            if (cartPanel) cartPanel.classList.remove('open');
        };
    }
});