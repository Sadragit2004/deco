// ============================================
// ثابت برای تصویر پیش‌فرض
// ============================================
const DEFAULT_IMAGE = '/media/images/nophoto.png';

// تابع کمکی برای بررسی و بازگرداندن تصویر معتبر
function getValidImage(imageUrl, defaultImage = DEFAULT_IMAGE) {
    if (!imageUrl || imageUrl === '' || imageUrl === 'null' || imageUrl === 'undefined') {
        return defaultImage;
    }
    return imageUrl;
}

// ============================================
// ساعت دیجیتال
// ============================================
function updateClock() {
    const now = new Date();

    // Time
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const timeString = `${hours}:${minutes}:${seconds}`;

    // Date (Persian/Jalali)
    const persianDate = new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(now);

    // Weekday (Persian)
    const weekdays = ['یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه'];
    const weekdayName = weekdays[now.getDay()];

    // Update desktop clock
    const desktopTime = document.getElementById('desktopTime');
    const desktopDate = document.getElementById('desktopDate');
    const desktopWeekday = document.getElementById('desktopWeekday');

    if (desktopTime) desktopTime.textContent = timeString;
    if (desktopDate) desktopDate.textContent = persianDate;
    if (desktopWeekday) desktopWeekday.textContent = weekdayName;

    // Update mobile clock if exists
    const mobileTime = document.getElementById('mobileTime');
    const mobileDate = document.getElementById('mobileDate');
    if (mobileTime) mobileTime.textContent = timeString;
    if (mobileDate) mobileDate.textContent = persianDate;
}

// Update clock every second
setInterval(updateClock, 1000);
updateClock();

// ============================================
// اسکرول خودکار محصولات با موس
// ============================================
const productScrolls = document.querySelectorAll('.products-scroll, .catalog-vertical-grid, .brands-horizontal, .portfolio-grid');

productScrolls.forEach(scrollContainer => {
    let isDown = false;
    let startX;
    let scrollLeft;

    scrollContainer.addEventListener('mousedown', (e) => {
        isDown = true;
        scrollContainer.style.cursor = 'grabbing';
        startX = e.pageX - scrollContainer.offsetLeft;
        scrollLeft = scrollContainer.scrollLeft;
    });

    scrollContainer.addEventListener('mouseleave', () => {
        isDown = false;
        scrollContainer.style.cursor = 'grab';
    });

    scrollContainer.addEventListener('mouseup', () => {
        isDown = false;
        scrollContainer.style.cursor = 'grab';
    });

    scrollContainer.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - scrollContainer.offsetLeft;
        const walk = (x - startX) * 2;
        scrollContainer.scrollLeft = scrollLeft - walk;
    });

    scrollContainer.style.cursor = 'grab';
});

// ============================================
// توابع کمکی
// ============================================
function getCsrfToken() {
    const cookieValue = document.cookie.match('(^|; )csrftoken=([^;]*)');
    return cookieValue ? cookieValue[2] : '';
}

