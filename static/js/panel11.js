// ناوبری موبایل
    const pages = { dashboard: 'mobileDashboard', printOrders: 'mobilePrintOrders', products: 'mobileProducts', reports: 'mobileReports' };
    document.querySelectorAll('.nav-item-mobile').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.nav-item-mobile').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.page-mobile').forEach(p=>p.classList.remove('active-page'));
            document.getElementById(pages[btn.dataset.nav]).classList.add('active-page');
        };
    });

    // ناوبری دسکتاپ
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.onclick = () => {
            document.querySelectorAll('.sidebar-item').forEach(i=>i.classList.remove('active'));
            item.classList.add('active');
            let page = item.dataset.page;
            document.querySelectorAll('.desktop-page').forEach(p=>p.classList.remove('active'));
            document.getElementById(`desktop${page.charAt(0).toUpperCase()+page.slice(1)}Page`).classList.add('active');
        };
    });

    // تب‌های دسکتاپ
    document.querySelectorAll('.desktop-tab').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.desktop-tab').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            let idx = Array.from(btn.parentElement.children).indexOf(btn);
            document.getElementById('desktopUsersTable').style.display = idx === 0 ? 'block' : 'none';
            document.getElementById('desktopOrdersTable').style.display = idx === 1 ? 'block' : 'none';
            document.getElementById('desktopPaymentsTable').style.display = idx === 2 ? 'block' : 'none';
        };
    });

    // تب‌های موبایل
    document.querySelectorAll('.mobile-tab-btn').forEach((btn, idx) => {
        btn.onclick = () => {
            document.querySelectorAll('.mobile-tab-btn').forEach(b=>b.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('mobileUsersList').style.display = idx === 0 ? 'block' : 'none';
            document.getElementById('mobileOrdersList').style.display = idx === 1 ? 'block' : 'none';
            document.getElementById('mobilePaymentsList').style.display = idx === 2 ? 'block' : 'none';
        };
    });

    // چارت‌ها
