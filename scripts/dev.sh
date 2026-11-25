#!/usr/bin/env bash
# Local development launcher for Hospital Automate: Django backend + Vite frontend.
#
#   scripts/dev.sh start   [all|backend|frontend]   (default: all)
#   scripts/dev.sh stop    [all|backend|frontend]
#   scripts/dev.sh restart [all|backend|frontend]
#   scripts/dev.sh status
#   scripts/dev.sh logs    [backend|frontend]
#   scripts/dev.sh setup   (virtualenv + migrations only)
#
# Why the virtualenv and Python's bytecode cache live outside the repo: this
# checkout sits on an iCloud-synced Desktop with "Optimize Mac Storage" on.
# macOS evicts files there (on 2026-11-24: 97% of backend/venv and 592 of 942
# __pycache__/*.pyc files), and Django then hangs at startup while Python waits
# for iCloud to download them one by one: nothing listens on the port and Vite
# answers every /api call with HTTP 502. The .py sources themselves stay local.
#
# Settings (environment variables, all optional):
#   HMS_DEV_HOME        state folder (venv, logs, pids, db backups)
#                       default: ~/.local/share/hospital-automate
#   HMS_VENV            Python virtualenv to use     default: $HMS_DEV_HOME/venv
#   HMS_BACKEND_PORT    Django port                  default: 8000
#   HMS_BACKEND_TIMEOUT seconds to wait for Django   default: 120
#   HMS_SKIP_MIGRATE=1  start without applying pending migrations
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
DEV_HOME="${HMS_DEV_HOME:-$HOME/.local/share/hospital-automate}"
VENV="${HMS_VENV:-$DEV_HOME/venv}"
HOST="127.0.0.1"
BACKEND_PORT="${HMS_BACKEND_PORT:-8000}"
BACKEND_URL="http://$HOST:$BACKEND_PORT"
FRONTEND_PORT=5173 # fixed: vite.config.js uses strictPort (Google sign-in origin)
FRONTEND_URL="http://localhost:$FRONTEND_PORT"
BACKEND_TIMEOUT="${HMS_BACKEND_TIMEOUT:-120}"
FRONTEND_TIMEOUT=60
LOCK_FILE="$BACKEND_DIR/requirements-lock.txt"
LOG_DIR="$DEV_HOME/logs"
RUN_DIR="$DEV_HOME/run"
BACKUP_DIR="$DEV_HOME/db-backups"
# Python then never reads (possibly evicted) backend/**/__pycache__ files.
export PYTHONPYCACHEPREFIX="$DEV_HOME/pycache"