function showNotification(message, type = 'success') {
    const notif = document.createElement('div');
    const colors = {
        success: '#10B981',
        error: '#EF4444',
        info: '#3B82F6',
        warning: '#F59E0B'
    };
    notif.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${colors[type] || colors.success};
        color: white;
        padding: 12px 24px;
        border-radius: 12px;
        z-index: 100000;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease;
        direction: rtl;
        font-family: inherit;
    `;
    notif.innerHTML = message;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notif.remove(), 300);
    }, 2500);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// رندر محصولات از API
// ============================================
function renderProductCard(product, showDiscount = true) {
    let productTitle = product.name || product.title || '';
    let truncatedTitle = productTitle.length > 35 ? productTitle.substring(0, 35) + '...' : productTitle;

    let discountText = '';
    if (showDiscount && (product.hasDiscount || product.discountPercent || product.discount)) {
        if (product.discountPercent) {
            discountText = `🔥 ${product.discountPercent}٪ تخفیف`;
        } else if (product.discount && typeof product.discount === 'string' && product.discount.includes('%')) {
            discountText = `🔥 ${product.discount}`;
        } else if (product.discount) {
            discountText = `🔥 ${product.discount} تخفیف`;
        } else if (product.hasDiscount) {
            discountText = `🔥 تخفیف ویژه`;
        }
    }

    let originalPriceHtml = '';
    if ((product.hasDiscount || product.discountPercent || product.discount) && product.originalPrice) {
        originalPriceHtml = `<span class="original-price">${product.originalPrice}</span>`;
    }

    const productImage = getValidImage(product.img || product.image);

    return `
        <div class="product-card-item" data-product-id="${product.id || product.product_id}">
            ${discountText ? `<div class="discount-badge">${discountText}</div>` : ''}
            <a href="/product/${product.slug || '#'}" class="product-img-link">
                <img src="${productImage}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(productTitle)}">
            </a>
            <a href="/product/${product.slug || '#'}" class="product-title-link">
                <h4 class="product-title-text">${escapeHtml(truncatedTitle)}</h4>
            </a>
            <div class="product-price-wrapper">
                ${originalPriceHtml}
                <span class="final-price">${product.price}</span>
                <span class="price-per-meter">/${product.meter || ' '}</span>
            </div>
            <div class="product-meta">
                <span><i class="fas fa-ruler-combined"></i> ${product.meter || ' '}</span>
                <span class="product-code"><i class="fas fa-barcode"></i> ${product.code || 'کد نامشخص'}</span>
            </div>
            <div class="price-row">
                
            </div>
        </div>
    `;
}

async function fetchAndRenderLatestProducts() {
    const container = document.getElementById('newProductsList');
    if (!container) return;
    try {
        const response = await fetch('/product/lastedProduct/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            const apiProducts = result.data.map(p => ({
                id: p.id,
                name: p.name,
                price: new Intl.NumberFormat('fa-IR').format(p.price),
                originalPrice: p.has_discount ? new Intl.NumberFormat('fa-IR').format(p.original_price) : null,
                discount: p.has_discount ? (p.discount_percent ? `${p.discount_percent}%` : 'تخفیف') : null,
                discountPercent: p.discount_percent,
                hasDiscount: p.has_discount,
                meter: " ",
                code: p.code,
                brand: p.brand,
                img: p.img,
                slug: p.slug
            }));
            container.innerHTML = apiProducts.map(p => renderProductCard(p, true)).join('');
        } else {
            container.innerHTML = '<div class="empty-state">محصولی یافت نشد</div>';
        }
    } catch (error) {
        console.error("خطا:", error);
        container.innerHTML = '<div class="error-state">خطا در بارگذاری محصولات</div>';
    }
}

async function fetchAndRenderBestsellers() {
    const container = document.getElementById('bestsellersList');
    if (!container) return;
    try {
        const response = await fetch('/product/api/bestsellers/?limit=12');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            const products = result.data.map(p => ({
                id: p.id,
                name: p.name,
                price: p.price_info.unit_final_price_display,
                originalPrice: p.price_info.has_discount ? p.price_info.unit_original_price_display : null,
                discount: p.price_info.has_discount ? `${p.price_info.discount_percent}%` : null,
                discountPercent: p.price_info.discount_percent,
                hasDiscount: p.price_info.has_discount,
                meter: p.sales_unit || ' ',
                code: p.code,
                brand: p.brand,
                img: getValidImage(p.image),
                slug: p.slug
            }));
            container.innerHTML = products.map(p => renderProductCard(p, true)).join('');
        } else {
            container.innerHTML = '<div class="empty-state">محصولی یافت نشد</div>';
        }
    } catch (error) {
        console.error("خطا:", error);
        container.innerHTML = '<div class="error-state">خطا در بارگذاری</div>';
    }
}

async function fetchAndRenderCategories() {
    const container = document.getElementById('categoriesGrid');
    if (!container) return;
    try {
        const response = await fetch('/product/noneParentCategory/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(c => `
                <div class="category-square" data-slug="${c.slug}">
                    <div onclick="redirectToCategory('${c.slug}')">
                        <img src="${getValidImage(c.img)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(c.name)}">
                        <span>${escapeHtml(c.name)}</span>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p>دسته‌بندی یافت نشد.</p>';
        }
    } catch (error) {
        console.error("خطا:", error);
        container.innerHTML = '<p>خطا در برقراری ارتباط با سرور.</p>';
    }
}

async function fetchAndRenderPopularBrands() {
    const container = document.getElementById('brandsList');
    if (!container) return;
    try {
        const response = await fetch('/product/popularBrands/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(b => `
                <div class="brand-logo">
                    <a href="/product/shop/?brand=${b.slug}">
                        <img src="${getValidImage(b.img)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(b.name)}">
                        <span>${escapeHtml(b.name)}</span>
                    </a>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p>برندی یافت نشد</p>';
        }
    } catch (error) {
        console.error("خطا:", error);
        container.innerHTML = '<p>خطا در بارگذاری برندها</p>';
    }
}

async function fetchAndRenderLatestCatalogs() {
    const container = document.getElementById('catalogVertical');
    if (!container) return;
    try {
        const response = await fetch('/product/latest-catalogs/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(catalog => `
                <div class="catalog-vertical-card">
                    <img src="${getValidImage(catalog.image_url)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(catalog.title)}">
                    <div class="info">
                        <h5>${escapeHtml(catalog.title)}</h5>
                        <span>${escapeHtml(catalog.brand_name || 'کاتالوگ')}</span>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p>کاتالوگی یافت نشد</p>';
        }
    } catch (error) {
        console.error("خطا:", error);
        container.innerHTML = '<p>خطا در بارگذاری کاتالوگ‌ها</p>';
    }
}

