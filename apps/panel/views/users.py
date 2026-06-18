# apps/admin_panel/api_views.py

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Sum, Avg, F
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from ..decorators import admin_required
from apps.user.models.user import CustomUser
from apps.user.models.security import UserSecurity
from apps.user.models.profile import UserAddress, Wallet, WalletTransaction, CustomerLoyalty
from apps.user.models.role import Role
from apps.order.models import Order, LoyaltyTransaction
from apps.peyment.models import Peyment


@admin_required
def admin_panel_index(request):
    """صفحه اصلی پنل ادمین - فقط رندر تمپلیت"""
    return render(request, 'panel_app/dashboard/users.html')


@admin_required
def api_dashboard_stats(request):
    """API آمار داشبورد"""
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = CustomUser.objects.count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    banned_users = UserSecurity.objects.filter(isBan=True).count()
    online_users = CustomUser.get_online_count()
    new_users_week = CustomUser.objects.filter(createAt__gte=week_ago).count()
    new_users_month = CustomUser.objects.filter(createAt__gte=month_ago).count()
    staff_count = CustomUser.objects.filter(is_staff=True).count()

    male_count = CustomUser.objects.filter(gender='M').count()
    female_count = CustomUser.objects.filter(gender='F').count()

    verified_users = UserSecurity.objects.filter(isVerfiyByManager=True).count()
    payment_users = UserSecurity.objects.filter(isPeymentuser=True).count()

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    paid_orders = Order.objects.filter(status='paid').count()
    processing_orders = Order.objects.filter(status='processing').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    ready_orders = Order.objects.filter(status='ready').count()

    total_revenue = Order.objects.filter(status='paid').aggregate(total=Sum('total'))['total'] or 0
    if isinstance(total_revenue, Decimal):
        total_revenue = float(total_revenue)

    total_wallet_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0
    if isinstance(total_wallet_balance, Decimal):
        total_wallet_balance = float(total_wallet_balance)

    top_users = CustomUser.objects.annotate(
        order_count=Count('orders')
    ).filter(order_count__gt=0).order_by('-order_count')[:5]

    top_users_data = []
    for user in top_users:
        top_users_data.append({
            'id': str(user.id),
            'name': f'{user.name} {user.family}' or user.mobileNumber,
            'mobile': user.mobileNumber,
            'order_count': user.order_count,
            'avatar': user.avatar.url if user.avatar else None
        })

    daily_stats = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

        orders_count = Order.objects.filter(created_at__range=[day_start, day_end]).count()
        new_users_count = CustomUser.objects.filter(createAt__range=[day_start, day_end]).count()

        daily_stats.append({
            'date': day.strftime('%Y-%m-%d'),
            'orders': orders_count,
            'new_users': new_users_count
        })

    return JsonResponse({
        'success': True,
        'data': {
            'users': {
                'total': total_users,
                'active': active_users,
                'banned': banned_users,
                'online': online_users,
                'new_week': new_users_week,
                'new_month': new_users_month,
                'male': male_count,
                'female': female_count,
                'staff': staff_count,
                'verified': verified_users,
                'payment': payment_users
            },
            'orders': {
                'total': total_orders,
                'pending': pending_orders,
                'paid': paid_orders,
                'processing': processing_orders,
                'delivered': delivered_orders,
                'cancelled': cancelled_orders,
                'confirmed': confirmed_orders,
                'ready': ready_orders
            },
            'revenue': total_revenue,
            'wallet_balance': total_wallet_balance,
            'top_users': top_users_data,
            'daily_stats': daily_stats
        }
    })


