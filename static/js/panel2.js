  // ==================== داده‌ها ====================
    let currentUser = { fullname: "امیرحسین باقری", email: "amir@printpanel.com", avatar: "ا" };
    let totalUsers = 2180, onlineUsersList = ["مهدی رضایی", "سارا محمدی", "علی کریمی", "زهرا نادری", "رضا فتاحی", "نگار جعفری", "حسین مرادی"];
    let todayOrders = 52, totalOrdersAll = 1470, todayPaymentsCount = 37, totalPaymentsSum = 1320000000, todayRevenue = 204000000;
    let ordersData = [
        {id:"ORD-100", type:"چاپی", amount:"2,450,000", status:"تحویل"},
        {id:"ORD-101", type:"غیر چاپی", amount:"890,000", status:"پردازش"},
        {id:"ORD-102", type:"چاپی", amount:"3,200,000", status:"در انتظار"}
    ];
    let usersList = [
        {username:"rezamoh", email:"reza@print.com", role:"ادمین"},
        {username:"sananevis", email:"sana@print.com", role:"کاربر"},
        {username:"ali_f", email:"ali@print.com", role:"کاربر ویژه"}
    ];
    let paymentsList = [
        {id:"PAY987", user:"مهدی رضایی", amount:"1,200,000", date:"۱۴۰۲/۱۲/۰۵"},
        {id:"PAY988", user:"سارا محمدی", amount:"750,000", date:"۱۴۰۲/۱۲/۰۶"}
    ];

    // ==================== رندر آمار و جداول ====================
    function renderStats() {
        const statsGrid = document.getElementById('statsGrid');
        const stats = [
            { label:"کل کاربران", value:totalUsers.toLocaleString(), sub:"آنلاین: "+onlineUsersList.length, icon:"fas fa-users" },
            { label:"سفارشات کل", value:totalOrdersAll.toLocaleString(), sub:"امروز: "+todayOrders, icon:"fas fa-shopping-cart" },
            { label:"پرداختی‌ها", value:totalPaymentsSum.toLocaleString(), sub:"امروز: "+todayPaymentsCount, icon:"fas fa-credit-card" },
            { label:"درآمد کل", value:(totalPaymentsSum/1e6).toFixed(1)+"M", sub:"امروز: "+(todayRevenue/1e6).toFixed(1)+"M", icon:"fas fa-chart-line" }
        ];
        statsGrid.innerHTML = stats.map(s => `
            <div class="stat-card glass-card">
                <div><div class="stat-label">${s.label}</div><div class="stat-number">${s.value}</div><div class="stat-sub">${s.sub}</div></div>
                <i class="${s.icon}" style="font-size:2rem; opacity:0.7; color:#c195ff;"></i>
            </div>
        `).join('');

        document.getElementById('onlineUsersContainer').innerHTML = onlineUsersList.map(u => `<div class="online-user-chip"><i class="fas fa-circle" style="font-size:8px; color:#5effa2;"></i> ${u}</div>`).join('');
        document.getElementById('ordersTbody').innerHTML = ordersData.map(o => `<tr><td>${o.id}</td><td>${o.type}</td><td>${o.amount}</td><td><span class="badge-success">${o.status}</span></td></tr>`).join('');
        document.getElementById('usersTbody').innerHTML = usersList.map(u => `<tr><td>${u.username}</td><td>${u.email}</td><td>${u.role}</td></tr>`).join('');
        document.getElementById('paymentsTbody').innerHTML = paymentsList.map(p => `<tr><td>${p.id}</td><td>${p.user}</td><td>${p.amount}</td><td>${p.date}</td></tr>`).join('');

        const fullTable = document.getElementById('fullUsersTable');
        if(fullTable) fullTable.innerHTML = `<thead><tr><th>نام کاربری</th><th>نقش</th><th>وضعیت</th></tr></thead><tbody>${[...usersList, {username:"نرگس سلطانی", role:"مدیر", status:"فعال"}, {username:"حمید رضایی", role:"کاربر", status:"فعال"}].map(u => `<tr><td>${u.username}</td><td>${u.role}</td><td><span class="badge-success">فعال</span></td></tr>`).join('')}</tbody>`;

        document.getElementById('deskName').innerText = currentUser.fullname;
        document.getElementById('deskEmail').innerText = currentUser.email;
        document.getElementById('deskAvatar').innerText = currentUser.fullname.charAt(0);
        document.getElementById('mobileUserName').innerText = currentUser.fullname.split(' ')[0];
    }

    // ==================== نویگیشن ====================
    const pages = ['dashboard', 'printOrders', 'nonPrintOrders', 'siteSettings', 'userList'];
    let activePage = 'dashboard';

    function changePage(pageId) {
        activePage = pageId;
        pages.forEach(p => document.getElementById(p+'Page')?.classList.remove('active-page'));
        document.getElementById(pageId+'Page').classList.add('active-page');
        renderNavs();
        setTimeout(() => { if(window.charts) Object.values(window.charts).forEach(ch => ch?.resize()); }, 100);
    }

    const menuItems = [
        { id:'dashboard', icon:'fas fa-tachometer-alt', title:'داشبورد' },
        { id:'printOrders', icon:'fas fa-print', title:'چاپی' },
        { id:'nonPrintOrders', icon:'fas fa-file-alt', title:'غیر چاپی' },
        { id:'siteSettings', icon:'fas fa-sliders-h', title:'تنظیمات' },
        { id:'userList', icon:'fas fa-users', title:'کاربران' }
    ];

    function renderNavs() {
        const desktopNav = document.getElementById('desktopNav');
        const bottomNav = document.getElementById('bottomNav');
        if(desktopNav) desktopNav.innerHTML = '';
        if(bottomNav) bottomNav.innerHTML = '';
        menuItems.forEach(item => {
            const btnDesk = document.createElement('button');
            btnDesk.className = `nav-item ${activePage === item.id ? 'active' : ''}`;
            btnDesk.innerHTML = `<i class="${item.icon}"></i> ${item.title}`;
            btnDesk.onclick = () => changePage(item.id);
            desktopNav.appendChild(btnDesk);

            const mobBtn = document.createElement('button');
            mobBtn.className = `bottom-nav-item ${activePage === item.id ? 'active' : ''}`;
            mobBtn.innerHTML = `<i class="${item.icon}"></i><span>${item.title}</span>`;
            mobBtn.onclick = () => changePage(item.id);
            bottomNav.appendChild(mobBtn);
        });
    }

    // ==================== چارت‌ها ====================
    let charts = {};
    function initCharts() {
        charts.usersChart = new Chart(document.getElementById('usersChart'), { type:'bar', data:{ labels:['فروردین','اردیبهشت','خرداد','تیر'], datasets:[{ label:'کاربران جدید', data:[52,78,114,138], backgroundColor:'#b37eff', borderRadius:8 }] }, options:{ responsive:true, maintainAspectRatio:true } });
        charts.salesChart = new Chart(document.getElementById('salesChart'), { type:'line', data:{ labels:['هفته1','هفته2','هفته3','هفته4'], datasets:[{ label:'فروش (میلیون)', data:[86,112,178,225], borderColor:'#daa6ff', backgroundColor:'#daa6ff20', tension:0.3, fill:true }] } });
        charts.printChart = new Chart(document.getElementById('printChart'), { type:'doughnut', data:{ labels:['چاپ افست','دیجیتال'], datasets:[{ data:[65,35], backgroundColor:['#a56eff','#d29eff'] }] } });
        charts.nonPrintChart = new Chart(document.getElementById('nonPrintChart'), { type:'pie', data:{ labels:['طراحی','سئو'], datasets:[{ data:[60,40], backgroundColor:['#bf85ff','#9f53ff'] }] } });
        charts.siteStatsChart = new Chart(document.getElementById('siteStatsChart'), { type:'bar', data:{ labels:['شنبه','یکشنبه','دوشنبه','سه‌شنبه'], datasets:[{ label:'بازدید', data:[480,730,950,1120], backgroundColor:'#b87aff' }] } });
        charts.usersRoleChart = new Chart(document.getElementById('usersRoleChart'), { type:'polarArea', data:{ labels:['ادمین','کاربران','مدیر'], datasets:[{ data:[8,2140,32], backgroundColor:['#bc86ff','#d8adff','#a157ff'] }] } });
        window.charts = charts;
    }

    // ==================== تب‌ها ====================
    function initTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                let target = btn.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active-tab-content'));
                document.getElementById(target).classList.add('active-tab-content');
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active-tab'));
                btn.classList.add('active-tab');
            });
        });
    }

    // ==================== مودال ====================
    const modal = document.getElementById('profileModal');
    function openModal() { modal.style.display = 'flex'; document.getElementById('fullnameInput').value = currentUser.fullname; document.getElementById('emailInput').value = currentUser.email; }
    document.getElementById('editDeskBtn')?.addEventListener('click', openModal);
    document.getElementById('mobileEditBtn')?.addEventListener('click', openModal);
    document.getElementById('closeModalBtn')?.addEventListener('click', () => modal.style.display = 'none');
    document.getElementById('saveProfileBtn')?.addEventListener('click', () => {
        let newName = document.getElementById('fullnameInput').value;
        let newEmail = document.getElementById('emailInput').value;
        if(newName) currentUser.fullname = newName;
        if(newEmail) currentUser.email = newEmail;
        renderStats();
        modal.style.display = 'none';
    });
    document.getElementById('logoutBtnDesk')?.addEventListener('click', () => { alert('خروج از حساب'); currentUser = { fullname:'میهمان', email:'guest@panel.com', avatar:'م' }; renderStats(); changePage('dashboard'); });

    // پویا
    setInterval(() => {
        todayOrders = 52 + Math.floor(Math.random() * 10);
        todayPaymentsCount = 37 + Math.floor(Math.random() * 6);
        todayRevenue += Math.floor(Math.random() * 3500000);
        totalUsers += Math.floor(Math.random() * 5);
        renderStats();
    }, 8000);

    // شروع
    function start() {
        renderNavs();
        initCharts();
        renderStats();
        initTabs();
        changePage('dashboard');
    }
    start();