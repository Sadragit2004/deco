// ============================================
// فایل کامل main.js - نسخه نهایی
// ============================================

const DEFAULT_IMAGE = '/media/images/nophoto.png';

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

    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const timeString = `${hours}:${minutes}:${seconds}`;

    const persianDate = new Intl.DateTimeFormat('fa-IR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(now);

    const weekdays = ['یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه'];
    const weekdayName = weekdays[now.getDay()];

    const desktopTime = document.getElementById('desktopTime');
    const desktopDate = document.getElementById('desktopDate');
    const desktopWeekday = document.getElementById('desktopWeekday');

    if (desktopTime) desktopTime.textContent = timeString;
    if (desktopDate) desktopDate.textContent = persianDate;
    if (desktopWeekday) desktopWeekday.textContent = weekdayName;

    const mobileTime = document.getElementById('mobileTime');
    const mobileDate = document.getElementById('mobileDate');
    if (mobileTime) mobileTime.textContent = timeString;
    if (mobileDate) mobileDate.textContent = persianDate;
}

setInterval(updateClock, 1000);
updateClock();

// ============================================
// تابع redirectToCategory
// ============================================
function redirectToCategory(slug) {
    if (!slug) {
        console.error('slug category is undefined');
        return;
    }
    window.location.href = `/product/category/${slug}/brands/`;
}

// ============================================
// استایل‌ها
// تمام استایل‌های ظاهری و ابعاد اصلی حفظ شده‌اند.
// فقط ویژگی‌ها و اجزای مربوط به اسکرول حذف شده‌اند.
// ============================================
function addHorizontalScrollStyles() {
    if (document.getElementById('horizontal-scroll-styles')) return;

    const styles = document.createElement('style');
    styles.id = 'horizontal-scroll-styles';
    styles.textContent = `
        .skeleton-wrapper {
            display: flex !important;
            flex-wrap: nowrap !important;
            gap: 16px !important;
            padding: 16px 8px !important;
            overflow-x: auto !important;
            min-height: 200px !important;
        }

        .skeleton-item {
            flex: 0 0 auto !important;
            width: 200px !important;
            min-width: 180px !important;
            background: #e2e8f0 !important;
            border-radius: 16px !important;
            overflow: hidden !important;
            animation: skeleton-pulse 1.5s ease-in-out infinite !important;
        }

        .skeleton-item .skeleton-img {
            width: 100% !important;
            height: 160px !important;
            background: #cbd5e1 !important;
        }

        .skeleton-item .skeleton-text {
            height: 16px !important;
            margin: 12px 16px 8px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
        }

        .skeleton-item .skeleton-text-sm {
            height: 12px !important;
            margin: 0 16px 12px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
            width: 60% !important;
        }

        .skeleton-category {
            flex: 0 0 auto !important;
            width: 140px !important;
            min-width: 120px !important;
            background: #e2e8f0 !important;
            border-radius: 16px !important;
            padding: 16px !important;
            text-align: center !important;
            animation: skeleton-pulse 1.5s ease-in-out infinite !important;
        }

        .skeleton-category .skeleton-circle {
            width: 80px !important;
            height: 80px !important;
            border-radius: 50% !important;
            background: #cbd5e1 !important;
            margin: 0 auto 12px !important;
        }

        .skeleton-category .skeleton-text {
            height: 14px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
            margin: 0 auto !important;
            width: 70% !important;
        }

        .skeleton-brand {
            flex: 0 0 auto !important;
            width: 140px !important;
            min-width: 120px !important;
            background: #e2e8f0 !important;
            border-radius: 16px !important;
            padding: 16px !important;
            text-align: center !important;
            animation: skeleton-pulse 1.5s ease-in-out infinite !important;
        }

        .skeleton-brand .skeleton-circle {
            width: 80px !important;
            height: 80px !important;
            border-radius: 50% !important;
            background: #cbd5e1 !important;
            margin: 0 auto 12px !important;
        }

        .skeleton-brand .skeleton-text {
            height: 14px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
            margin: 0 auto !important;
            width: 70% !important;
        }

        .skeleton-catalog {
            flex: 0 0 auto !important;
            width: 200px !important;
            min-width: 180px !important;
            background: #e2e8f0 !important;
            border-radius: 16px !important;
            overflow: hidden !important;
            animation: skeleton-pulse 1.5s ease-in-out infinite !important;
        }

        .skeleton-catalog .skeleton-img {
            width: 100% !important;
            height: 160px !important;
            background: #cbd5e1 !important;
        }

        .skeleton-catalog .skeleton-text {
            height: 16px !important;
            margin: 12px 16px 8px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
        }

        .skeleton-catalog .skeleton-text-sm {
            height: 12px !important;
            margin: 0 16px 12px !important;
            background: #cbd5e1 !important;
            border-radius: 8px !important;
            width: 50% !important;
        }

        @keyframes skeleton-pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    `;
    document.head.appendChild(styles);
}

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
        padding: 14px 28px;
        border-radius: 12px;
        z-index: 100000;
        font-weight: 600;
        box-shadow: 0 6px 25px rgba(0,0,0,0.2);
        animation: slideInRight 0.4s ease;
        direction: rtl;
        font-family: inherit;
        max-width: 90%;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
    `;
    notif.innerHTML = message;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.style.animation = 'slideOutRight 0.4s ease';
        setTimeout(() => notif.remove(), 400);
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// نمایش اسکلتون
// ============================================
function showSkeleton(containerId, type = 'product', count = 6) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let skeletonHTML = '';

    if (type === 'category') {
        skeletonHTML = '<div class="skeleton-wrapper">';
        for (let i = 0; i < count; i++) {
            skeletonHTML += `
                <div class="skeleton-category">
                    <div class="skeleton-circle"></div>
                    <div class="skeleton-text"></div>
                </div>
            `;
        }
        skeletonHTML += '</div>';
    } else if (type === 'brand') {
        skeletonHTML = '<div class="skeleton-wrapper">';
        for (let i = 0; i < count; i++) {
            skeletonHTML += `
                <div class="skeleton-brand">
                    <div class="skeleton-circle"></div>
                    <div class="skeleton-text"></div>
                </div>
            `;
        }
        skeletonHTML += '</div>';
    } else if (type === 'catalog') {
        skeletonHTML = '<div class="skeleton-wrapper">';
        for (let i = 0; i < count; i++) {
            skeletonHTML += `
                <div class="skeleton-catalog">
                    <div class="skeleton-img"></div>
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text-sm"></div>
                </div>
            `;
        }
        skeletonHTML += '</div>';
    } else {
        skeletonHTML = '<div class="skeleton-wrapper">';
        for (let i = 0; i < count; i++) {
            skeletonHTML += `
                <div class="skeleton-item">
                    <div class="skeleton-img"></div>
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text-sm"></div>
                </div>
            `;
        }
        skeletonHTML += '</div>';
    }

    container.innerHTML = skeletonHTML;
}

// ============================================
// رندر کارت محصول
// ============================================
function renderProductCard(product, showDiscount = true) {
    let productTitle = product.name || product.title || '';
    let truncatedTitle = productTitle.length > 30 ? productTitle.substring(0, 30) + '...' : productTitle;

    let discountText = '';
    if (showDiscount && (product.hasDiscount || product.discountPercent || product.discount)) {
        if (product.discountPercent) {
            discountText = `🔥 ${product.discountPercent}٪`;
        } else if (product.discount && typeof product.discount === 'string' && product.discount.includes('%')) {
            discountText = `🔥 ${product.discount}`;
        } else if (product.discount) {
            discountText = `🔥 ${product.discount}`;
        } else if (product.hasDiscount) {
            discountText = `🔥 ویژه`;
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
                <img loading="lazy" src="${productImage}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(productTitle)}">
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
                <span class="product-code"><i class="fas fa-barcode"></i> ${product.code || '---'}</span>
            </div>
            <div class="price-row">

            </div>
        </div>
    `;
}

