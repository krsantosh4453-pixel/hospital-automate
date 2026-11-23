#!/usr/bin/env bash
# Encrypted backups for the docker-compose.prod.yml stack, plus a restore drill.
#
# Runs on the Docker host from the repository root. Needs only Docker: pg_dump
# runs in the postgres container and encryption in the backend container, so
# the host needs no PostgreSQL client or Python packages.
#
#   scripts/deploy/backup.sh create              # database + media, encrypted
#   scripts/deploy/backup.sh verify FILE          # decrypts and checks a backup
#   scripts/deploy/backup.sh restore-check FILE   # restores a DB backup into a
#                                                 # scratch database, compares, drops it
#   scripts/deploy/backup.sh restore FILE NEWDB   # restores into a NEW database
#                                                 # (never over an existing one)
#   scripts/deploy/backup.sh prune                # deletes backups older than RETENTION_DAYS
#
# Files are Fernet(gzip(...)) with BACKUP_ENCRYPTION_KEY from the env file, the
# same format as backend/scripts/backup.py (*.sql.gz.enc), so either tool can
# verify or restore them. Overwriting the live database is deliberately not
# offered: restore into NEWDB, then switch POSTGRES_DB to it
# (docs/STAGING_DEPLOYMENT.md, "Restore after data loss").
set -euo pipefail

ENV_FILE=${ENV_FILE:-.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/hms}
RETENTION_DAYS=${RETENTION_DAYS:-30}
SCRATCH_DB=hms_restore_check

dc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# stdin -> stdout through Fernet, inside the backend container (it has the key
# and the cryptography package). Refuses to run without a key: these files
# hold patient data.
FERNET_PY='
import os, sys
from cryptography.fernet import Fernet
key = os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip()
if not key:
    sys.exit("BACKUP_ENCRYPTION_KEY is not set in the env file; refusing to handle unencrypted backups")
f = Fernet(key.encode())
data = sys.stdin.buffer.read()
sys.stdout.buffer.write(f.encrypt(data) if sys.argv[1] == "encrypt" else f.decrypt(data))
'
# One-off containers from the backend image: they work while the backend
# service is stopped (during a restore) and never run its entrypoint.
in_backend_image() { dc run --rm --no-deps -T -e RUN_MIGRATIONS=false --entrypoint "$1" backend "${@:2}"; }
encrypt() { in_backend_image python -c "$FERNET_PY" encrypt; }
decrypt() { in_backend_image python -c "$FERNET_PY" decrypt; }
psql_in() { local db=$1; shift; dc exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d $db -v ON_ERROR_STOP=1 $*"; }

create() {
  umask 077
  mkdir -p "$BACKUP_DIR"
  local stamp db media
  stamp=$(date -u +%Y%m%d_%H%M%S)
  db="$BACKUP_DIR/hms_backup_${stamp}.sql.gz.enc"
  media="$BACKUP_DIR/hms_media_${stamp}.tar.gz.enc"

  log "Dumping database"
  dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' \
    | gzip -c | encrypt > "$db.partial"
  mv "$db.partial" "$db"

  log "Archiving media (uploaded documents, consultation audio)"
  in_backend_image tar -C /app -czf - media | encrypt > "$media.partial"
  mv "$media.partial" "$media"

  verify "$db"
  verify "$media"
  ls -l "$db" "$media" >&2
  echo "$db"
}

verify() {
  local file=$1
  [ -f "$file" ] || die "no such file: $file"
  case "$file" in
    *.sql.gz.enc)
      # head stops reading early; the SIGPIPE that gives gzip is expected, so
      # judge the result by the header text (empty if decryption failed).
      local header
      header=$(decrypt < "$file" | gzip -dc 2>/dev/null | head -c 4096 || true)
      case "$header" in
        *"PostgreSQL database dump"*) ;;
        *) die "$file is not a readable pg_dump backup (wrong key or damaged file)" ;;
      esac
      ;;
    *.tar.gz.enc)
      decrypt < "$file" | tar -tzf - > /dev/null || die "$file is not a readable media archive"
      ;;
    *) die "unknown backup type: $file" ;;
  esac
  log "verified: $file"
}

restore_check() {
  local file=$1 started live restored
  case "$file" in *.sql.gz.enc) ;; *) die "restore-check takes a *.sql.gz.enc database backup" ;; esac
  verify "$file"
  started=$(date +%s)

  # The scratch name is fixed and must never be the live database.
  dc exec -T postgres sh -c "[ \"\$POSTGRES_DB\" != '$SCRATCH_DB' ]" || die "POSTGRES_DB is $SCRATCH_DB"
  dc exec -T postgres sh -c "dropdb -U \"\$POSTGRES_USER\" --if-exists $SCRATCH_DB && createdb -U \"\$POSTGRES_USER\" $SCRATCH_DB"
  log "Restoring into scratch database $SCRATCH_DB"
  decrypt < "$file" | gzip -dc \
    | dc exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d $SCRATCH_DB -v ON_ERROR_STOP=1 -q" > /dev/null

  local count_sql="select (select count(*) from information_schema.tables where table_schema='public')
    || ' tables, ' || (select count(*) from django_migrations) || ' migrations'"
  live=$(dc exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -tAc \"$count_sql\"")
  restored=$(dc exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d $SCRATCH_DB -tAc \"$count_sql\"")
  dc exec -T postgres sh -c "dropdb -U \"\$POSTGRES_USER\" $SCRATCH_DB"

  log "live:     $live"
  log "restored: $restored"
  log "restore took $(( $(date +%s) - started )) s"
  [ "$live" = "$restored" ] || die "restored schema differs from live (a migration ran after this backup?)"
  log "restore check passed"
}

restore() {
  local file=$1 newdb=$2 exists
  case "$file" in *.sql.gz.enc) ;; *) die "restore takes a *.sql.gz.enc database backup" ;; esac
  [[ "$newdb" =~ ^[a-z][a-z0-9_]{0,62}$ ]] || die "NEWDB must be a plain lower-case name"
  exists=$(dc exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d postgres -tAc \"select 1 from pg_database where datname='$newdb'\"")
  [ -z "$exists" ] || die "database $newdb already exists; restore only into a new database"
  verify "$file"
  dc exec -T postgres sh -c "createdb -U \"\$POSTGRES_USER\" $newdb"
  log "Restoring $file into new database $newdb"
  decrypt < "$file" | gzip -dc | psql_in "$newdb" -q > /dev/null
  log "restored: $(psql_in "$newdb" -tAc "\"select count(*) || ' migrations' from django_migrations\"")"
  log "Next: set POSTGRES_DB=$newdb in $ENV_FILE and run 'up -d' (the old database is kept)."
}

prune() {
  [ -d "$BACKUP_DIR" ] || die "no backup directory: $BACKUP_DIR"
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'hms_*.enc' -mtime "+$RETENTION_DAYS" -print -delete
}

case "${1:-}" in
  create) create ;;
  verify) verify "${2:?usage: backup.sh verify FILE}" ;;
  restore-check) restore_check "${2:?usage: backup.sh restore-check FILE}" ;;
  restore) restore "${2:?usage: backup.sh restore FILE NEWDB}" "${3:?usage: backup.sh restore FILE NEWDB}" ;;
  prune) prune ;;
  *) sed -n '2,21p' "$0"; exit 2 ;;
esac