// ============================================
// رندر نمونه کارها از API
// ============================================
async function fetchAndRenderPortfolios() {
    const container = document.getElementById('portfolioList');
    if (!container) return;

    try {
        const response = await fetch('/api/portfolios/');
        const result = await response.json();

        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(portfolio => `
                <div class="portfolio-card" onclick="showPortfolioDetail(${portfolio.id})">
                    <img src="${getValidImage(portfolio.image)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(portfolio.title)}">
                    <div class="portfolio-title-overlay">
                        <h4>${escapeHtml(portfolio.title)}</h4>
                        <small>${escapeHtml(portfolio.user_name)}</small>
                        <div class="portfolio-stats">
                            <i class="fas fa-image"></i> ${portfolio.images_count}
                            <i class="fas fa-calendar"></i> ${portfolio.created_at.split(' ')[0]}
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state"><i class="fas fa-images"></i><p>هیچ نمونه کاری یافت نشد</p></div>';
        }
    } catch (error) {
        console.error('خطا در دریافت نمونه کارها:', error);
        container.innerHTML = '<div class="error-state"><i class="fas fa-exclamation-circle"></i><p>خطا در بارگذاری نمونه کارها</p></div>';
    }
}

// نمایش جزئیات نمونه کار
window.showPortfolioDetail = async function(portfolioId) {
    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/`);
        const result = await response.json();

        if (result.status === 'success') {
            showPortfolioModal(result.data);
        }
    } catch (error) {
        console.error('خطا:', error);
        showNotification('خطا در دریافت جزئیات نمونه کار', 'error');
    }
};

function showPortfolioModal(portfolio) {
    const modal = document.createElement('div');
    modal.className = 'portfolio-modal';
    modal.innerHTML = `
        <div class="portfolio-modal-content">
            <span class="close-modal">&times;</span>
            <h2>${escapeHtml(portfolio.title)}</h2>
            <p class="portfolio-user">${escapeHtml(portfolio.user_name)}</p>
            <p class="portfolio-description">${escapeHtml(portfolio.description || 'توضیحاتی ثبت نشده است')}</p>
            <div class="portfolio-gallery">
                ${portfolio.gallery.map(img => `
                    <img src="${getValidImage(img.image)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="تصویر گالری">
                `).join('')}
            </div>
            <div class="portfolio-date">تاریخ ثبت: ${portfolio.created_at.split(' ')[0]}</div>
        </div>
    `;

    document.body.appendChild(modal);
    modal.style.display = 'flex';

    modal.querySelector('.close-modal').onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
}

// ============================================
// رندر نمونه کارهای کاربر از API
// ============================================
async function fetchAndRenderUserPortfolios() {
    const container = document.getElementById('portfolioUserContainer');
    if (!container) return;

    try {
        const response = await fetch('/api/my-portfolios/');
        const result = await response.json();

        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(portfolio => `
                <div class="portfolio-user-card">
                    <div class="portfolio-user-header">
                        <h4>${escapeHtml(portfolio.title)}</h4>
                        <button class="btn-delete-portfolio" onclick="deleteUserPortfolio(${portfolio.id})">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                    <p class="portfolio-user-desc">${escapeHtml(portfolio.description || 'بدون توضیحات')}</p>
                    <div class="portfolio-user-gallery">
                        ${portfolio.gallery.slice(0, 3).map(img => `
                            <img src="${getValidImage(img.image)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="تصویر نمونه کار">
                        `).join('')}
                        ${portfolio.images_count > 3 ? `<div class="gallery-more">+${portfolio.images_count - 3}</div>` : ''}
                    </div>
                    <div class="portfolio-user-footer">
                        <span><i class="fas fa-calendar"></i> ${portfolio.created_at.split(' ')[0]}</span>
                        <span><i class="fas fa-image"></i> ${portfolio.images_count} عکس</span>
                        <button class="btn-add-image" onclick="addImageToPortfolio(${portfolio.id})">
                            <i class="fas fa-plus"></i> افزودن عکس
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `
                <div class="empty-cart">
                    <i class="fas fa-images"></i>
                    <p>هیچ نمونه کاری آپلود نکرده‌اید</p>
                    <small>از بخش آپلود نمونه کار، پروژه‌های خود را به اشتراک بگذارید</small>
                    <button class="btn-create-portfolio" onclick="showCreatePortfolioForm()">
                        <i class="fas fa-plus"></i> ایجاد نمونه کار جدید
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('خطا در دریافت نمونه کارهای کاربر:', error);
        container.innerHTML = '<div class="error-state"><p>خطا در بارگذاری نمونه کارها</p></div>';
    }
}

// حذف نمونه کار کاربر
window.deleteUserPortfolio = async function(portfolioId) {
    if (!confirm('آیا از حذف این نمونه کار مطمئن هستید؟')) return;

    try {
        const response = await fetch(`/api/portfolios/${portfolioId}/delete/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });

        const result = await response.json();
        if (result.status === 'success') {
            showNotification('نمونه کار با موفقیت حذف شد', 'success');
            fetchAndRenderUserPortfolios();
        } else {
            showNotification(result.message || 'خطا در حذف', 'error');
        }
    } catch (error) {
        showNotification('خطا در ارتباط با سرور', 'error');
    }
};

// نمایش فرم ایجاد نمونه کار
window.showCreatePortfolioForm = function() {
    const modal = document.createElement('div');
    modal.className = 'portfolio-modal';
    modal.innerHTML = `
        <div class="portfolio-modal-content" style="max-width: 500px;">
            <span class="close-modal">&times;</span>
            <h2>ایجاد نمونه کار جدید</h2>
            <form id="createPortfolioForm">
                <div class="form-group">
                    <label>عنوان نمونه کار</label>
                    <input type="text" id="portfolioTitle" required placeholder="مثال: پروژه دکوراسیون داخلی ویلا">
                </div>
                <div class="form-group">
                    <label>توضیحات (اختیاری)</label>
                    <textarea id="portfolioDesc" rows="3" placeholder="توضیحات مربوط به این پروژه..."></textarea>
                </div>
                <button type="submit" class="btn-submit">ایجاد نمونه کار</button>
            </form>
        </div>
    `;

    document.body.appendChild(modal);
    modal.style.display = 'flex';

    modal.querySelector('.close-modal').onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

    document.getElementById('createPortfolioForm').onsubmit = async (e) => {
        e.preventDefault();
        const title = document.getElementById('portfolioTitle').value;
        const description = document.getElementById('portfolioDesc').value;

        try {
            const response = await fetch('/api/portfolios/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ title, description })
            });

            const result = await response.json();
            if (result.status === 'success') {
                modal.remove();
                showNotification('نمونه کار با موفقیت ایجاد شد', 'success');
                fetchAndRenderUserPortfolios();
                setTimeout(() => addImageToPortfolio(result.data.id), 500);
            } else {
                showNotification(result.message || 'خطا در ایجاد', 'error');
            }
        } catch (error) {
            showNotification('خطا در ارتباط با سرور', 'error');
        }
    };
};

// افزودن عکس به نمونه کار
window.addImageToPortfolio = async function(portfolioId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await fetch(`/api/portfolios/${portfolioId}/upload-image/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                },
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                showNotification('عکس با موفقیت آپلود شد', 'success');
                fetchAndRenderUserPortfolios();
            } else {
                showNotification(result.message || 'خطا در آپلود', 'error');
            }
        } catch (error) {
            showNotification('خطا در ارتباط با سرور', 'error');
        }
    };
    input.click();
};

