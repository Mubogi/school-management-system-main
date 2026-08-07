"""7-day automated backup + Google Drive cloud outbox (APScheduler + network listener)."""
from __future__ import annotations

import logging
import shutil
import socket
import threading
import time
from pathlib import Path

from django.utils import timezone

logger = logging.getLogger(__name__)

_daemon_started = False
_daemon_lock = threading.Lock()
_scheduler = None


def is_online(timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection(('8.8.8.8', 53), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def upload_to_google_drive(file_path: Path, refresh_token: str, folder_id: str) -> bool:
    if not refresh_token or not folder_id:
        return False
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        logger.warning('google-api-python-client not installed')
        return False

    from django.conf import settings
    client_id = settings.GOOGLE_DRIVE_CLIENT_ID
    client_secret = settings.GOOGLE_DRIVE_CLIENT_SECRET
    if not client_id or not client_secret:
        logger.warning('GOOGLE_DRIVE_CLIENT_ID/SECRET not configured')
        return False

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id,
        client_secret=client_secret,
    )
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    meta = {'name': file_path.name, 'parents': [folder_id]}
    media = MediaFileUpload(str(file_path), resumable=True)
    service.files().create(body=meta, media_body=media, fields='id').execute()
    return True


def _folder_id_from_url(url: str) -> str:
    if not url:
        return ''
    if '/folders/' in url:
        return url.split('/folders/')[-1].split('?')[0].strip('/')
    return ''


def process_cloud_outbox() -> int:
    from core.models import SchoolConfiguration
    from core.backup_utils import cloud_outbox_dir

    school = SchoolConfiguration.get_school()
    if not school or not school.backup_google_refresh_token:
        return 0

    folder_id = school.backup_google_folder_id or _folder_id_from_url(school.backup_google_drive_url)
    if not folder_id:
        return 0

    uploaded = 0
    for path in sorted(cloud_outbox_dir().glob('*.schoolhub')):
        try:
            if upload_to_google_drive(path, school.backup_google_refresh_token, folder_id):
                path.unlink(missing_ok=True)
                uploaded += 1
        except Exception as exc:
            logger.warning('Drive upload failed %s: %s', path.name, exc)
    return uploaded


def run_scheduled_backup():
    from core.models import SchoolConfiguration
    from core.backup_utils import should_run_auto_backup, save_schoolhub_to_disk, cloud_outbox_dir

    school = SchoolConfiguration.get_school()
    if not should_run_auto_backup(school):
        return None

    path = save_schoolhub_to_disk(school)
    school.backup_last_export_at = timezone.now()
    school.save(update_fields=['backup_last_export_at'])

    if is_online() and school.backup_google_refresh_token:
        folder_id = school.backup_google_folder_id or _folder_id_from_url(school.backup_google_drive_url)
        try:
            if not upload_to_google_drive(path, school.backup_google_refresh_token, folder_id):
                dest = cloud_outbox_dir() / path.name
                shutil.move(str(path), str(dest))
        except Exception:
            dest = cloud_outbox_dir() / path.name
            shutil.move(str(path), str(dest))
    else:
        dest = cloud_outbox_dir() / path.name
        if path.resolve() != dest.resolve():
            shutil.move(str(path), str(dest))
    return path


def _network_listener_loop():
    while True:
        try:
            if is_online():
                process_cloud_outbox()
        except Exception as exc:
            logger.debug('outbox listener: %s', exc)
        time.sleep(300)


def _start_apscheduler():
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        return False

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_scheduled_backup,
        trigger=IntervalTrigger(days=7),
        id='schoolhub_weekly_backup',
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        process_cloud_outbox,
        trigger=IntervalTrigger(minutes=30),
        id='cloud_outbox_upload',
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    return True


def start_cloud_sync_daemon():
    global _daemon_started
    with _daemon_lock:
        if _daemon_started:
            return
        _daemon_started = True

    if not _start_apscheduler():
        threading.Thread(target=_fallback_scheduler_loop, name='backup-scheduler', daemon=True).start()

    threading.Thread(target=_network_listener_loop, name='network-listener', daemon=True).start()


def _fallback_scheduler_loop():
    while True:
        try:
            run_scheduled_backup()
        except Exception as exc:
            logger.debug('backup scheduler: %s', exc)
        time.sleep(86400)