@admin_required
def api_users_list(request):
    """API لیست کاربران با جستجو و فیلتر"""
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 25))
    is_active = request.GET.get('is_active')
    is_staff = request.GET.get('is_staff')
    is_banned = request.GET.get('is_banned')
    is_online = request.GET.get('is_online')
    gender = request.GET.get('gender')
    is_verified = request.GET.get('is_verified')
    is_payment = request.GET.get('is_payment')
    sort_by = request.GET.get('sort_by', '-createAt')

    allowed_sorts = ['createAt', '-createAt', 'mobileNumber', '-mobileNumber', 'family', '-family']
    if sort_by not in allowed_sorts:
        sort_by = '-createAt'

    users = CustomUser.objects.select_related('security', 'loyalty', 'wallet').all()

    if search:
        users = users.filter(
            Q(mobileNumber__icontains=search) |
            Q(name__icontains=search) |
            Q(family__icontains=search) |
            Q(email__icontains=search) |
            Q(shop_name__icontains=search)
        )

    if is_active in ['true', 'false']:
        users = users.filter(is_active=is_active == 'true')

    if is_staff in ['true', 'false']:
        users = users.filter(is_staff=is_staff == 'true')

    if is_banned in ['true', 'false']:
        users = users.filter(security__isBan=is_banned == 'true')

    if is_online in ['true', 'false']:
        users = users.filter(is_online=is_online == 'true')

    if gender in ['M', 'F']:
        users = users.filter(gender=gender)

    if is_verified in ['true', 'false']:
        users = users.filter(security__isVerfiyByManager=is_verified == 'true')

    if is_payment in ['true', 'false']:
        users = users.filter(security__isPeymentuser=is_payment == 'true')

    users = users.order_by(sort_by)

    paginator = Paginator(users, page_size)
    page_obj = paginator.get_page(page)

    users_data = []
    for user in page_obj:
        security = getattr(user, 'security', None)
        loyalty = getattr(user, 'loyalty', None)
        wallet = getattr(user, 'wallet', None)
        orders_count = user.orders.count()
        user_roles = list(user.roles.values('id', 'title'))

        users_data.append({
            'id': str(user.id),
            'mobileNumber': user.mobileNumber,
            'name': user.name or '',
            'family': user.family or '',
            'full_name': f'{user.name} {user.family}' or user.mobileNumber,
            'email': user.email or '',
            'gender': user.gender,
            'gender_display': user.get_gender_display(),
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_online': user.is_online,
            'is_banned': security.isBan if security else False,
            'is_verified_by_manager': security.isVerfiyByManager if security else False,
            'is_payment_user': security.isPeymentuser if security else False,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'created_at': user.createAt.isoformat(),
            'age': user.age,
            'shop_name': user.shop_name or '',
            'avatar': user.avatar.url if user.avatar else None,
            'total_points': loyalty.total_points if loyalty else 0,
            'wallet_balance': float(wallet.balance) if wallet and wallet.balance else 0,
            'orders_count': orders_count,
            'roles': user_roles
        })

    return JsonResponse({
        'success': True,
        'data': {
            'users': users_data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'page_size': page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            },
            'filters_applied': {
                'search': search,
                'is_active': is_active,
                'is_staff': is_staff,
                'is_banned': is_banned,
                'is_online': is_online,
                'gender': gender,
                'is_verified': is_verified,
                'is_payment': is_payment
            }
        }
    })


@admin_required
def api_user_detail(request, user_id):
    """API جزئیات کامل یک کاربر"""
    user = get_object_or_404(CustomUser.objects.select_related('security', 'loyalty', 'wallet'), id=user_id)
    security = getattr(user, 'security', None)
    loyalty = getattr(user, 'loyalty', None)
    wallet = getattr(user, 'wallet', None)
    user_roles = list(user.roles.values('id', 'title'))

    addresses = []
    for addr in user.addresses.all():
        addresses.append({
            'id': str(addr.id),
            'type': addr.address_type,
            'type_display': addr.get_address_type_display(),
            'province': addr.province.name if addr.province else '',
            'city': addr.city.name if addr.city else '',
            'address': addr.address_text,
            'postal_code': addr.postal_code or '',
            'is_default': addr.is_default
        })

    recent_orders = []
    for order in user.orders.order_by('-created_at')[:10]:
        recent_orders.append({
            'id': str(order.id),
            'order_number': order.order_number,
            'total': float(order.total) if order.total else 0,
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.isoformat(),
            'items_count': order.items.count()
        })

    wallet_transactions = []
    if wallet:
        for trans in wallet.transactions.all().order_by('-created_at')[:20]:
            wallet_transactions.append({
                'amount': float(trans.amount),
                'type': trans.transaction_type,
                'type_display': trans.get_transaction_type_display(),
                'status': trans.status,
                'description': trans.description or '',
                'created_at': trans.created_at.isoformat()
            })

    loyalty_transactions = []
    if loyalty:
        for trans in loyalty.transactions.all().order_by('-created_at')[:20]:
            loyalty_transactions.append({
                'points': trans.points,
                'type': trans.transaction_type,
                'type_display': trans.get_transaction_type_display(),
                'description': trans.description or '',
                'created_at': trans.created_at.isoformat()
            })

    payments = []
    for payment in Peyment.objects.filter(customer=user).order_by('-createAt')[:10]:
        payments.append({
            'amount': payment.amount,
            'is_finaly': payment.isFinaly,
            'ref_id': payment.refId or '',
            'method': payment.payment_method,
            'created_at': payment.createAt.isoformat()
        })

    total_orders = user.orders.count()
    total_spent = user.orders.filter(status='paid').aggregate(total=Sum('total'))['total'] or 0
    if isinstance(total_spent, Decimal):
        total_spent = float(total_spent)

    avg_order_value = user.orders.filter(status='paid').aggregate(avg=Avg('total'))['avg'] or 0
    if isinstance(avg_order_value, Decimal):
        avg_order_value = float(avg_order_value)

    return JsonResponse({
        'success': True,
        'data': {
            'id': str(user.id),
            'mobileNumber': user.mobileNumber,
            'email': user.email,
            'name': user.name or '',
            'family': user.family or '',
            'full_name': f'{user.name} {user.family}' or user.mobileNumber,
            'gender': user.gender,
            'gender_display': user.get_gender_display(),
            'birth_date': user.birth_date.isoformat() if user.birth_date else None,
            'age': user.age,
            'shop_name': user.shop_name or '',
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_online': user.is_online,
            'last_activity': user.last_activity.isoformat() if user.last_activity else None,
            'created_at': user.createAt.isoformat(),
            'avatar': user.avatar.url if user.avatar else None,
            'roles': user_roles,
            'security': {
                'is_banned': security.isBan if security else False,
                'is_info_filed': security.isInfoFiled if security else False,
                'has_active_code': bool(security.activeCode) if security else False,
                'is_verified_by_manager': security.isVerfiyByManager if security else False,
                'is_payment_user': security.isPeymentuser if security else False
            } if security else None,
            'wallet': {
                'balance': float(wallet.balance) if wallet and wallet.balance else 0,
                'frozen_balance': float(wallet.frozen_balance) if wallet and wallet.frozen_balance else 0
            } if wallet else None,
            'loyalty': {
                'total_points': loyalty.total_points if loyalty else 0,
                'total_coins': loyalty.total_coins if loyalty else 0,
                'current_tier': loyalty.current_tier if loyalty else 'bronze',
                'tier_display': loyalty.get_current_tier_display() if loyalty else 'برنزی',
                'lifetime_purchase': float(loyalty.lifetime_purchase) if loyalty and loyalty.lifetime_purchase else 0
            } if loyalty else None,
            'addresses': addresses,
            'recent_orders': recent_orders,
            'wallet_transactions': wallet_transactions,
            'loyalty_transactions': loyalty_transactions,
            'payments': payments,
            'stats': {
                'total_orders': total_orders,
                'total_spent': total_spent,
                'avg_order_value': avg_order_value
            }
        }
    })


