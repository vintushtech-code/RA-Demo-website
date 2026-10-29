"""
Management Command: backup_database
===================================
CLI tool to generate on-demand database snapshots and inspect automated backup health.
Provided by: VintushTech & KPRegTech for Sabin Balan (GuardianTree FP)
"""

from django.core.management.base import BaseCommand
from login.backup_service import (
    create_live_backup,
    get_latest_backups_summary,
    get_all_backups,
    restore_database_from_snapshot
)


class Command(BaseCommand):
    help = "Generate an instantaneous snapshot of the SQLite database, list backups, or restore previous data."

    def add_arguments(self, parser):
        parser.add_argument('--status', action='store_true', help='Inspect backup health and statistics')
        parser.add_argument('--list', action='store_true', help='List all available backup snapshots in the vault')
        parser.add_argument('--restore', type=str, help='Restore database from a specified snapshot filename')

    def handle(self, *args, **options):
        if options['status']:
            summary = get_latest_backups_summary()
            self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
            self.stdout.write(self.style.MIGRATE_HEADING("  Continuous Database Backup & Preservation Vault"))
            self.stdout.write(self.style.MIGRATE_HEADING("  Provided by: VintushTech & KPRegTech"))
            self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
            self.stdout.write(f"Status:            {summary.get('status')}")
            self.stdout.write(f"Total Snapshots:   {summary.get('total_backups')}")
            self.stdout.write(f"Latest Snapshot:   {summary.get('latest_file')}")
            self.stdout.write(f"Latest Timestamp:  {summary.get('latest_timestamp')}")
            self.stdout.write(f"Snapshot Size:     {summary.get('latest_size_kb')} KB")
            self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
            return

        if options['list']:
            backups = get_all_backups()
            self.stdout.write(self.style.MIGRATE_HEADING("Available Database Vault Snapshots:"))
            for b in backups:
                latest_tag = " (LATEST)" if b.get('is_latest') else ""
                self.stdout.write(f" - {b['filename']} | {b['size_kb']} KB | {b['timestamp']}{latest_tag}")
            return

        if options['restore']:
            filename = options['restore']
            res = restore_database_from_snapshot(filename)
            if res.get('success'):
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] {res.get('message')}"))
            else:
                self.stdout.write(self.style.ERROR(f"[ERROR] Restore failed: {res.get('error')}"))
            return

        res = create_live_backup(event_trigger="CLI Manual Backup")
        if res and res.get('success'):
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Database Snapshot Created: {res['file_name']} ({res['file_size_kb']} KB)"))
        else:
            self.stdout.write(self.style.ERROR(f"[ERROR] Backup failed: {res.get('error') if res else 'Unknown error'}"))
