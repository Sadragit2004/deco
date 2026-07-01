import json
import os
import re

print("🔍 در حال پردازش فایل data.sql...")

with open('data.sql', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# ساختار ذخیره دیتاها به صورت تفکیک شده
all_tables = {}
current_table = None
current_columns = []
in_copy = False
row_count = 0
table_data = []

for i, line in enumerate(lines):
    line = line.strip()

    # پیدا کردن شروع COPY
    if line.startswith('COPY ') and ' FROM stdin;' in line:
        # استخراج نام جدول و ستون‌ها
        parts = line.replace('COPY ', '').replace(' FROM stdin;', '').split('(')
        if len(parts) >= 2:
            table_part = parts[0].strip()
            # حذف public. از نام جدول
            if table_part.startswith('public.'):
                current_table = table_part.replace('public.', '')
            else:
                current_table = table_part

            columns_part = parts[1].replace(')', '').strip()
            current_columns = [c.strip() for c in columns_part.split(',')]
            in_copy = True
            row_count = 0
            table_data = []
            print(f"\n📋 جدول: {current_table} ({len(current_columns)} ستون)")
        continue

    # پیدا کردن پایان COPY
    if line == '\\.' and in_copy:
        in_copy = False
        # ذخیره دیتاهای جدول در all_tables
        if current_table and table_data:
            all_tables[current_table] = {
                'columns': current_columns,
                'data': table_data,
                'count': len(table_data)
            }
            print(f"   ✅ {len(table_data)} رکورد ذخیره شد")
        current_table = None
        current_columns = []
        table_data = []
        continue

    # پردازش خطوط دیتا
    if in_copy and line and line != '\\' and not line.startswith('--'):
        # جدا کردن با tab
        values = line.split('\t')

        # تبدیل \N به None
        values = [None if v == '\\N' else v for v in values]

        # اگه تعداد ستون‌ها برابر بود
        if len(values) == len(current_columns):
            row = dict(zip(current_columns, values))
            table_data.append(row)
            row_count += 1

if len(all_tables) > 0:
    # ذخیره به JSON با فرمت تفکیک شده
    result = {
        'tables': all_tables,
        'summary': {
            'total_tables': len(all_tables),
            'total_rows': sum(t['count'] for t in all_tables.values())
        }
    }

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("✅ تبدیل با موفقیت انجام شد!")
    print(f"✅ تعداد جداول: {len(all_tables)}")
    print(f"✅ مجموع رکوردها: {result['summary']['total_rows']}")
    print("\n📊 لیست جداول:")
    for table_name, info in all_tables.items():
        print(f"   - {table_name}: {info['count']} رکورد ({len(info['columns'])} ستون)")
    print(f"\n📁 فایل: {os.path.abspath('data.json')}")
    print("=" * 60)
else:
    print("\n❌ هیچ داده‌ای پیدا نشد!")