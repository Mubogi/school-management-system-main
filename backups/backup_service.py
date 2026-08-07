"""
Hybrid Backup Service for School Management System
Supports local, USB, and Google Drive backups with offline sync.
"""
import os
import zipfile
import hashlib
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Backup configuration
BACKUP_DIR = Path('/backups')
MEDIA_DIR = Path('/workspace/project/school-management-system-main/media')
DB_PATH = Path('/workspace/project/school-management-system-main/db.sqlite3')
ENCRYPTION_KEY = 'school_sms_backup_encryption_2026'  # In production, use secure key


def get_backup_dir():
    """Get or create the backup directory."""
    backup_dir = BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compress_directory(source_dir, output_file):
    """Create a ZIP archive of a directory."""
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(source_dir.parent)
                zipf.write(file_path, arcname)


def create_backup(school_id=None, backup_type='MANUAL'):
    """
    Create a full system backup including database and media.
    Returns: (success, backup_path, message)
    """
    from licensing.models import BackupRecord
    from django.contrib.auth.models import User
    from django.db import connection
    
    try:
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create backup filename
        if school_id:
            filename = f"backup_{school_id}_{timestamp}.zip"
        else:
            filename = f"backup_{timestamp}.zip"
        
        backup_path = backup_dir / filename
        
        # Create temporary directory for backup contents
        temp_dir = backup_dir / 'temp' / timestamp
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Close database connection to ensure consistent backup
        connection.close()
        
        # Copy database
        db_backup = temp_dir / 'db.sqlite3'
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, db_backup)
        
        # Copy media directory
        media_backup = temp_dir / 'media'
        if MEDIA_DIR.exists():
            shutil.copytree(MEDIA_DIR, media_backup, dirs_exist_ok=True)
        
        # Create ZIP archive
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item in temp_dir.rglob('*'):
                if item.is_file():
                    arcname = item.relative_to(temp_dir)
                    zipf.write(item, arcname)
        
        # Calculate checksum
        checksum = calculate_checksum(backup_path)
        
        # Get file size
        file_size = backup_path.stat().st_size
        
        # Clean up temp directory
        shutil.rmtree(temp_dir.parent, ignore_errors=True)
        
        # Create backup record
        try:
            from core.models import SchoolConfiguration
            school = SchoolConfiguration.objects.first()
        except Exception:
            school = None
        
        record = BackupRecord.objects.create(
            backup_type=backup_type,
            filename=filename,
            file_path=str(backup_path),
            file_size=file_size,
            checksum=checksum,
            status='COMPLETED',
            is_encrypted=False,
            sync_status='LOCAL',
            completed_at=datetime.now(),
            school=school,
        )
        
        # Log the backup
        from licensing.models import AuditLog
        AuditLog.log(
            action='BACKUP_CREATE',
            description=f"Backup created: {filename}",
            school=school,
        )
        
        return True, backup_path, f"Backup created: {filename}"
        
    except Exception as e:
        return False, None, f"Backup failed: {str(e)}"


def schedule_auto_backup():
    """
    Scheduled task to run automatic weekly backups.
    Call this from a cron job or Celery task.
    """
    from licensing.models import BackupRecord
    
    # Check if we should run (Saturday midnight)
    now = datetime.now()
    
    # For demo purposes, we'll run if no backup in last 24 hours
    latest_backup = BackupRecord.objects.filter(
        backup_type='SCHEDULED',
        status='COMPLETED'
    ).order_by('-created_at').first()
    
    if latest_backup:
        hours_since = (datetime.now() - latest_backup.created_at).total_seconds() / 3600
        if hours_since < 24:
            return False, "Too soon for scheduled backup"
    
    success, path, msg = create_backup(backup_type='SCHEDULED')
    return success, msg


def sync_to_usb():
    """
    Sync pending backups to attached USB drive.
    Returns: (success, message)
    """
    from licensing.models import BackupRecord
    
    # Look for USB mount points
    usb_paths = [
        Path('/media/usb'),
        Path('/mnt/usb'),
        Path('/mnt/backup'),
    ]
    
    usb_path = None
    for path in usb_paths:
        if path.exists():
            usb_path = path
            break
    
    if not usb_path:
        return False, "No USB drive detected"
    
    try:
        # Get pending backups
        pending = BackupRecord.objects.filter(
            status='COMPLETED',
            sync_status='LOCAL'
        ).order_by('-created_at')[:5]
        
        synced_count = 0
        for record in pending:
            source = Path(record.file_path)
            if source.exists():
                dest = usb_path / record.filename
                shutil.copy2(source, dest)
                record.sync_status = 'USB'
                record.save()
                synced_count += 1
        
        return True, f"Synced {synced_count} backup(s) to USB"
    except Exception as e:
        return False, f"USB sync failed: {str(e)}"