// ============================================
// سبد خرید
// ============================================
let cart = [];

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

async function loadCartFromAPI() {
    try {
        const result = await CartAPI.getData();
        if (result.success && result.items) {
            cart = result.items.map(item => ({
                id: item.product_id,
                name: item.name,
                price: parseFloat(item.price),
                priceStr: item.price_display,
                meter: " ",
                code: item.code || "PRO-" + item.product_id,
                brand: item.brand || "برند",
                guarantee: "۱۲ ماه",
                img: getValidImage(item.image),
                qty: item.quantity,
                slug: item.slug
            }));
        }
        renderCart();
    } catch (error) {
        console.error('خطا:', error);
    }
}

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
                <img src="${item.img}" class="cart-item-image" onerror="this.src='${DEFAULT_IMAGE}'">
                <div class="cart-item-details">
                    <div class="cart-item-title">${escapeHtml(item.name)}</div>
                    <div class="cart-item-specs">
                        <span><i class="fas fa-ruler-combined"></i> ${item.meter}</span>
                        <span><i class="fas fa-barcode"></i> ${item.code}</span>
                        <span><i class="fas fa-trademark"></i> ${item.brand}</span>
                        <span><i class="fas fa-shield-alt"></i> ${item.guarantee}</span>
                    </div>
                    <div class="cart-item-price">${item.priceStr} تومان</div>
                    <div class="cart-quantity-control">
                        <button class="qty-btn" onclick="changeQuantity(${item.id}, -1)">−</button>
                        <span class="cart-item-qty" id="qty-${item.id}">${item.qty}</span>
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
            <button class="checkout-btn" onclick="checkout()"><i class="fas fa-check-circle"></i> ثبت سفارش و پرداخت</button>
        </div>
    `;

    const totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
    const cartCountElem = document.getElementById('cartCount');
    if (cartCountElem) cartCountElem.innerText = totalQty;
}

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

window.checkout = function() {
    if (cart.length === 0) {
        alert('سبد خرید شما خالی است!');
        return;
    }
    window.location.href = '/order/create/';
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

// ============================================
// اعلان‌ها
// ============================================
let notificationInterval;
let notificationsData = [];
let pendingOrderData = null;

async function fetchNotifications() {
    try {
        const response = await fetch('/notification/');
        const data = await response.json();

        if (data.success) {
            const badge = document.querySelector('#notifIcon .badge-count');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.innerText = data.unread_count;
                    badge.style.display = 'flex';
                } else {
                    badge.innerText = '0';
                    badge.style.display = 'none';
                }
            }

            notificationsData = data.notifications || [];
            pendingOrderData = data.pending_order;
            renderNotificationsPanel();
            renderPendingOrderCard();
        }
    } catch (error) {
        console.error('خطا:', error);
    }
}

function renderNotificationsPanel() {
    const container = document.getElementById('notifList');
    if (!container) return;

    if (!notificationsData || notificationsData.length === 0) {
        container.innerHTML = `<div class="empty-notif"><i class="far fa-bell-slash"></i><p>هیچ اعلانی وجود ندارد</p></div>`;
        return;
    }

    container.innerHTML = notificationsData.map(n => `
        <div class="notif-item ${!n.is_sent ? 'unread' : ''}" data-id="${n.id}" onclick="markNotificationAsRead('${n.id}')">
            <div class="notif-icon"><i class="fas ${getStatusIcon(n.new_status)}"></i></div>
            <div class="notif-content">
                <div class="notif-message">${escapeHtml(n.message)}</div>
                <div class="notif-time">${n.created_at}</div>
            </div>
            ${!n.is_sent ? '<div class="notif-dot"></div>' : ''}
        </div>
    `).join('');
}

function renderPendingOrderCard() {
    const container = document.getElementById('pendingOrderCard');
    if (!container) return;

    if (pendingOrderData) {
        container.innerHTML = `
            <div class="pending-order-card">
                <div class="pending-order-header">
                    <i class="fas fa-clock"></i>
                    <span>سفارش در انتظار پرداخت</span>
                </div>
                <div class="pending-order-number">شماره: ${pendingOrderData.order_number}</div>
                <div class="pending-order-amount">مبلغ: ${pendingOrderData.total_amount_display} تومان</div>
                <button class="pending-pay-btn" onclick="payPendingOrder('${pendingOrderData.order_id}')">
                    <i class="fas fa-credit-card"></i> پرداخت سفارش
                </button>
                <div class="pending-order-date">${pendingOrderData.created_at}</div>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="no-pending-card">
                <i class="fas fa-check-circle"></i>
                <p>هیچ سفارش در انتظار پرداختی ندارید</p>
            </div>
        `;
    }
}

async function markNotificationAsRead(notificationId) {
    try {
        const response = await fetch('/notification/mark-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ notification_id: notificationId })
        });
        const data = await response.json();
        if (data.success) fetchNotifications();
    } catch (error) {
        console.error('خطا:', error);
    }
}

async function markAllNotificationsAsRead() {
    try {
        const response = await fetch('/notification/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        const data = await response.json();
        if (data.success) {
            fetchNotifications();
            showNotification('همه اعلان‌ها خوانده شدند', 'success');
        }
    } catch (error) {
        console.error('خطا:', error);
    }
}

window.payPendingOrder = function(orderId) {
    window.location.href = `/payment/${orderId}/`;
};

function getStatusIcon(status) {
    const icons = {
        'paid': 'fa-check-circle',
        'processing': 'fa-spinner',
        'packaging': 'fa-box',
        'shipped': 'fa-truck',
        'delivered': 'fa-home',
        'cancelled': 'fa-times-circle',
        'pending': 'fa-clock'
    };
    return icons[status] || 'fa-bell';
}

function startNotificationPolling() {
    fetchNotifications();
    notificationInterval = setInterval(fetchNotifications, 120000);
}

function stopNotificationPolling() {
    if (notificationInterval) clearInterval(notificationInterval);
}

function addMarkAllButton() {
    const notifHeader = document.querySelector('#notifPanel .panel-header');
    if (notifHeader && !document.getElementById('markAllBtn')) {
        const markAllBtn = document.createElement('button');
        markAllBtn.id = 'markAllBtn';
        markAllBtn.innerHTML = '<i class="fas fa-check-double"></i> همه را خوانده شد';
        markAllBtn.onclick = markAllNotificationsAsRead;
        notifHeader.appendChild(markAllBtn);
    }
}

// ============================================
// سفارشات و پرداخت‌ها (از API)
// ============================================
async function renderOrders() {
    const container = document.getElementById('ordersContainer');
    if (!container) return;

    try {
        const response = await fetch('/order/api/orders/');
        const result = await response.json();

        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(order => `
                <div class="order-card-expanded">
                    <div class="order-header">
                        <span class="order-number">#${order.order_number}</span>
                        <span class="order-status ${order.status_class}">${order.status_display}</span>
                        <span class="order-date"><i class="fas fa-calendar-alt"></i> ${order.created_at.split(' ')[0]}</span>
                    </div>
                    <div class="order-items">
                        ${order.items.map(item => `
                            <div class="order-item-row">
                                <span class="order-item-name">${escapeHtml(item.name)} × ${item.quantity}</span>
                                <span class="order-item-price">${item.total_price_display} تومان</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="order-total-row">
                        <span>جمع کل سفارش:</span>
                        <span>${order.total_amount_display} تومان</span>
                    </div>
                    <button class="btn-order-details" onclick="showOrderDetails('${order.id}')">مشاهده جزئیات</button>
                </div>
            `).join('');
        } else {
            container.innerHTML = `<div class="empty-cart"><i class="fas fa-truck"></i><p>هیچ سفارشی ثبت نشده است</p></div>`;
        }
    } catch (error) {
        console.error('خطا:', error);
        container.innerHTML = '<div class="error-state">خطا در بارگذاری سفارشات</div>';
    }
}

