#!/usr/bin/env bash
# On-host checks for a running docker-compose.prod.yml stack (staging or
# production). Run from the repository root on the Docker host after `up -d`.
# Prints PASS/FAIL per check and exits non-zero if any check failed.
#
#   scripts/deploy/verify_host.sh
#
# Public-facing checks (certificate, redirects, headers, closed ports seen from
# outside) are in scripts/deploy/verify_public.sh.
set -uo pipefail

ENV_FILE=${ENV_FILE:-.env.production}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
dc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

FAILED=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAILED=1; }
check() { local name=$1; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

container() { dc ps -q "$1"; }
health() { docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$(container "$1")" 2>/dev/null; }
env_of() { docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$(container "$1")"; }
ports_of() { docker inspect -f '{{range $p, $b := .NetworkSettings.Ports}}{{range $b}}{{$p}}={{.HostIp}}:{{.HostPort}} {{end}}{{end}}' "$(container "$1")"; }

# 1. Every service is up, and healthy where it has a health check.
for svc in postgres redis backend celery-worker frontend nginx; do
  state=$(health "$svc")
  check "service $svc is healthy ($state)" test "$state" = healthy
done
state=$(health celery-beat)
check "service celery-beat is running ($state)" test "$state" = running

# 2. Effective Django settings in the running backend.
SETTINGS_PY='
from django.conf import settings as s
from ai_scribe.services.llm import LLMClinicalService
from ai_scribe.services.stt import SpeechToTextService
print("DEBUG", s.DEBUG)
print("MOCK_ALLOWED", s.AI_SCRIBE_ALLOW_MOCK_PROVIDERS)
print("MOCK_LLM_REGISTERED", "development" in LLMClinicalService()._providers)
print("MOCK_STT_REGISTERED", "development" in SpeechToTextService()._providers)
print("SSL_REDIRECT", s.SECURE_SSL_REDIRECT)
print("SECURE_COOKIES", s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE and s.AUTH_COOKIE_SECURE)
print("HSTS", s.SECURE_HSTS_SECONDS > 0)
print("DEV_LOGIN", s.DEV_LOGIN_ENABLED)
print("WILDCARD_HOST", "*" in s.ALLOWED_HOSTS)
'
out=$(dc exec -T backend python manage.py shell -c "$SETTINGS_PY" 2>/dev/null)
want() { grep -qx "$1 $2" <<<"$out"; }
check "DEBUG is False" want DEBUG False
check "mock AI providers disallowed by settings" want MOCK_ALLOWED False
check "no mock LLM provider registered" want MOCK_LLM_REGISTERED False
check "no mock STT provider registered" want MOCK_STT_REGISTERED False
check "HTTPS redirect on" want SSL_REDIRECT True
check "session, CSRF and auth cookies are Secure" want SECURE_COOKIES True
check "HSTS enabled" want HSTS True
check "development sign-in off" want DEV_LOGIN False
check "ALLOWED_HOSTS has no wildcard" want WILDCARD_HOST False

# 3. Django's own deployment checks and migration state.
check "manage.py check --deploy" dc exec -T backend python manage.py check --deploy --fail-level WARNING
unapplied=$(dc exec -T backend python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]')
check "no unapplied migrations ($unapplied)" test "$unapplied" -eq 0

# 4. Only the backend container migrates.
check "backend has RUN_MIGRATIONS=true" grep -qx 'RUN_MIGRATIONS=true' <(env_of backend)
for svc in celery-worker celery-beat; do
  check "$svc does not migrate" bash -c "! grep -qx 'RUN_MIGRATIONS=true' <<<\"\$1\"" _ "$(env_of "$svc")"
  check "$svc log shows migrate skipped" bash -c 'grep -q "skipping migrate" <<<"$1"' _ "$(dc logs --no-log-prefix "$svc" 2>&1 | head -50)"
done

# 5. Database and Redis are not published beyond loopback.
check "postgres published on 127.0.0.1 only ($(ports_of postgres))" \
  bash -c '[ -z "$1" ] || ! grep -qvE "=127\.0\.0\.1:" <<<"$(tr " " "\n" <<<"$1" | grep .)"' _ "$(ports_of postgres)"
check "redis has no published port" test -z "$(ports_of redis)"
check "backend published on 127.0.0.1 only ($(ports_of backend))" \
  bash -c '[ -z "$1" ] || ! grep -qvE "=127\.0\.0\.1:" <<<"$(tr " " "\n" <<<"$1" | grep .)"' _ "$(ports_of backend)"
check "redis refuses unauthenticated clients" \
  bash -c 'docker exec -e REDISCLI_AUTH= "$1" redis-cli ping 2>&1 | grep -q NOAUTH' _ "$(container redis)"

# 6. Container logs rotate.
for svc in backend nginx postgres; do
  max=$(docker inspect -f '{{index .HostConfig.LogConfig.Config "max-size"}}' "$(container "$svc")")
  check "$svc log rotation (max-size=$max)" test -n "$max"
done

# 7. Readiness through the app itself.
check "/health/ready/ reports database and cache healthy" bash -c \
  'docker exec "$1" sh -c "curl -fsS -H \"Host: \${ALLOWED_HOSTS%%,*}\" http://localhost:8000/health/ready/" | grep -q "\"database\": \"healthy\", \"cache\": \"healthy\""' \
  _ "$(container backend)"

echo
if [ "$FAILED" -eq 0 ]; then echo "All on-host checks passed."; else echo "Some on-host checks FAILED."; fi
exit "$FAILED"
