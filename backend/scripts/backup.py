#!/usr/bin/env python
"""
PostgreSQL Backup Script for Hospital Management System.

Creates encrypted, compressed backups with verification.
"""

import os
import sys
import subprocess
import gzip
import shutil
import logging
import argparse
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles PostgreSQL database backups."""

    def __init__(self, database_url: str, backup_dir: str, encryption_key: str = None):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.encryption_key = encryption_key
        self.cipher = Fernet(encryption_key.encode()) if encryption_key else None

        # Parse database URL
        self.db_config = self._parse_database_url(database_url)

    def _parse_database_url(self, url: str) -> dict:
        """Parse PostgreSQL connection URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],
            'user': parsed.username,
            'password': parsed.password,
        }

    def create_backup(self, suffix: str = None) -> Path:
        """
        Create a database backup.

        Returns:
            Path to the backup file
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        suffix = f"_{suffix}" if suffix else ""
        filename = f"hms_backup_{timestamp}{suffix}.sql"

        # Create uncompressed backup first
        uncompressed_path = self.backup_dir / filename
        compressed_path = self.backup_dir / f"{filename}.gz"
        final_path = compressed_path

        logger.info(f"Creating backup: {filename}")

        # Run pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['password']

        cmd = [
            'pg_dump',
            '-h', self.db_config['host'],
            '-p', str(self.db_config['port']),
            '-U', self.db_config['user'],
            '-d', self.db_config['database'],
            '--no-owner',
            '--no-privileges',
            '--format=plain',
            '--file', str(uncompressed_path),
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            raise RuntimeError(f"Backup failed: {result.stderr}")

        logger.info(f"Uncompressed backup size: {uncompressed_path.stat().st_size} bytes")

        # Compress
        logger.info("Compressing backup...")
        with open(uncompressed_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed
        uncompressed_path.unlink()

        logger.info(f"Compressed backup size: {compressed_path.stat().st_size} bytes")

        # Encrypt if key provided
        if self.cipher:
            encrypted_path = self.backup_dir / f"{filename}.gz.enc"
            logger.info("Encrypting backup...")
            with open(compressed_path, 'rb') as f_in:
                encrypted_data = self.cipher.encrypt(f_in.read())
            with open(encrypted_path, 'wb') as f_out:
                f_out.write(encrypted_data)
            compressed_path.unlink()
            final_path = encrypted_path
            logger.info(f"Encrypted backup size: {final_path.stat().st_size} bytes")

        # Verify backup
        if not self.verify_backup(final_path):
            raise RuntimeError("Backup verification failed")

        logger.info(f"Backup completed: {final_path}")
        return final_path

    def verify_backup(self, backup_path: Path) -> bool:
        """
        Verify backup integrity by attempting to read it.

        Returns:
            True if backup is valid
        """
        logger.info(f"Verifying backup: {backup_path.name}")

        try:
            if backup_path.suffix == '.enc':
                # Decrypt first
                with open(backup_path, 'rb') as f_in:
                    decrypted = self.cipher.decrypt(f_in.read())
                # Check if it's valid gzip
                import gzip
                with gzip.GzipFile(fileobj=type('obj', (object,), {'read': lambda self, n: decrypted[:n]})()) as gz:
                    gz.read(1024)  # Read first 1KB to verify
            elif backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rb') as f:
                    f.read(1024)
            else:
                # Plain SQL
                with open(backup_path, 'r') as f:
                    f.read(1024)

            logger.info("Backup verification passed")
            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def restore_backup(self, backup_path: Path, target_database: str = None) -> bool:
        """
        Restore database from backup.

        WARNING: This will overwrite the target database!
        """
        logger.warning(f"Starting restore from: {backup_path.name}")

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Determine target database
        target_db = target_database or self.db_config['database']

        # Prepare file for restore
        if backup_path.suffix == '.enc':
            if not self.cipher:
                raise ValueError("Encryption key required for encrypted backup")
            logger.info("Decrypting backup...")
            with open(backup_path, 'rb') as f_in:
                decrypted = self.cipher.decrypt(f_in.read())
            temp_path = backup_path.with_suffix('.sql.gz')
            with open(temp_path, 'wb') as f_out:
                f_out.write(decrypted)
            restore_path = temp_path
        elif backup_path.suffix == '.gz':
            restore_path = backup_path
        else:
            restore_path = backup_path

        # Decompress if needed
        if restore_path.suffix == '.gz':
            logger.info("Decompressing backup...")
            sql_path = restore_path.with_suffix('.sql')
            with gzip.open(restore_path, 'rb') as f_in:
                with open(sql_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            restore_path = sql_path

        # Run pg_restore or psql
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['password']

        if restore_path.suffix == '.sql':
            cmd = [
                'psql',
                '-h', self.db_config['host'],
                '-p', str(self.db_config['port']),
                '-U', self.db_config['user'],
                '-d', target_db,
                '-f', str(restore_path),
                '-v', 'ON_ERROR_STOP=1',
            ]
        else:
            # Custom format
            cmd = [
                'pg_restore',
                '-h', self.db_config['host'],
                '-p', str(self.db_config['port']),
                '-U', self.db_config['user'],
                '-d', target_db,
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                str(restore_path),
            ]

        logger.info("Running restore...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        # Cleanup temp files
        for temp_file in [restore_path.with_suffix('.sql'), restore_path.with_suffix('.sql.gz')]:
            if temp_file.exists() and temp_file != backup_path:
                temp_file.unlink()

        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            return False

        logger.info("Restore completed successfully")
        return True

    def list_backups(self) -> list:
        """List available backups."""
        backups = []
        for ext in ['.sql.gz.enc', '.sql.gz', '.sql']:
            for backup in self.backup_dir.glob(f'*{ext}'):
                stat = backup.stat()
                backups.append({
                    'name': backup.name,
                    'path': backup,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'encrypted': ext == '.sql.gz.enc',
                })
        return sorted(backups, key=lambda x: x['created'], reverse=True)

    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention_days."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        removed = 0

        for backup in self.list_backups():
            if backup['created'] < cutoff:
                logger.info(f"Removing old backup: {backup['name']}")
                backup['path'].unlink()
                removed += 1

        logger.info(f"Cleanup complete. Removed {removed} backups.")
        return removed


def main():
    parser = argparse.ArgumentParser(description='HMS Database Backup Tool')
    parser.add_argument('action', choices=['create', 'restore', 'list', 'verify', 'cleanup'],
                        help='Action to perform')
    parser.add_argument('--database-url', required=True, help='PostgreSQL connection URL')
    parser.add_argument('--backup-dir', default='/backups', help='Backup directory')
    parser.add_argument('--encryption-key', help='Encryption key (base64 encoded)')
    parser.add_argument('--backup-file', help='Backup file for restore/verify')
    parser.add_argument('--target-database', help='Target database for restore')
    parser.add_argument('--retention-days', type=int, default=30, help='Retention days for cleanup')

    args = parser.parse_args()

    # Get encryption key from env if not provided
    encryption_key = args.encryption_key or os.environ.get('BACKUP_ENCRYPTION_KEY')

    backup = DatabaseBackup(args.database_url, args.backup_dir, encryption_key)

    try:
        if args.action == 'create':
            backup.create_backup()
        elif args.action == 'restore':
            if not args.backup_file:
                parser.error('--backup-file required for restore')
            backup.restore_backup(Path(args.backup_file), args.target_database)
        elif args.action == 'list':
            backups = backup.list_backups()
            for b in backups:
                print(f"{b['name']} - {b['size']} bytes - {b['created']} - {'encrypted' if b['encrypted'] else 'plain'}")
        elif args.action == 'verify':
            if not args.backup_file:
                parser.error('--backup-file required for verify')
            backup.verify_backup(Path(args.backup_file))
        elif args.action == 'cleanup':
            backup.cleanup_old_backups(args.retention_days)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()