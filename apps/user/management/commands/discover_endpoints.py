# ==================== فایل apps/user/management/commands/discover_endpoints.py ====================

from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver
from apps.user.models.role import Endpoint
import re


class Command(BaseCommand):
    help = 'کشف تمام اندپوینت‌های پروژه و ذخیره در دیتابیس'

    def extract_urls(self, patterns, parent_pattern='', app_name=''):
        urls = []

        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                # ریکرس کردن برای resolverهای تو در تو
                new_parent = parent_pattern + str(pattern.pattern)
                new_app = pattern.app_name or app_name
                urls.extend(self.extract_urls(pattern.url_patterns, new_parent, new_app))

            elif isinstance(pattern, URLPattern):
                # استخراج URL کامل
                url_path = parent_pattern + str(pattern.pattern)

                # حذف پارامترهای regex
                url_path = re.sub(r'\(\?P<[^>]+>[^\)]+\)', '{param}', url_path)
                url_path = re.sub(r'\?P<[^>]+>', '', url_path)
                url_path = re.sub(r'\[\^/\]\+', '{param}', url_path)
                url_path = re.sub(r'<[^:]+:[^>]+>', '{param}', url_path)
                url_path = re.sub(r'\\', '', url_path)
                url_path = re.sub(r'\$', '', url_path)

                # نام URL
                url_name = pattern.name or ''

                # اپلیکیشن
                app = pattern.default_args.get('app_name', '') or app_name
                if not app and hasattr(pattern, 'app_name'):
                    app = pattern.app_name or ''

                urls.append({
                    'url_name': url_name,
                    'url_path': url_path,
                    'app_name': app or 'main',
                })

        return urls

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 در حال کشف اندپوینت‌ها...'))

        resolver = get_resolver()
        all_urls = self.extract_urls(resolver.url_patterns)

        # حذف URLهای تکراری
        unique_urls = {}
        for url in all_urls:
            key = f"{url['url_path']}_{url['app_name']}"
            if key not in unique_urls and url['url_name']:
                unique_urls[key] = url

        # ذخیره در دیتابیس
        created_count = 0
        updated_count = 0

        for url_data in unique_urls.values():
            obj, created = Endpoint.objects.update_or_create(
                url_name=url_data['url_name'],
                defaults={
                    'url_path': url_data['url_path'],
                    'app_name': url_data['app_name'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ جدید: {obj.app_name} - {obj.url_name}'))
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ کشف کامل شد!'))
        self.stdout.write(self.style.SUCCESS(f'   📝 جدید: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'   🔄 بروزرسانی: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'   📊 مجموع: {len(unique_urls)} اندپوینت'))