from django.core.management.base import BaseCommand

from core.models import SchoolConfiguration
from core.backup_utils import should_run_auto_backup, save_schoolhub_to_disk
from core.cloud_sync import process_cloud_outbox, is_online
from django.utils import timezone


class Command(BaseCommand):
    help = 'Auto-export system backup when sync interval has elapsed'

    def handle(self, *args, **options):
        school = SchoolConfiguration.get_school()
        if not should_run_auto_backup(school):
            self.stdout.write('Auto backup not due.')
            return
        path = save_schoolhub_to_disk(school)
        school.backup_last_export_at = timezone.now()
        school.save(update_fields=['backup_last_export_at'])
        self.stdout.write(self.style.SUCCESS(f'Encrypted backup saved: {path}'))
        if is_online() and school.backup_google_refresh_token:
            n = process_cloud_outbox()
            self.stdout.write(f'Cloud outbox processed: {n} upload(s)')
        elif school.backup_google_drive_url:
            self.stdout.write(f'Queued for Drive when online: {path}')
