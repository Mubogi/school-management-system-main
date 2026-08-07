import os
import sys
import hashlib
import base64
import json
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.utils import timezone

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = Exception

SCHOOLHUB_MAGIC = b'SCHOOLHUB1'
SCHOOLHUB_EXT = '.schoolhub'


def _project_root():
    return Path(getattr(settings, 'DATA_DIR', settings.BASE_DIR))


def _data_paths():
    root = _project_root()
    return root / 'db.sqlite3', Path(settings.MEDIA_ROOT)


def _derive_fernet_key(school=None) -> bytes:
    """Deterministic Fernet key from deployment secret + school id."""
    secret = getattr(settings, 'SCHOOLHUB_BACKUP_PEPPER', getattr(settings, 'SECRET_KEY', 'officehub'))
    school_id = getattr(school, 'pk', 0) or 0
    digest = hashlib.sha256(f'{secret}:{school_id}:schoolhub-backup:v2'.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def flush_sqlite_wal():
    """Checkpoint SQLite WAL so db.sqlite3 contains all committed writes."""
    from django.db import connections
    db_path, _ = _data_paths()
    connections.close_all()
    if not db_path.exists():
        return
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.commit()
        conn.close()
    except Exception:
        pass


def close_all_db_handles():
    from django.db import connections
    connections.close_all()


def create_backup_zip():
    """Legacy zip backup (download / disk)."""
    root = _project_root()
    buffer = BytesIO()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        db_path, media_root = _data_paths()
        if db_path.exists():
            zf.write(db_path, 'db.sqlite3')

        if media_root.exists():
            for folder, _, files in os.walk(media_root):
                for fname in files:
                    full = Path(folder) / fname
                    arcname = 'media/' + str(full.relative_to(media_root)).replace('\\', '/')
                    zf.write(full, arcname)

        from core.models import SchoolConfiguration
        school = SchoolConfiguration.get_school()
        manifest = {
            'created_at': timezone.now().isoformat(),
            'app': 'Jordan Hub School System',
            'version': '1.0',
            'school_name': school.school_name if school else '',
        }
        zf.writestr('manifest.json', json.dumps(manifest, indent=2))

        from django.apps import apps
        all_data = []
        for model in apps.get_app_config('core').get_models():
            qs = model.objects.all()
            if qs.exists():
                all_data.append(serializers.serialize('json', qs))
        zf.writestr('data_export.json', '\n'.join(all_data))

    buffer.seek(0)
    return buffer, f'officehub_backup_{timestamp}.zip'


def create_schoolhub_backup(school=None):
    """Encrypted .schoolhub package (db + media + manifest)."""
    if Fernet is None:
        raise RuntimeError('Install cryptography: pip install cryptography')

    from core.models import SchoolConfiguration
    school = school or SchoolConfiguration.get_school()
    flush_sqlite_wal()
    db_path, media_root = _data_paths()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'jordan_hub_{timestamp}{SCHOOLHUB_EXT}'

    payload = BytesIO()
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, 'db.sqlite3')
        if media_root.exists():
            for folder, _, files in os.walk(media_root):
                for fname in files:
                    full = Path(folder) / fname
                    arcname = 'media/' + str(full.relative_to(media_root)).replace('\\', '/')
                    zf.write(full, arcname)
        manifest = {
            'created_at': timezone.now().isoformat(),
            'format': 'schoolhub',
            'version': '1.0',
            'school_name': school.school_name if school else '',
        }
        zf.writestr('manifest.json', json.dumps(manifest, indent=2))

    fernet = Fernet(_derive_fernet_key(school))
    encrypted = fernet.encrypt(payload.getvalue())
    out = BytesIO()
    out.write(SCHOOLHUB_MAGIC)
    out.write(encrypted)
    out.seek(0)
    return out, filename


def save_schoolhub_to_disk(school=None):
    buffer, filename = create_schoolhub_backup(school)
    backup_dir = _project_root() / 'backups'
    backup_dir.mkdir(exist_ok=True)
    dest = backup_dir / filename
    with open(dest, 'wb') as f:
        f.write(buffer.getvalue())
    return dest


def save_backup_to_disk():
    """Save legacy zip to backups/ folder."""
    buffer, filename = create_backup_zip()
    backup_dir = _project_root() / 'backups'
    backup_dir.mkdir(exist_ok=True)
    dest = backup_dir / filename
    with open(dest, 'wb') as f:
        f.write(buffer.getvalue())
    return dest


def _rollback_paths(rollback_dir: Path):
    db_path, media_root = _data_paths()
    rb_db = rollback_dir / 'db.sqlite3'
    rb_media = rollback_dir / 'media'
    if rb_db.exists():
        shutil.copy2(rb_db, db_path)
    if rb_media.exists():
        if media_root.exists():
            shutil.rmtree(media_root, ignore_errors=True)
        shutil.copytree(rb_media, media_root)