async function renderPayments() {
    const container = document.getElementById('paymentsContainer');
    if (!container) return;

    try {
        const response = await fetch('/payment/api/transactions/');
        const result = await response.json();

        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(payment => `
                <div class="payment-card-expanded">
                    <div class="payment-header">
                        <span class="payment-id">${payment.transaction_id}</span>
                        <span class="payment-status ${payment.status === 'موفق' ? 'success' : 'pending'}">${payment.status}</span>
                        <span class="payment-date"><i class="fas fa-calendar-alt"></i> ${payment.created_at.split(' ')[0]}</span>
                    </div>
                    <div class="payment-details-grid">
                        <div class="payment-detail-item">
                            <span class="payment-detail-label"><i class="fas fa-money-bill-wave"></i> مبلغ:</span>
                            <span class="payment-detail-value">${payment.amount_display} تومان</span>
                        </div>
                        <div class="payment-detail-item">
                            <span class="payment-detail-label"><i class="fas fa-credit-card"></i> روش پرداخت:</span>
                            <span class="payment-detail-value">${payment.method || 'کارت اعتباری'}</span>
                        </div>
                        ${payment.ref_id ? `
                        <div class="payment-detail-item">
                            <span class="payment-detail-label"><i class="fas fa-hashtag"></i> کد رهگیری:</span>
                            <span class="payment-detail-value">${payment.ref_id}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="order-total-row">
                        <span>مبلغ نهایی پرداختی:</span>
                        <span>${payment.amount_display} تومان</span>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `<div class="empty-cart"><i class="fas fa-credit-card"></i><p>هیچ تراکنشی ثبت نشده است</p></div>`;
        }
    } catch (error) {
        console.error('خطا:', error);
        container.innerHTML = '<div class="error-state">خطا در بارگذاری تراکنش‌ها</div>';
    }
}

