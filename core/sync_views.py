"""Offline client sync API — multipart image pipeline from IndexedDB."""
import base64
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def _save_image_bytes(raw: bytes, filename: str, subfolder: str = 'offline_sync') -> dict:
    media_root = Path(settings.MEDIA_ROOT) / subfolder
    media_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or f'{uuid.uuid4().hex}.bin'
    dest = media_root / safe_name
    dest.write_bytes(raw)
    return {
        'type': 'image',
        'path': str(dest.relative_to(settings.MEDIA_ROOT)),
        'size': len(raw),
    }


@login_required
@require_POST
def offline_sync_upload(request):
    """Accept multipart FormData or JSON batch from PWA offline queue."""
    saved = []

    if request.content_type and 'multipart/form-data' in request.content_type:
        for key in request.FILES:
            uploaded = request.FILES[key]
            raw = uploaded.read()
            saved.append(_save_image_bytes(raw, uploaded.name))
        text = request.POST.get('text', '').strip()
        if text:
            note_path = Path(settings.MEDIA_ROOT) / 'offline_sync' / f'note_{uuid.uuid4().hex}.txt'
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(text, encoding='utf-8')
            saved.append({'type': 'text', 'path': str(note_path.relative_to(settings.MEDIA_ROOT))})
        student_id = request.POST.get('student_id', '')
        if student_id and request.FILES.get('photo'):
            photo = request.FILES['photo']
            sub = f'student_photos/{student_id}'
            saved.append(_save_image_bytes(photo.read(), photo.name, sub))
        return JsonResponse({'ok': True, 'saved': saved, 'count': len(saved)})

    try:
        payload = json.loads(request.body.decode('utf-8'))
        items = payload.get('items', [payload])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    for item in items:
        kind = item.get('kind', 'text')
        if kind == 'image' and item.get('blob_base64'):
            raw = base64.b64decode(item['blob_base64'])
            name = item.get('filename') or f'{uuid.uuid4().hex}.png'
            saved.append(_save_image_bytes(raw, name))
        elif item.get('text'):
            note_path = Path(settings.MEDIA_ROOT) / 'offline_sync' / f'note_{uuid.uuid4().hex}.txt'
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(item['text'], encoding='utf-8')
            saved.append({'type': 'text', 'path': str(note_path.relative_to(settings.MEDIA_ROOT))})

    return JsonResponse({'ok': True, 'saved': saved, 'count': len(saved)})


@require_POST
@csrf_exempt
def offline_sync_ping(request):
    return JsonResponse({'ok': True, 'online': True, 'server': 'jordan-school-hub'})