@admin_required
def api_user_toggle_verified(request, user_id):
    """API تغییر وضعیت تایید مدیر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)
    security, _ = UserSecurity.objects.get_or_create(user=user)

    security.isVerfiyByManager = not security.isVerfiyByManager
    security.save()

    return JsonResponse({
        'success': True,
        'is_verified': security.isVerfiyByManager,
        'message': f'کاربر {"تایید شد" if security.isVerfiyByManager else "تایید لغو شد"}'
    })


@admin_required
def api_user_toggle_payment(request, user_id):
    """API تغییر وضعیت حق عضویت"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)
    security, _ = UserSecurity.objects.get_or_create(user=user)

    security.isPeymentuser = not security.isPeymentuser
    security.save()

    return JsonResponse({
        'success': True,
        'is_payment_user': security.isPeymentuser,
        'message': f'حق عضویت کاربر {"فعال شد" if security.isPeymentuser else "غیرفعال شد"}'
    })


@admin_required
def api_user_toggle_ban(request, user_id):
    """API بن/آنبان کردن کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)
    security, _ = UserSecurity.objects.get_or_create(user=user)

    security.isBan = not security.isBan
    security.save()

    return JsonResponse({
        'success': True,
        'is_banned': security.isBan,
        'message': f'کاربر {"بن شد" if security.isBan else "از بن خارج شد"}'
    })


@admin_required
def api_user_toggle_online_status(request, user_id):
    """API تغییر وضعیت آنلاین کاربر (دستی)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    if user.is_online:
        user.set_offline()
    else:
        user.set_online()

    return JsonResponse({
        'success': True,
        'is_online': user.is_online,
        'message': f'کاربر {"آنلاین شد" if user.is_online else "آفلاین شد"}'
    })