def restore_schoolhub_backup(uploaded_file, school=None):
    """Restore from encrypted .schoolhub with rollback on failure."""
    if Fernet is None:
        raise RuntimeError('Install cryptography: pip install cryptography')

    from core.models import SchoolConfiguration
    school = school or SchoolConfiguration.get_school()
    raw = uploaded_file.read()
    if not raw.startswith(SCHOOLHUB_MAGIC):
        raise ValueError('Invalid .schoolhub file — integrity check failed')

    fernet = Fernet(_derive_fernet_key(school))
    try:
        decrypted = fernet.decrypt(raw[len(SCHOOLHUB_MAGIC):])
    except InvalidToken:
        raise ValueError('Backup decryption failed — tampered or wrong deployment key')

    with zipfile.ZipFile(BytesIO(decrypted), 'r') as zf:
        bad = zf.testzip()
        if bad:
            raise ValueError(f'Corrupt archive entry: {bad}')

    root = _project_root()
    rollback_dir = root / 'backups' / f'_rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    rollback_dir.mkdir(parents=True, exist_ok=True)
    db_path, media_root = _data_paths()

    close_all_db_handles()

    try:
        if db_path.exists():
            shutil.copy2(db_path, rollback_dir / 'db.sqlite3')
        if media_root.exists():
            shutil.copytree(media_root, rollback_dir / 'media')

        temp_dir = root / 'backups' / '_restore_temp'
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)

        with zipfile.ZipFile(BytesIO(decrypted), 'r') as zf:
            zf.extractall(temp_dir)

        db_src = temp_dir / 'db.sqlite3'
        if db_src.exists():
            shutil.copy2(db_src, db_path)

        media_src = temp_dir / 'media'
        if media_src.exists():
            if media_root.exists():
                shutil.rmtree(media_root)
            shutil.copytree(media_src, media_root)

        shutil.rmtree(temp_dir, ignore_errors=True)
        close_all_db_handles()
        return {'restored': True, 'rollback_dir': str(rollback_dir)}
    except Exception as exc:
        close_all_db_handles()
        _rollback_paths(rollback_dir)
        raise RuntimeError(f'Restore failed; automatic rollback applied. ({exc})') from exc


def restore_backup_zip(uploaded_file):
    """Restore database and media from uploaded backup zip or .schoolhub."""
    name = getattr(uploaded_file, 'name', '') or ''
    if name.lower().endswith(SCHOOLHUB_EXT):
        return restore_schoolhub_backup(uploaded_file)

    root = _project_root()
    rollback_dir = root / 'backups' / f'_rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    rollback_dir.mkdir(parents=True, exist_ok=True)
    db_path, media_root = _data_paths()

    close_all_db_handles()

    if db_path.exists():
        shutil.copy2(db_path, rollback_dir / 'db.sqlite3')
    if media_root.exists():
        shutil.copytree(media_root, rollback_dir / 'media')

    temp_dir = root / 'backups' / '_restore_temp'
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        with zipfile.ZipFile(uploaded_file, 'r') as zf:
            bad = zf.testzip()
            if bad:
                raise ValueError(f'Corrupt zip entry: {bad}')
            zf.extractall(temp_dir)

        db_src = temp_dir / 'db.sqlite3'
        if db_src.exists():
            shutil.copy2(db_src, db_path)

        media_src = temp_dir / 'media'
        if media_src.exists():
            if media_root.exists():
                shutil.rmtree(media_root)
            shutil.copytree(media_src, media_root)

        shutil.rmtree(temp_dir, ignore_errors=True)
        close_all_db_handles()
        return {'restored': True, 'rollback_dir': str(rollback_dir)}
    except Exception as exc:
        close_all_db_handles()
        _rollback_paths(rollback_dir)
        raise RuntimeError(f'Restore failed; automatic rollback applied. ({exc})') from exc


def should_run_auto_backup(school):
    if not school or not school.backup_auto_sync_enabled:
        return False
    if not school.backup_last_export_at:
        return True
    days = school.backup_auto_sync_days or 7
    delta = timezone.now() - school.backup_last_export_at
    return delta.days >= days


def get_local_network_url(request):
    import socket

    host = request.get_host().split(':')[0]
    port = str(request.get_port()) if hasattr(request, 'get_port') else str(request.META.get('SERVER_PORT', '8000'))

    lan_ip = host
    if host in ('127.0.0.1', 'localhost'):
        lan_ip = get_lan_ip()

    scheme = 'https' if request.is_secure() else 'http'
    return f'{scheme}://{lan_ip}:{port}/'


def get_lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def server_accepts_lan(request):
    host_header = request.get_host().split(':')[0]
    return host_header not in ('127.0.0.1', 'localhost') or request.META.get('HTTP_X_FORWARDED_FOR')


def cloud_outbox_dir():
    d = _project_root() / 'cloud_outbox'
    d.mkdir(exist_ok=True)
    return d


def reset_system_factory(jordan_user):
    from django.apps import apps
    from django.contrib.auth import get_user_model
    from core.models import SchoolConfiguration, UserProfile, StudentIDSequence, PromotionCriteria

    User = get_user_model()
    jordan_id = jordan_user.pk

    core_models = list(apps.get_app_config('core').get_models())
    skip_labels = {'core.userprofile', 'core.schoolconfiguration'}
    for model in reversed(core_models):
        if model._meta.label_lower in skip_labels:
            continue
        model.objects.all().delete()

    UserProfile.objects.exclude(user_id=jordan_id).delete()
    User.objects.exclude(pk=jordan_id).delete()

    SchoolConfiguration.objects.all().delete()
    school = SchoolConfiguration.objects.create(
        school_name='My School',
        school_initials_prefix='SCH',
        network_app_name='Jordan Hub School System',
        is_active=True,
    )
    PromotionCriteria.objects.get_or_create(school=school)
    StudentIDSequence.objects.get_or_create(school=school, defaults={'last_number': 0})

    profile, _ = UserProfile.objects.get_or_create(user=jordan_user)
    profile.role = 'SUPER_ADMIN'
    profile.school = school
    profile.is_active = True
    profile.save()

    jordan_user.is_superuser = True
    jordan_user.is_staff = True
    jordan_user.is_active = True
    jordan_user.save()

    _, media_root = _data_paths()
    if media_root.exists():
        shutil.rmtree(media_root, ignore_errors=True)
    media_root.mkdir(parents=True, exist_ok=True)

    return school
