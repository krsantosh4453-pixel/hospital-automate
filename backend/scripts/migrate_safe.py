#!/usr/bin/env python
"""
Database Migration Safety Script for Hospital Management System.

Provides safe migration practices for production deployments.
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages safe database migrations."""

    def __init__(self, settings_module: str = 'config.settings.production'):
        self.settings_module = settings_module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

    def check_migration_state(self) -> dict:
        """Check current migration state."""
        import django
        django.setup()

        from django.db import connection
        from django.db.migrations.recorder import MigrationRecorder

        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        # Get all migrations
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(connection, ignore_no_migrations=True)

        all_migrations = set()
        for app, migrations in loader.graph.nodes.items():
            for migration in migrations:
                all_migrations.add((app, migration))

        unapplied = all_migrations - applied

        return {
            'applied_count': len(applied),
            'unapplied_count': len(unapplied),
            'unapplied': sorted(list(unapplied)),
        }

    def show_migration_plan(self) -> list:
        """Show what migrations would be applied."""
        import django
        django.setup()

        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        return [(migration.app_label, migration.name) for migration in plan]

    def create_pre_migration_backup(self, database_url: str, backup_dir: str, encryption_key: str = None) -> str:
        """Create a backup before migration."""
        from scripts.backup import DatabaseBackup

        backup = DatabaseBackup(database_url, backup_dir, encryption_key)
        backup_path = backup.create_backup(suffix='pre_migration')
        logger.info(f"Pre-migration backup created: {backup_path}")
        return str(backup_path)

    def run_migrations(self, fake: bool = False, plan: bool = False) -> bool:
        """Run database migrations."""
        cmd = ['python', 'manage.py', 'migrate']

        if plan:
            cmd.append('--plan')
        if fake:
            cmd.append('--fake')

        logger.info(f"Running migrations: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
            return False

        logger.info(result.stdout)
        return True

    def check_for_destructive_operations(self) -> list:
        """Check pending migrations for destructive operations."""
        import django
        django.setup()

        from django.db import connection
        from django.db.migrations.loader import MigrationLoader
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        destructive_ops = []
        keywords = [
            'RemoveField', 'DeleteModel', 'AlterField', 'RunSQL',
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER TABLE.*DROP',
        ]

        for migration in plan:
            for operation in migration.operations:
                op_name = operation.__class__.__name__
                if op_name in ['RemoveField', 'DeleteModel']:
                    destructive_ops.append({
                        'migration': f"{migration.app_label}.{migration.name}",
                        'operation': op_name,
                        'details': str(operation),
                    })
                elif op_name == 'RunSQL':
                    sql = getattr(operation, 'sql', '')
                    if any(kw in sql.upper() for kw in ['DROP', 'DELETE', 'TRUNCATE', 'ALTER TABLE']):
                        destructive_ops.append({
                            'migration': f"{migration.app_label}.{migration.name}",
                            'operation': 'RunSQL (potentially destructive)',
                            'details': sql[:200],
                        })

        return destructive_ops

    def verify_migration_safety(self) -> bool:
        """Verify migrations are safe to run."""
        logger.info("Checking migration safety...")

        # Check for destructive operations
        destructive = self.check_for_destructive_operations()
        if destructive:
            logger.warning("POTENTIALLY DESTRUCTIVE OPERATIONS DETECTED:")
            for op in destructive:
                logger.warning(f"  {op['migration']}: {op['operation']} - {op['details']}")
            logger.warning("Review these migrations carefully before proceeding!")
            return False

        # Check migration state
        state = self.check_migration_state()
        if state['unapplied_count'] == 0:
            logger.info("No pending migrations.")
            return True

        logger.info(f"Pending migrations: {state['unapplied_count']}")
        for app, name in state['unapplied']:
            logger.info(f"  {app}.{name}")

        return True

    def rollback_migration(self, app: str, migration: str) -> bool:
        """Rollback a specific migration."""
        cmd = ['python', 'manage.py', 'migrate', app, migration]
        logger.info(f"Rolling back: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Rollback failed: {result.stderr}")
            return False

        logger.info(result.stdout)
        return True


def main():
    parser = argparse.ArgumentParser(description='HMS Migration Safety Tool')
    parser.add_argument('action', choices=['check', 'plan', 'apply', 'backup', 'verify', 'rollback'],
                        help='Action to perform')
    parser.add_argument('--settings', default='config.settings.production', help='Django settings module')
    parser.add_argument('--database-url', help='Database URL for backup')
    parser.add_argument('--backup-dir', default='/backups', help='Backup directory')
    parser.add_argument('--encryption-key', help='Backup encryption key')
    parser.add_argument('--app', help='App name for rollback')
    parser.add_argument('--migration', help='Migration name for rollback')
    parser.add_argument('--fake', action='store_true', help='Fake migrations')
    parser.add_argument('--force', action='store_true', help='Force destructive operations')

    args = parser.parse_args()

    manager = MigrationManager(args.settings)

    try:
        if args.action == 'check':
            state = manager.check_migration_state()
            print(f"Applied migrations: {state['applied_count']}")
            print(f"Pending migrations: {state['unapplied_count']}")
            for app, name in state['unapplied']:
                print(f"  {app}.{name}")

        elif args.action == 'plan':
            plan = manager.show_migration_plan()
            print("Migration plan:")
            for app, name in plan:
                print(f"  {app}.{name}")

        elif args.action == 'verify':
            if not manager.verify_migration_safety():
                sys.exit(1)

        elif args.action == 'backup':
            if not args.database_url:
                parser.error('--database-url required for backup')
            encryption_key = args.encryption_key or os.environ.get('BACKUP_ENCRYPTION_KEY')
            manager.create_pre_migration_backup(args.database_url, args.backup_dir, encryption_key)

        elif args.action == 'apply':
            # Safety check first
            if not args.force:
                if not manager.verify_migration_safety():
                    logger.error("Migration safety check failed. Use --force to override.")
                    sys.exit(1)

            # Create backup before migration
            if args.database_url:
                encryption_key = args.encryption_key or os.environ.get('BACKUP_ENCRYPTION_KEY')
                manager.create_pre_migration_backup(args.database_url, args.backup_dir, encryption_key)

            # Run migrations
            if not manager.run_migrations(fake=args.fake):
                sys.exit(1)

        elif args.action == 'rollback':
            if not args.app or not args.migration:
                parser.error('--app and --migration required for rollback')
            if not manager.rollback_migration(args.app, args.migration):
                sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()