# apps/user/views/role_views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import json
from apps.user.models.role import Role, RoleBanUrl
from apps.user.models.user import CustomUser


def role_panel_view(request):
    return render(request, 'panel_app/dashboard/roles_panel.html')


@csrf_exempt
def roles_api(request):
    page = request.GET.get('page', 1)
    page_size = int(request.GET.get('page_size', 10))
    search = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')

    roles = Role.objects.all()

    if search:
        roles = roles.filter(Q(title__icontains=search) | Q(slug__icontains=search))

    if is_active == 'true':
        roles = roles.filter(isActive=True)
    elif is_active == 'false':
        roles = roles.filter(isActive=False)

    roles = roles.order_by('title')
    paginator = Paginator(roles, page_size)

    try:
        roles_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        roles_page = paginator.page(1)

    roles_data = []
    for role in roles_page:
        ban_urls = role.ban_urls.filter(isActive=True)
        roles_data.append({
            'id': str(role.id),
            'title': role.title,
            'slug': role.slug,
            'isActive': role.isActive,
            'createAt': role.createAt.strftime('%Y-%m-%d %H:%M:%S'),
            'ban_urls': [{'id': str(b.id), 'url_pattern': b.url_pattern, 'description': b.description, 'isActive': b.isActive} for b in ban_urls],
            'users_count': role.users.count()
        })

    return JsonResponse({
        'success': True,
        'data': {
            'roles': roles_data,
            'pagination': {
                'current_page': roles_page.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': roles_page.has_next(),
                'has_previous': roles_page.has_previous(),
                'page_size': page_size
            }
        }
    })


@csrf_exempt
def role_detail_api(request, role_id):
    try:
        role = Role.objects.get(id=role_id)
        ban_urls = role.ban_urls.all()

        return JsonResponse({
            'success': True,
            'data': {
                'id': str(role.id),
                'title': role.title,
                'slug': role.slug,
                'isActive': role.isActive,
                'createAt': role.createAt.strftime('%Y-%m-%d %H:%M:%S'),
                'ban_urls': [{'id': str(b.id), 'url_pattern': b.url_pattern, 'description': b.description, 'isActive': b.isActive} for b in ban_urls],
                'users_count': role.users.count()
            }
        })
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'نقش یافت نشد'}, status=404)


@csrf_exempt
def role_create_api(request):
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        slug = data.get('slug', '').strip()
        isActive = data.get('isActive', True)

        if not title:
            return JsonResponse({'success': False, 'message': 'عنوان نقش الزامی است'})

        if Role.objects.filter(title=title).exists():
            return JsonResponse({'success': False, 'message': 'نقشی با این عنوان قبلاً ثبت شده است'})

        role = Role.objects.create(
            title=title,
            slug=slug or title.replace(' ', '_'),
            isActive=isActive
        )

        return JsonResponse({
            'success': True,
            'message': 'نقش با موفقیت ایجاد شد',
            'data': {'id': str(role.id)}
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
def role_update_api(request, role_id):
    try:
        role = Role.objects.get(id=role_id)
        data = json.loads(request.body)

        title = data.get('title', '').strip()
        if title and title != role.title:
            if Role.objects.filter(title=title).exclude(id=role_id).exists():
                return JsonResponse({'success': False, 'message': 'نقشی با این عنوان قبلاً ثبت شده است'})
            role.title = title

        role.slug = data.get('slug', role.slug)
        role.isActive = data.get('isActive', role.isActive)
        role.save()

        return JsonResponse({'success': True, 'message': 'نقش با موفقیت ویرایش شد'})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'نقش یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
def role_delete_api(request, role_id):
    try:
        role = Role.objects.get(id=role_id)

        if role.users.exists():
            return JsonResponse({
                'success': False,
                'message': f'این نقش به {role.users.count()} کاربر متصل است'
            })

        role.delete()
        return JsonResponse({'success': True, 'message': 'نقش با موفقیت حذف شد'})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'نقش یافت نشد'}, status=404)


@csrf_exempt
def ban_url_create_api(request, role_id):
    try:
        role = Role.objects.get(id=role_id)
        data = json.loads(request.body)
        url_pattern = data.get('url_pattern', '').strip()
        description = data.get('description', '')
        isActive = data.get('isActive', True)

        if not url_pattern:
            return JsonResponse({'success': False, 'message': 'الگوی URL الزامی است'})

        if RoleBanUrl.objects.filter(role=role, url_pattern=url_pattern).exists():
            return JsonResponse({'success': False, 'message': 'این URL قبلاً ثبت شده است'})

        ban_url = RoleBanUrl.objects.create(
            role=role,
            url_pattern=url_pattern,
            description=description,
            isActive=isActive
        )

        return JsonResponse({
            'success': True,
            'message': 'URL ممنوع اضافه شد',
            'data': {'id': str(ban_url.id)}
        })
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'نقش یافت نشد'}, status=404)


@csrf_exempt
def ban_url_update_api(request, ban_url_id):
    try:
        ban_url = RoleBanUrl.objects.get(id=ban_url_id)
        data = json.loads(request.body)

        ban_url.url_pattern = data.get('url_pattern', ban_url.url_pattern)
        ban_url.description = data.get('description', ban_url.description)
        ban_url.isActive = data.get('isActive', ban_url.isActive)
        ban_url.save()

        return JsonResponse({'success': True, 'message': 'URL ممنوع ویرایش شد'})
    except RoleBanUrl.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'URL یافت نشد'}, status=404)


@csrf_exempt
def ban_url_delete_api(request, ban_url_id):
    try:
        ban_url = RoleBanUrl.objects.get(id=ban_url_id)
        ban_url.delete()
        return JsonResponse({'success': True, 'message': 'URL ممنوع حذف شد'})
    except RoleBanUrl.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'URL یافت نشد'}, status=404)


@csrf_exempt
def assign_users_to_role_api(request, role_id):
    try:
        role = Role.objects.get(id=role_id)
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])

        users = CustomUser.objects.filter(id__in=user_ids)
        for user in users:
            user.roles.add(role)

        return JsonResponse({'success': True, 'message': f'{users.count()} کاربر اضافه شدند'})
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'نقش یافت نشد'}, status=404)


@csrf_exempt
def remove_user_from_role_api(request, role_id, user_id):
    try:
        role = Role.objects.get(id=role_id)
        user = CustomUser.objects.get(id=user_id)
        user.roles.remove(role)
        return JsonResponse({'success': True, 'message': 'کاربر از نقش حذف شد'})
    except (Role.DoesNotExist, CustomUser.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'یافت نشد'}, status=404)