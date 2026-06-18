# ==================== فایل apps/user/middleware/role_permission_middleware.py ====================

from django.shortcuts import redirect
from django.http import JsonResponse
from django.urls import resolve


class RolePermissionMiddleware:
    """میدلور جدی بررسی دسترسی نقش‌ها به URL ها"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_path = request.path

        # ========== دیباگ ==========
        print("\n" + "=" * 80)
        print(f"🔍 میدلور اجرا شد")
        print(f"📍 مسیر درخواستی: {current_path}")
        print(f"👤 کاربر: {request.user}")
        print(f"🔐 لاگین: {request.user.is_authenticated}")
        print(f"👑 سوپرادمین: {request.user.is_superuser}")
        # ============================

        # مسیرهای عمومی که همیشه آزاد هستند (فقط لاگین و ثابت)
        public_paths = [
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/verify/',
            '/admin/',
            '/static/',
            '/media/',
            '/admin/'
        ]

        # بررسی مسیرهای عمومی
        for public_path in public_paths:
            if current_path.startswith(public_path):
                print(f"✅ مسیر عمومی: {public_path} - دسترسی آزاد")
                print("=" * 80)
                return self.get_response(request)

        # صفحه اصلی
        if current_path == '/':
            print("✅ صفحه اصلی - دسترسی آزاد")
            print("=" * 80)
            return self.get_response(request)

        # کاربر لاگین نکرده
        if not request.user.is_authenticated:
            print("❌ کاربر لاگین نیست - ریدایرکت به لاگین")
            print("=" * 80)
            return redirect('/accounts/login/')

        # ========== بررسی جدی دسترسی ==========
        # حتی سوپرادمین هم باید قوانین رو رعایت کنه
        # همه نقش‌ها رو میگیریم (اگر سوپرادمین باشه، roles خالیه ولی خودش سوپرادمینه)

        # دریافت همه نقش‌های فعال کاربر (برای سوپرادمین این لیست خالیه)
        user_roles = request.user.roles.filter(isActive=True)
        print(f"📋 نقش‌های کاربر: {list(user_roles.values_list('title', flat=True))}")

        # اگر کاربر سوپرادمین است و نقشی نداره
        if request.user.is_superuser and not user_roles.exists():
            print("⚠️ سوپرادمین بدون نقش - نیاز به بررسی دسترسی ندارد")
            print("=" * 80)
            return self.get_response(request)

        # اگر کاربر هیچ نقشی ندارد (و سوپرادمین هم نیست)
        if not user_roles.exists():
            print("❌ کاربر بدون نقش - دسترسی به هیچ URL ای مجاز نیست!")
            print("=" * 80)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'شما هیچ نقشی ندارید و دسترسی به هیچ بخشی ندارید'
                }, status=403)
            return redirect('/')

        # ========== جمع‌آوری لیست سیاه URL ها از همه نقش‌های کاربر ==========
        banned_urls = []
        for role in user_roles:
            ban_urls = role.ban_urls.filter(isActive=True)
            for ban in ban_urls:
                banned_urls.append({
                    'pattern': ban.url_pattern,
                    'role': role.title,
                    'description': ban.description
                })

        print(f"🚫 لیست سیاه URL ها برای این کاربر:")
        for banned in banned_urls:
            print(f"   - نقش: {banned['role']} | الگو: {banned['pattern']}")

        # ========== بررسی دسترسی ==========
        for banned in banned_urls:
            if self.match_url(current_path, banned['pattern']):
                print(f"🚫 دسترسی ممنوع شد!")
                print(f"   نقش: {banned['role']}")
                print(f"   الگو: {banned['pattern']}")
                print(f"   مسیر درخواستی: {current_path}")
                print("=" * 80)

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': f'شما به این بخش دسترسی ندارید (نقش: {banned["role"]})',
                        'banned_url': banned['pattern']
                    }, status=403)

                return redirect('/')

        print(f"✅ دسترسی مجاز است - مسیر {current_path} در لیست سیاه نیست")
        print("=" * 80)
        return self.get_response(request)

    def match_url(self, current_path, pattern):
        """
        بررسی تطابق URL با الگو - جدی و دقیق
        """
        # نرمالایز کردن مسیرها
        current_path = current_path.rstrip('/')
        pattern = pattern.rstrip('/')

        # 1. تطابق کامل
        if current_path == pattern:
            return True

        # 2. تطابق با شروع (برای دایرکتوری‌ها)
        if pattern.endswith('/'):
            if current_path.startswith(pattern):
                return True
            # اگه الگو مثل /admin باشه (بدون اسلش آخر)
            if current_path.startswith(pattern + '/'):
                return True

        # 3. تطابق با الگوی star
        if '*' in pattern:
            import re
            regex_pattern = pattern.replace('*', '.*')
            if re.match(f"^{regex_pattern}", current_path):
                return True

        # 4. تطابق با شروع ساده
        if current_path.startswith(pattern):
            return True

        # 5. تطابق با الگوی {param}
        if '{' in pattern and '}' in pattern:
            import re
            regex_pattern = re.sub(r'\{[^}]+\}', r'[^/]+', pattern)
            if re.match(f"^{regex_pattern}$", current_path):
                return True

        return False