// ============================================
// رندر دسته‌بندی‌ها
// ============================================
async function fetchAndRenderCategories() {
    const container = document.getElementById('categoriesGrid');
    if (!container) return;

    showSkeleton('categoriesGrid', 'category', 8);

    try {
        const response = await fetch('/product/noneParentCategory/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(c => `
                <div class="category-square" data-slug="${c.slug}" onclick="redirectToCategory('${c.slug}')">
                    <div onclick="redirectToCategory('${c.slug}')">
                        <img loading="lazy" src="${getValidImage(c.img)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(c.name)}">
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

// ============================================
// رندر محصولات جدید
// ============================================
async function fetchAndRenderLatestProducts() {
    const container = document.getElementById('newProductsList');
    if (!container) return;

    showSkeleton('newProductsList', 'product', 6);

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
                slug: p.slug,
                in_stock: p.in_stock !== false
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

// ============================================
// رندر پرفروش‌ترین‌ها
// ============================================
async function fetchAndRenderBestsellers() {
    const container = document.getElementById('bestsellersList');
    if (!container) return;

    showSkeleton('bestsellersList', 'product', 6);

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
                slug: p.slug,
                in_stock: p.in_stock !== false
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

// ============================================
// رندر برندهای محبوب
// ============================================
async function fetchAndRenderPopularBrands() {
    const container = document.getElementById('brandsList');
    if (!container) return;

    showSkeleton('brandsList', 'brand', 8);

    try {
        const response = await fetch('/product/popularBrands/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(b => `
                <div class="brand-logo">
                    <a href="/product/shop/?brand=${b.slug}">
                        <img loading="lazy" src="${getValidImage(b.img)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(b.name)}">
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

// ============================================
// رندر آخرین کاتالوگ‌ها
// ============================================
async function fetchAndRenderLatestCatalogs() {
    const container = document.getElementById('catalogVertical');
    if (!container) return;

    showSkeleton('catalogVertical', 'catalog', 6);

    try {
        const response = await fetch('/product/latest-catalogs/');
        const result = await response.json();
        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(catalog => `
                <div class="catalog-vertical-card">
                    <img loading="lazy" src="${getValidImage(catalog.image_url)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(catalog.title)}">
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
// رندر نمونه کارها
// ============================================
async function fetchAndRenderPortfolios() {
    const container = document.getElementById('portfolioList');
    if (!container) return;

    showSkeleton('portfolioList', 'product', 6);

    try {
        const response = await fetch('/api/portfolios/');
        const result = await response.json();

        if (result.status === 'success' && result.data.length > 0) {
            container.innerHTML = result.data.map(portfolio => `
                <div class="portfolio-card" onclick="showPortfolioDetail(${portfolio.id})">
                    <img loading="lazy" src="${getValidImage(portfolio.image)}" onerror="this.src='${DEFAULT_IMAGE}'" alt="${escapeHtml(portfolio.title)}">
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

// ============================================
// اجرای اولیه
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    addHorizontalScrollStyles();

    fetchAndRenderCategories();
    fetchAndRenderLatestProducts();
    fetchAndRenderBestsellers();
    fetchAndRenderPopularBrands();
    fetchAndRenderLatestCatalogs();
    fetchAndRenderPortfolios();

    console.log('✅ تمام سیستم‌ها با موفقیت بارگذاری شدند');
    console.log('✨ اسکرول افقی و کلیک دسته‌بندی‌ها فعال شد');
});

// ============================================
// پایان فایل
// ============================================