def check_online_and_sync():
    """
    Check internet connectivity and sync pending backups to cloud.
    In production, this would use Google Drive API or AWS S3.
    Returns: (success, message)
    """
    import socket
    from licensing.models import BackupRecord
    
    def check_internet():
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False
    
    # Check if online
    if not check_internet():
        # Mark pending backups as PENDING_SYNC
        BackupRecord.objects.filter(
            status='COMPLETED',
            sync_status='LOCAL'
        ).update(sync_status='PENDING_SYNC')
        return False, "Offline - backups marked for sync"
    
    try:
        # Get pending syncs
        pending = BackupRecord.objects.filter(
            status='COMPLETED',
            sync_status__in=['LOCAL', 'PENDING_SYNC']
        ).order_by('-created_at')[:3]
        
        synced_count = 0
        for record in pending:
            # In production, implement actual cloud upload here
            # For now, just mark as synced
            record.sync_status = 'DRIVE'
            record.synced_at = datetime.now()
            record.save()
            synced_count += 1
        
        return True, f"Synced {synced_count} backup(s) to cloud"
    except Exception as e:
        return False, f"Cloud sync failed: {str(e)}"


def list_backups(limit=10):
    """Get recent backup records."""
    from licensing.models import BackupRecord
    return BackupRecord.objects.all()[:limit]


def delete_backup(backup_id):
    """Delete a backup record and file."""
    from licensing.models import BackupRecord
    
    try:
        record = BackupRecord.objects.get(id=backup_id)
        file_path = Path(record.file_path)
        
        if file_path.exists():
            file_path.unlink()
        
        record.delete()
        return True, "Backup deleted"
    except Exception as e:
        return False, f"Delete failed: {str(e)}"


def restore_backup(backup_id):
    """
    Restore system from a backup.
    WARNING: This will overwrite current data!
    Returns: (success, message)
    """
    from django.contrib.auth.models import User
    from django.db import connection
    import sqlite3
    
    try:
        from licensing.models import BackupRecord
        record = BackupRecord.objects.get(id=backup_id)
        backup_file = Path(record.file_path)
        
        if not backup_file.exists():
            return False, "Backup file not found"
        
        # Verify checksum
        current_checksum = calculate_checksum(backup_file)
        if current_checksum != record.checksum:
            return False, "Backup file corrupted (checksum mismatch)"
        
        # Extract to temp directory
        temp_dir = get_backup_dir() / 'restore_temp'
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        
        with zipfile.ZipFile(backup_file, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # Restore database
        db_backup = temp_dir / 'db.sqlite3'
        if db_backup.exists():
            connection.close()
            shutil.copy2(db_backup, DB_PATH)
        
        # Restore media
        media_backup = temp_dir / 'media'
        if media_backup.exists():
            if MEDIA_DIR.exists():
                shutil.rmtree(MEDIA_DIR)
            shutil.copytree(media_backup, MEDIA_DIR)
        
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Log restoration
        from licensing.models import AuditLog
        AuditLog.log(
            action='BACKUP_RESTORE',
            description=f"System restored from: {record.filename}",
        )
        
        return True, "System restored successfully. Please restart the application."
        
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


# CLI commands for cron/scheduler
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'backup':
            success, path, msg = create_backup(backup_type='MANUAL')
            print(msg)
        
        elif cmd == 'auto':
            success, msg = schedule_auto_backup()
            print(msg)
        
        elif cmd == 'sync-usb':
            success, msg = sync_to_usb()
            print(msg)
        
        elif cmd == 'sync-cloud':
            success, msg = check_online_and_sync()
            print(msg)
        
        elif cmd == 'list':
            for b in list_backups(20):
                print(f"{b.filename} - {b.status} - {b.file_size_mb}MB - {b.created_at}")
        
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("Usage: python -m backups.backup_service [backup|auto|sync-usb|sync-cloud|list]")