window.showOrderDetails = function(orderId) {
    window.location.href = `/order/${orderId}/`;
};

// ============================================
// علاقه‌مندی‌ها (از API)
// ============================================
async function renderWishlist() {
    const container = document.getElementById('wishlistContainer');
    if (!container) return;

    try {
        const response = await fetch('/order/wishlist/');
        const result = await response.json();

        if (result.success && result.items && result.items.length > 0) {
            container.innerHTML = result.items.map(item => `
                <div class="wishlist-card">
                    <div class="wishlist-heart-icon"><i class="fas fa-heart"></i></div>
                    <img src="${getValidImage(item.image)}" class="wishlist-img" onerror="this.src='${DEFAULT_IMAGE}'">
                    <div class="wishlist-info">
                        <div class="wishlist-title">${escapeHtml(item.name)}</div>
                        <div class="product-meta" style="margin:5px 0">
                            <span><i class="fas fa-ruler-combined"></i>  </span>
                            <span class="product-code"><i class="fas fa-barcode"></i> ${item.code || '---'}</span>
                        </div>
                        <div class="wishlist-price">${item.price_display} تومان</div>
                        <div class="wishlist-meta">
                            <button class="btn-remove-wishlist" onclick="removeFromWishlist(${item.product_id})">
                                <i class="fas fa-trash-alt"></i> حذف
                            </button>

                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = `<div class="empty-cart"><i class="fas fa-heart"></i><p>لیست علاقه‌مندی شما خالی است</p></div>`;
        }
    } catch (error) {
        console.error('خطا:', error);
        container.innerHTML = '<div class="error-state">خطا در بارگذاری لیست علاقه‌مندی</div>';
    }
}

window.removeFromWishlist = async function(productId) {
    try {
        const response = await fetch('/order/wishlist/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ product_id: productId })
        });
        const result = await response.json();
        if (result.success) {
            showNotification('محصول از علاقه‌مندی‌ها حذف شد', 'info');
            renderWishlist();
        } else {
            showNotification(result.message || 'خطا در حذف', 'error');
        }
    } catch (error) {
        showNotification('خطا در ارتباط با سرور', 'error');
    }
};

// ============================================
// جستجو
// ============================================
const searchInput = document.getElementById('globalSearchInput');
const suggestionsDiv = document.getElementById('searchSuggestions');

if (searchInput) {
    searchInput.addEventListener('input', async (e) => {
        const val = e.target.value.trim();
        if (val.length < 2) {
            suggestionsDiv?.classList.remove('show');
            return;
        }

        try {
            const response = await fetch(`/product/search/?q=${encodeURIComponent(val)}`);
            const result = await response.json();

            if (result.status === 'success' && result.data.length > 0) {
                if (suggestionsDiv) {
                    suggestionsDiv.innerHTML = result.data.slice(0, 5).map(p => `
                        <div class="suggestion-item" onclick="searchSelect('${escapeHtml(p.name)}', '${p.slug}')">
                            <img src="${getValidImage(p.image)}" style="width: 30px; height: 30px; object-fit: cover; border-radius: 8px;" onerror="this.src='${DEFAULT_IMAGE}'">
                            <strong style="flex:1">${escapeHtml(p.name)}</strong>
                            <span style="color:#e96500;">${p.price_display}</span>
                        </div>
                    `).join('');
                    suggestionsDiv.classList.add('show');
                }
            } else {
                suggestionsDiv?.classList.remove('show');
            }
        } catch (error) {
            console.error('خطا:', error);
        }
    });
}

window.searchSelect = (term, slug) => {
    if (searchInput) searchInput.value = term;
    if (suggestionsDiv) suggestionsDiv.classList.remove('show');
    if (slug) window.location.href = `/product/${slug}/`;
};

document.addEventListener('click', (e) => {
    if (searchInput && suggestionsDiv && !searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.classList.remove('show');
    }
});

function redirectToCategory(slug) {
    if (slug) window.location.href = `/product/category/${slug}/brands/`;
}

// ============================================
// مدیریت تب‌ها
// ============================================
const panesMap = {
    shop: 'shopPane',
    orders: 'ordersPane',
    payments: 'paymentsPane',
    wishlist: 'wishlistPane',
    'portfolio-user': 'portfolioUserPane'
};

function switchTab(tabId) {
    if (!panesMap[tabId]) return;

    Object.values(panesMap).forEach(p => {
        const pane = document.getElementById(p);
        if (pane) pane.classList.remove('active-pane');
    });

    const activePane = document.getElementById(panesMap[tabId]);
    if (activePane) activePane.classList.add('active-pane');

    document.querySelectorAll('.nav-item-side').forEach(el => el.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item-side[data-tab="${tabId}"]`);
    if (activeNav) activeNav.classList.add('active');

    document.querySelectorAll('.bottom-item').forEach(b => b.classList.remove('active-bottom'));
    const activeBottom = document.querySelector(`.bottom-item[data-mobile-tab="${tabId}"]`);
    if (activeBottom) activeBottom.classList.add('active-bottom');

    if (tabId === 'orders') renderOrders();
    if (tabId === 'payments') renderPayments();
    if (tabId === 'wishlist') renderWishlist();
    if (tabId === 'portfolio-user') fetchAndRenderUserPortfolios();

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('.nav-item-side').forEach(el => {
    el.addEventListener('click', () => switchTab(el.getAttribute('data-tab')));
});
document.querySelectorAll('.bottom-item[data-mobile-tab]').forEach(el => {
    el.addEventListener('click', () => switchTab(el.getAttribute('data-mobile-tab')));
});

// ============================================
// پنل‌ها
// ============================================
const profileTrigger = document.getElementById('profileTriggerTop');
const profilePanel = document.getElementById('profilePanel');
const closeProfile = document.getElementById('closeProfile');
const cartIcon = document.getElementById('cartIcon');
const cartPanel = document.getElementById('cartPanel');
const closeCart = document.getElementById('closeCart');
const notifIcon = document.getElementById('notifIcon');
const notifPanel = document.getElementById('notifPanel');
const closeNotif = document.getElementById('closeNotif');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebarDesktop = document.getElementById('sidebarDesktop');

if (profileTrigger) profileTrigger.onclick = () => profilePanel?.classList.add('open');
if (closeProfile) closeProfile.onclick = () => profilePanel?.classList.remove('open');
if (cartIcon) cartIcon.onclick = () => { cartPanel?.classList.add('open'); renderCart(); };
if (closeCart) closeCart.onclick = () => cartPanel?.classList.remove('open');
if (notifIcon) notifIcon.onclick = () => { notifPanel?.classList.add('open'); renderNotificationsPanel(); };
if (closeNotif) closeNotif.onclick = () => notifPanel?.classList.remove('open');

if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
        sidebarDesktop?.classList.toggle('open-mobile');
    });
}

