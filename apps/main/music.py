# main/music.py

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Music


@require_http_methods(["GET"])
def music_list_api(request):
    """لیست همه آهنگ‌ها"""
    musics = Music.objects.all().order_by('-created_at')

    data = []
    for music in musics:
        data.append({
            'id': music.id,
            'title': music.title,
            'artist': music.artist,
            'audio_file': request.build_absolute_uri(music.audio_file.url) if music.audio_file else None,
            'cover': request.build_absolute_uri(music.cover.url) if music.cover else None,
            'created_at': music.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({
        'success': True,
        'count': len(data),
        'musics': data
    })


@require_http_methods(["GET"])
def music_detail_api(request, music_id):
    """جزئیات یه آهنگ"""
    try:
        music = Music.objects.get(id=music_id)
    except Music.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'آهنگ پیدا نشد'
        }, status=404)

    data = {
        'id': music.id,
        'title': music.title,
        'artist': music.artist,
        'audio_file': request.build_absolute_uri(music.audio_file.url) if music.audio_file else None,
        'cover': request.build_absolute_uri(music.cover.url) if music.cover else None,
        'created_at': music.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    }

    return JsonResponse({
        'success': True,
        'music': data
    })