#!/usr/bin/env bash
# Public-facing checks for a deployed stack, run from a machine OUTSIDE the
# server (a laptop or CI runner), so that closed ports are seen as the
# internet sees them.
#
#   scripts/deploy/verify_public.sh staging.your-hospital.org
#
# A real staging rehearsal passes with no options: the certificate must chain
# to a CA your system trusts. For a LOCAL rehearsal only:
#   HMS_CONNECT_IP=127.0.0.1   connect to this address instead of DNS
#   HMS_CA_FILE=path/ca.pem    trust this private CA (marks the run LOCAL)
# Exits non-zero if any check failed.
set -uo pipefail

DOMAIN=${1:?usage: verify_public.sh DOMAIN}
CONNECT_IP=${HMS_CONNECT_IP:-}
CA_FILE=${HMS_CA_FILE:-}
FAILED=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAILED=1; }
check() { local name=$1; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

CURL=(curl -sS --max-time 15)
if [ -n "$CONNECT_IP" ]; then
  CURL+=(--resolve "$DOMAIN:443:$CONNECT_IP" --resolve "$DOMAIN:80:$CONNECT_IP")
fi
[ -n "$CA_FILE" ] && CURL+=(--cacert "$CA_FILE")
TARGET=${CONNECT_IP:-$DOMAIN}

if [ -n "$CA_FILE" ] || [ -n "$CONNECT_IP" ]; then
  echo "NOTE: LOCAL mode (private CA or fixed address). This is NOT a real staging verification."
fi

headers() { "${CURL[@]}" -o /dev/null -D - "$1" | tr -d '\r'; }
status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }

# 1. Certificate: verified chain, matching name, not expiring within 14 days.
check "TLS certificate verifies for $DOMAIN" "${CURL[@]}" -o /dev/null "https://$DOMAIN/health/live/"
expiry=$(echo | openssl s_client -connect "$TARGET:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$expiry" ]; then
  check "certificate valid for 14+ more days (expires $expiry)" \
    bash -c 'echo | openssl s_client -connect "$1:443" -servername "$2" 2>/dev/null | openssl x509 -noout -checkend 1209600 >/dev/null' _ "$TARGET" "$DOMAIN"
  issuer=$(echo | openssl s_client -connect "$TARGET:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null)
  echo "INFO  $issuer"
else
  fail "could not read the certificate from $TARGET:443"
fi
check "TLS 1.0/1.1 refused" bash -c '! echo | openssl s_client -connect "$1:443" -servername "$2" -tls1_1 >/dev/null 2>&1' _ "$TARGET" "$DOMAIN"

# 2. HTTP redirects to HTTPS on the same host name.
loc=$(headers "http://$DOMAIN/some/path?x=1" | awk -F': ' 'tolower($1)=="location"{print $2}')
check "HTTP -> HTTPS redirect (Location: $loc)" test "$loc" = "https://$DOMAIN/some/path?x=1"

# 3. Security headers on the app shell and on the API.
for path in / /api/ /health/live/; do
  h=$(headers "https://$DOMAIN$path")
  for header in "strict-transport-security: max-age=" "content-security-policy:" "x-frame-options: deny" \
                "x-content-type-options: nosniff" "referrer-policy:"; do
    check "$path sends ${header%%:*}" grep -qi "^$header" <<<"$h"
  done
  check "$path hides the nginx version" bash -c '! grep -qiE "^server: nginx/[0-9]" <<<"$1"' _ "$h"
done

# 4. Application endpoints.
check "/health/ready/ is 200" test "$(status "https://$DOMAIN/health/ready/")" = 200
check "/media/ is never served directly (404)" test "$(status "https://$DOMAIN/media/documents/x.pdf")" = 404
code=$(status "https://$DOMAIN/api/schema/")
check "/api/schema/ needs a platform-admin sign-in ($code)" bash -c '[ "$1" = 401 ] || [ "$1" = 403 ]' _ "$code"
code=$(status -H "Content-Type: application/json" -d '{}' "https://$DOMAIN/api/auth/staff/login/")
check "staff login endpoint answers JSON errors, not 5xx ($code)" bash -c '[ "$1" -ge 400 ] && [ "$1" -lt 500 ]' _ "$code"

# 5. Unknown host names are dropped before Django.
code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -H "Host: not-$DOMAIN" "http://$TARGET/" 2>/dev/null)
check "unknown Host on port 80 gets no response ($code)" test "$code" = 000

# 6. Only 80 and 443 are open from outside. Meaningless from the server itself
# (loopback ports are open there by design), so skipped for a loopback target.
case "$TARGET" in
  127.*|localhost|::1) echo "SKIP  closed-port checks: target is loopback; run this from another machine" ;;
  *)
    for port in 5432 6379 8000 5555; do
      check "port $port closed from here" bash -c '! (exec 3<>"/dev/tcp/$1/$2") 2>/dev/null' _ "$TARGET" "$port"
    done
    ;;
esac

echo
if [ "$FAILED" -eq 0 ]; then echo "All public checks passed."; else echo "Some public checks FAILED."; fi
exit "$FAILED"