document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebarDesktop && mobileMenuBtn) {
        if (!e.target.closest('#sidebarDesktop') && !e.target.closest('#mobileMenuBtn')) {
            sidebarDesktop.classList.remove('open-mobile');
        }
    }
});

// ============================================
// استایل‌ها
// ============================================
function addProductCardStyles() {
    if (document.getElementById('product-card-styles')) return;
    const styles = document.createElement('style');
    styles.id = 'product-card-styles';
    styles.textContent = `
        .product-card-item {
            background: white; border-radius: 16px; overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05); transition: all 0.3s ease;
            position: relative; display: flex; flex-direction: column; height: 100%;
            border: 1px solid #eee;
        }
        .product-card-item:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
        .product-img-link { display: block; overflow: hidden; }
        .product-card-item img { width: 100%; aspect-ratio: 1 / 0.9; object-fit: cover; transition: transform 0.3s ease; }
        .product-card-item:hover img { transform: scale(1.02); }
        .product-title-link { text-decoration: none; padding: 8px 10px 0 10px; display: block; }
        .product-title-text {
            font-size: 0.85rem; font-weight: 600; line-height: 1.4; margin: 0;
            color: #1e2a3e; display: -webkit-box; -webkit-line-clamp: 2;
            -webkit-box-orient: vertical; overflow: hidden; min-height: 38px;
        }
        .product-price-wrapper { padding: 6px 10px; display: flex; align-items: baseline; flex-wrap: wrap; gap: 6px; }
        .final-price { font-size: 1rem; font-weight: 800; color: #e96500; }
        .original-price { font-size: 0.7rem; color: #94a3b8; text-decoration: line-through; }
        .price-per-meter { font-size: 0.65rem; color: #64748b; }
        .product-meta { padding: 0 10px 6px; display: flex; justify-content: space-between; font-size: 0.65rem; color: #64748b; gap: 8px; }
        .product-meta span { display: flex; align-items: center; gap: 3px; }
        .price-row { padding: 6px 10px 10px; display: flex; justify-content: flex-end; }
        .add-icon {
            width: 32px; height: 32px; background: linear-gradient(135deg, #e96500, #b85500);
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            cursor: pointer; transition: all 0.2s; color: white;
        }
        .add-icon:hover { transform: scale(1.05); }
        .discount-badge {
            position: absolute; top: 8px; right: 8px;
            background: #fee2e2; color: #b91c1c; padding: 2px 8px;
            border-radius: 20px; font-size: 0.6rem; font-weight: 700; z-index: 2;
        }
        .portfolio-modal {
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); z-index: 10000; justify-content: center; align-items: center;
        }
        .portfolio-modal-content {
            background: white; border-radius: 20px; max-width: 800px; width: 90%;
            max-height: 90vh; overflow-y: auto; padding: 20px; position: relative;
        }
        .portfolio-gallery {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-top: 20px;
        }
        .portfolio-gallery img {
            width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 12px;
        }
        .portfolio-user-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
        }
        .portfolio-user-gallery {
            display: flex; gap: 10px; margin-top: 10px; position: relative;
        }
        .portfolio-user-gallery img {
            width: 80px; height: 80px; object-fit: cover; border-radius: 8px;
        }
        .gallery-more {
            width: 80px; height: 80px; background: rgba(0,0,0,0.7); border-radius: 8px;
            display: flex; align-items: center; justify-content: center; color: white;
        }
        .empty-state, .error-state {
            text-align: center; padding: 40px; color: #94a3b8;
        }
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(styles);
}

function addNotificationStyles() {
    if (document.getElementById('notification-styles')) return;
    const styles = document.createElement('style');
    styles.id = 'notification-styles';
    styles.textContent = `
        .notif-item.unread { background: #fef3e8; border-right: 3px solid #e96500; }
        .notif-dot { width: 8px; height: 8px; background: #e96500; border-radius: 50%; margin-right: 10px; }
        .pending-order-card {
            background: linear-gradient(135deg, #fff5eb, #ffe8d6); border-radius: 16px;
            padding: 16px; margin-bottom: 20px; border: 1px solid #ffd9b5;
        }
        .pending-pay-btn {
            width: 100%; background: linear-gradient(135deg, #e96500, #b85500);
            color: white; border: none; padding: 12px; border-radius: 12px;
            font-weight: 700; margin: 12px 0; cursor: pointer;
        }
    `;
    document.head.appendChild(styles);
}

function setupAutoScroll(containerId, scrollAmount = 280, intervalTime = 3000) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    let autoScrollInterval;
    let isHovering = false;

    function startAutoScroll() {
        if (autoScrollInterval) clearInterval(autoScrollInterval);
        autoScrollInterval = setInterval(() => {
            if (!isHovering && container && container.children.length > 0) {
                const maxScroll = container.scrollWidth - container.clientWidth;
                const currentScroll = container.scrollLeft;
                if (currentScroll + scrollAmount >= maxScroll) {
                    container.scrollTo({ left: 0, behavior: 'smooth' });
                } else {
                    container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
                }
            }
        }, intervalTime);
    }

    function stopAutoScroll() {
        if (autoScrollInterval) clearInterval(autoScrollInterval);
    }

    container.addEventListener('mouseenter', () => { isHovering = true; stopAutoScroll(); });
    container.addEventListener('mouseleave', () => { isHovering = false; startAutoScroll(); });
    startAutoScroll();
    return { stop: stopAutoScroll, start: startAutoScroll };
}

// ============================================
// اجرای اولیه
// ============================================
addProductCardStyles();
addNotificationStyles();
fetchAndRenderLatestProducts();
fetchAndRenderBestsellers();
fetchAndRenderCategories();
fetchAndRenderPopularBrands();
fetchAndRenderLatestCatalogs();
fetchAndRenderPortfolios();
fetchAndRenderUserPortfolios();
loadCartFromAPI();
renderOrders();
renderPayments();
renderWishlist();
startNotificationPolling();
addMarkAllButton();

setTimeout(() => {
    setupAutoScroll('newProductsList', 280, 3000);
    setupAutoScroll('topProductsList', 280, 3000);
    setupAutoScroll('bestsellersList', 280, 3000);
}, 1000);

window.addEventListener('beforeunload', stopNotificationPolling);