info() { printf '\033[36m•\033[0m %s\n' "$*"; }
ok() { printf '\033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[33m!\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

mkdir -p "$LOG_DIR" "$RUN_DIR" "$BACKUP_DIR" || fail "Cannot create $DEV_HOME"

read_pid() { cat "$RUN_DIR/$1.pid" 2>/dev/null || true; }
pid_alive() { [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null; }
listener_pid() { lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -n 1; }
describe_pid() { ps -o pid=,command= -p "$1" 2>/dev/null | cut -c1-160; }
# Django's DEBUG logging prints every SQL query; show only the useful lines.
show_log() { grep -v ' DEBUG ' "$LOG_DIR/$1.log" 2>/dev/null | tail -n "${2:-30}" >&2; }
is_hms_backend() { curl -s --max-time 3 "$1/health/" 2>/dev/null | grep -q '"service": *"hms-backend"'; }

find_python() {
  local candidate
  for candidate in "${HMS_PYTHON:-}" python3.12 /opt/homebrew/bin/python3.12 python3; do
    [ -n "$candidate" ] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    "$candidate" -c 'import sys; sys.exit(sys.version_info[:2] < (3, 12))' 2>/dev/null || continue
    command -v "$candidate"
    return 0
  done
  return 1
}

# The venv is rebuilt whenever backend/requirements-lock.txt changes.
ensure_venv() {
  local want have python
  want=$(shasum -a 256 "$LOCK_FILE" | cut -d' ' -f1) || fail "Cannot read $LOCK_FILE"
  have=$(cat "$VENV/.requirements-lock.sha256" 2>/dev/null || true)
  if [ "$want" = "$have" ] && "$VENV/bin/python" -c 'import django' 2>/dev/null; then
    return 0
  fi
  python=$(find_python) || fail "Python 3.12+ not found. Install it with: brew install python@3.12"
  info "Preparing the backend virtualenv in $VENV (first run takes 1-2 minutes) ..."
  [ -x "$VENV/bin/python" ] || "$python" -m venv "$VENV" || fail "Could not create the virtualenv $VENV"
  if ! "$VENV/bin/python" -m pip install -q --disable-pip-version-check -r "$LOCK_FILE" >"$LOG_DIR/pip.log" 2>&1; then
    tail -n 25 "$LOG_DIR/pip.log" >&2
    fail "pip install failed (full log: $LOG_DIR/pip.log)"
  fi
  echo "$want" >"$VENV/.requirements-lock.sha256"
  ok "Virtualenv ready: $VENV"
}

# Development settings refuse to start without these (values are never printed).
check_env_file() {
  local key
  [ -f "$ROOT/.env" ] || fail "No .env file. Create it with: cp .env.example .env (then fill in the values)"
  for key in DJANGO_SECRET_KEY GOOGLE_CLIENT_ID; do
    if [ -z "${!key:-}" ] && ! grep -Eq "^$key=.+" "$ROOT/.env"; then
      fail "$key is empty in .env; Django development settings require it (see .env.example)"
    fi
  done
}

# Warn when iCloud has moved project files off this Mac: first reads stall.
icloud_check() {
  local on_disk apparent
  case "$ROOT" in
    "$HOME/Desktop"/* | "$HOME/Documents"/* | "$HOME/Library/Mobile Documents"/*) ;;
    *) return 0 ;;
  esac
  on_disk=$(du -sk -I venv "$BACKEND_DIR" 2>/dev/null | cut -f1)
  apparent=$(du -skA -I venv "$BACKEND_DIR" 2>/dev/null | cut -f1)
  if [ "${apparent:-0}" -gt 0 ] && [ $((on_disk * 100 / apparent)) -lt 80 ]; then
    warn "Only $((on_disk * 100 / apparent))% of backend/ is stored on this Mac (iCloud 'Optimize Mac Storage')."
    warn "Startup can be slow while macOS downloads files. Lasting fix: move the project out of Desktop/Documents."
  fi
}

backup_database() {
  local db="$BACKEND_DIR/db.sqlite3" target
  [ -f "$db" ] || return 0
  target="$BACKUP_DIR/db-$(date +%Y%m%d-%H%M%S).sqlite3"
  # .backup gives a consistent copy even if something else has the file open.
  sqlite3 "$db" ".backup '$target'" 2>/dev/null || cp "$db" "$target" || fail "Could not back up $db"
  info "Backed up the development database to $target"
}

# Code ahead of the database schema answers registration (and more) with HTTP 500.
apply_migrations() {
  local plan="$LOG_DIR/showmigrations.log" pending
  if ! (cd "$BACKEND_DIR" && "$VENV/bin/python" manage.py showmigrations --plan) >"$plan" 2>&1; then
    grep -v ' DEBUG ' "$plan" | tail -n 30 >&2
    fail "Django could not load its settings or apps (error above)."
  fi
  pending=$(grep -c '^\[ \]' "$plan" || true)
  if [ "$pending" -eq 0 ]; then
    ok "Database schema is up to date"
    return 0
  fi
  if [ "${HMS_SKIP_MIGRATE:-0}" = "1" ]; then
    warn "$pending migrations are not applied (HMS_SKIP_MIGRATE=1); expect HTTP 500 errors."
    return 0
  fi
  backup_database
  info "Applying $pending pending migrations ..."
  if ! (cd "$BACKEND_DIR" && "$VENV/bin/python" manage.py migrate --noinput) >"$LOG_DIR/migrate.log" 2>&1; then
    grep -v ' DEBUG ' "$LOG_DIR/migrate.log" | tail -n 30 >&2
    fail "Migration failed. The backup above holds the database as it was."
  fi
  ok "Applied $pending migrations"
}

wait_for() { # name pid url timeout
  local name=$1 pid=$2 url=$3 limit=$4 waited=0
  while [ "$waited" -lt "$limit" ]; do
    curl -sf -o /dev/null --max-time 2 "$url" && return 0
    if ! pid_alive "$pid"; then
      show_log "$name"
      rm -f "$RUN_DIR/$name.pid"
      fail "The $name exited during startup (its last log lines are above; full log: $LOG_DIR/$name.log)."
    fi
    sleep 1
    waited=$((waited + 1))
  done
  show_log "$name"
  fail "The $name did not answer at $url within ${limit}s (still running as pid $pid; log: $LOG_DIR/$name.log)."
}

start_backend() {
  local holder pid
  holder=$(listener_pid "$BACKEND_PORT")
  if [ -n "$holder" ]; then
    if is_hms_backend "$BACKEND_URL"; then
      ok "Backend already running at $BACKEND_URL: $(describe_pid "$holder")"
      return 0
    fi
    fail "Port $BACKEND_PORT is used by another program, which this script will not stop:
    $(describe_pid "$holder")
  Start on another port instead: HMS_BACKEND_PORT=8010 scripts/dev.sh start"
  fi
  ensure_venv
  check_env_file
  icloud_check
  apply_migrations
  info "Starting Django at $BACKEND_URL ..."
  (cd "$BACKEND_DIR" && exec nohup "$VENV/bin/python" manage.py runserver "$HOST:$BACKEND_PORT") >"$LOG_DIR/backend.log" 2>&1 &
  pid=$!
  echo "$pid" >"$RUN_DIR/backend.pid"
  wait_for backend "$pid" "$BACKEND_URL/health/live/" "$BACKEND_TIMEOUT"
  ok "Backend is up: $BACKEND_URL (pid $pid)"
}

check_proxy() {
  if curl -sf -o /dev/null --max-time 5 "$FRONTEND_URL/health/"; then
    ok "Vite proxy reaches Django ($FRONTEND_URL/api -> $BACKEND_URL)"
    return 0
  fi
  warn "Vite at $FRONTEND_URL cannot reach Django through its proxy (HTTP 502)."
  warn "Start the backend (scripts/dev.sh start backend). If Vite was started with another"
  warn "VITE_PROXY_TARGET, restart it: scripts/dev.sh restart frontend"
  return 1
}

start_frontend() {
  local holder pid
  holder=$(listener_pid "$FRONTEND_PORT")
  if [ -n "$holder" ]; then
    ok "Frontend already running at $FRONTEND_URL: $(describe_pid "$holder")"
    check_proxy
    return
  fi
  if [ ! -x "$ROOT/node_modules/.bin/vite" ]; then
    info "Installing frontend packages (npm ci) ..."
    (cd "$ROOT" && npm ci) || fail "npm ci failed"
  fi
  info "Starting Vite at $FRONTEND_URL (proxy -> $BACKEND_URL) ..."
  (cd "$ROOT" && VITE_PROXY_TARGET="$BACKEND_URL" exec nohup "$ROOT/node_modules/.bin/vite") >"$LOG_DIR/frontend.log" 2>&1 &
  pid=$!
  echo "$pid" >"$RUN_DIR/frontend.pid"
  wait_for frontend "$pid" "$FRONTEND_URL/" "$FRONTEND_TIMEOUT"
  ok "Frontend is up: $FRONTEND_URL (pid $pid)"
  check_proxy
}

# Stops only a process this script started, and only if it is still ours.
stop_one() {
  local name=$1 pattern=$2 pid
  pid=$(read_pid "$name")
  if ! pid_alive "$pid"; then
    rm -f "$RUN_DIR/$name.pid"
    info "The $name was not started by this script; nothing to stop."
    return 0
  fi
  if ! ps -o command= -p "$pid" | grep -q "$pattern"; then
    rm -f "$RUN_DIR/$name.pid"
    warn "pid $pid is no longer the $name; leaving it alone."
    return 0
  fi
  pkill -TERM -P "$pid" 2>/dev/null # runserver's auto-reloader child
  kill -TERM "$pid" 2>/dev/null
  rm -f "$RUN_DIR/$name.pid"
  ok "Stopped the $name (pid $pid)"
}

status() {
  local holder
  holder=$(listener_pid "$BACKEND_PORT")
  if [ -n "$holder" ] && is_hms_backend "$BACKEND_URL"; then
    ok "Backend  $BACKEND_URL  $(describe_pid "$holder")"
  elif [ -n "$holder" ]; then
    warn "Backend port $BACKEND_PORT is held by a non-HMS program: $(describe_pid "$holder")"
  else
    warn "Backend  not running (start: scripts/dev.sh start backend)"
  fi
  holder=$(listener_pid "$FRONTEND_PORT")
  if [ -n "$holder" ]; then
    ok "Frontend $FRONTEND_URL  $(describe_pid "$holder")"
    check_proxy
  else
    warn "Frontend not running (start: scripts/dev.sh start frontend)"
  fi
  info "Logs: $LOG_DIR   Virtualenv: $VENV"
}

summary() {
  echo
  ok "Hospital Automate is running"
  echo "    App:      $FRONTEND_URL"
  echo "    API:      $BACKEND_URL/api/   Health: $BACKEND_URL/health/ready/"
  echo "    Logs:     scripts/dev.sh logs [backend|frontend]"
  echo "    Stop:     scripts/dev.sh stop        Restart one: scripts/dev.sh restart backend"
  echo "    Both servers keep running after this terminal closes; after a reboot run start again."
}

command=${1:-start}
target=${2:-all}
case "$target" in all | backend | frontend) ;; *) fail "Unknown target '$target' (use all, backend or frontend)" ;; esac

case "$command" in
  start)
    [ "$target" = "frontend" ] || start_backend
    [ "$target" = "backend" ] || start_frontend
    if [ "$target" = "all" ]; then summary; fi
    ;;
  stop)
    [ "$target" = "backend" ] || stop_one frontend "vite"
    [ "$target" = "frontend" ] || stop_one backend "manage.py runserver"
    ;;
  restart)
    bash "$ROOT/scripts/dev.sh" stop "$target" && sleep 1 && exec bash "$ROOT/scripts/dev.sh" start "$target"
    ;;
  status) status ;;
  logs)
    [ "$target" = "all" ] && target=backend
    tail -n 40 -f "$LOG_DIR/$target.log" | grep --line-buffered -v ' DEBUG '
    ;;
  setup)
    ensure_venv
    check_env_file
    apply_migrations
    ;;
  migrate)
    ensure_venv
    apply_migrations
    ;;
  *) fail "Unknown command '$command' (use start, stop, restart, status, logs, setup or migrate)" ;;
esac