@admin_required
def api_user_toggle_active(request, user_id):
    """API تغییر وضعیت فعال/غیرفعال کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    user.is_active = not user.is_active
    user.save()

    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'کاربر {"فعال شد" if user.is_active else "غیرفعال شد"}'
    })


@admin_required
def api_user_update_wallet(request, user_id):
    """API افزایش/کاهش موجودی کیف پول کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)
    wallet, _ = Wallet.objects.get_or_create(user=user)

    try:
        data = json.loads(request.body)
        amount = int(data.get('amount', 0))
        operation = data.get('operation', 'add')

        if operation == 'add':
            wallet.balance += amount
            message = f'مبلغ {amount:,} تومان به کیف پول اضافه شد'
        else:
            if wallet.balance >= amount:
                wallet.balance -= amount
                message = f'مبلغ {amount:,} تومان از کیف پول کسر شد'
            else:
                return JsonResponse({'success': False, 'error': 'موجودی کیف پول کافی نیست'})

        wallet.save()

        from apps.user.models.profile import WalletTransaction
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='adjust',
            status='completed',
            description=f'تعدیل دستی توسط ادمین: {message}'
        )

        return JsonResponse({
            'success': True,
            'new_balance': float(wallet.balance),
            'message': message
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def api_user_update_points(request, user_id):
    """API افزایش/کاهش امتیازات کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)
    loyalty, _ = CustomerLoyalty.objects.get_or_create(user=user)

    try:
        data = json.loads(request.body)
        points = int(data.get('points', 0))
        operation = data.get('operation', 'add')

        if operation == 'add':
            loyalty.total_points += points
            message = f'{points} امتیاز به کاربر اضافه شد'
        else:
            if loyalty.total_points >= points:
                loyalty.total_points -= points
                message = f'{points} امتیاز از کاربر کسر شد'
            else:
                return JsonResponse({'success': False, 'error': 'امتیاز کاربر کافی نیست'})

        loyalty.save()

        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            points=points,
            transaction_type='adjust',
            description=f'تعدیل دستی توسط ادمین: {message}'
        )

        return JsonResponse({
            'success': True,
            'new_points': loyalty.total_points,
            'message': message
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def api_user_delete(request, user_id):
    """API حذف کاربر (سافت دیلیت)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    if request.user.id == user.id:
        return JsonResponse({'success': False, 'error': 'نمی‌توانید خودتان را حذف کنید'})

    try:
        user.is_active = False
        user.save()
        return JsonResponse({'success': True, 'message': 'کاربر غیرفعال شد'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def api_user_create(request):
    """API ایجاد کاربر جدید"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        mobile = data.get('mobileNumber')

        if not mobile:
            return JsonResponse({'success': False, 'error': 'شماره موبایل الزامی است'})

        if CustomUser.objects.filter(mobileNumber=mobile).exists():
            return JsonResponse({'success': False, 'error': 'این شماره موبایل قبلاً ثبت شده است'})

        user = CustomUser.objects.create_user(
            mobileNumber=mobile,
            password=data.get('password', '12345678'),
            name=data.get('name', ''),
            family=data.get('family', ''),
            email=data.get('email', ''),
            gender=data.get('gender', 'M'),
            shop_name=data.get('shop_name', ''),
            is_active=data.get('is_active', True),
            is_staff=data.get('is_staff', False),
        )

        UserSecurity.objects.get_or_create(user=user)
        Wallet.objects.get_or_create(user=user)

        return JsonResponse({
            'success': True,
            'message': 'کاربر با موفقیت ایجاد شد',
            'user_id': str(user.id)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def api_user_update(request, user_id):
    """API ویرایش کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    try:
        data = json.loads(request.body)

        if 'name' in data:
            user.name = data['name']
        if 'family' in data:
            user.family = data['family']
        if 'email' in data:
            user.email = data['email']
        if 'gender' in data:
            user.gender = data['gender']
        if 'shop_name' in data:
            user.shop_name = data['shop_name']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_staff' in data:
            user.is_staff = data['is_staff']
        if 'birth_date' in data and data['birth_date']:
            user.birth_date = data['birth_date']
        if data.get('new_password'):
            user.set_password(data['new_password'])

        user.save()

        if 'is_banned' in data:
            security, _ = UserSecurity.objects.get_or_create(user=user)
            security.isBan = data['is_banned']
            security.save()

        if 'is_verified' in data:
            security, _ = UserSecurity.objects.get_or_create(user=user)
            security.isVerfiyByManager = data['is_verified']
            security.save()

        if 'is_payment' in data:
            security, _ = UserSecurity.objects.get_or_create(user=user)
            security.isPeymentuser = data['is_payment']
            security.save()

        return JsonResponse({'success': True, 'message': 'کاربر با موفقیت ویرایش شد'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def api_user_get_roles(request, user_id):
    """API دریافت نقش‌های کاربر و لیست تمام نقش‌ها"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    user_roles = list(user.roles.values('id', 'title'))
    all_roles = list(Role.objects.filter(isActive=True).values('id', 'title'))

    return JsonResponse({
        'success': True,
        'user_roles': user_roles,
        'all_roles': all_roles
    })


@admin_required
def api_user_update_roles(request, user_id):
    """API به‌روزرسانی نقش‌های کاربر"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    user = get_object_or_404(CustomUser, id=user_id)

    try:
        data = json.loads(request.body)
        role_ids = data.get('role_ids', [])

        user.roles.clear()

        for role_id in role_ids:
            try:
                role = Role.objects.get(id=role_id)
                user.roles.add(role)
            except:
                pass

        new_roles = list(user.roles.values('id', 'title'))

        return JsonResponse({
            'success': True,
            'message': 'نقش‌های کاربر با موفقیت به‌روزرسانی شد',
            'roles': new_roles
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})