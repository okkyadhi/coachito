#!/usr/bin/env bash
# Curl smoke-test for the /curriculum/* endpoints.
#
# Prerequisites:
#   1. Stack running:    docker compose -f infra/docker-compose.yml up -d
#   2. Migrations applied: alembic upgrade head    (run inside `api` container)
#   3. Seed loaded:      python -m scripts.seed   (run inside `api` container)
#   4. Demo workspace seeded: python -m scripts.dev_seed_demo
#
# Usage:
#   bash apps/api/scripts/curl_test_curriculum.sh
#
# Set API_HOST if your API isn't on localhost:8002 (the docker-compose default).

set -euo pipefail

API="${API_HOST:-http://localhost:8002}"

# These emails / slug have to exist in your seed.  Adjust if your demo seed
# uses different identifiers — grep apps/api/scripts/dev_seed_demo.py for the
# exact values.
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@senayan.test}"
COACH_EMAIL="${COACH_EMAIL:-coach@senayan.test}"
SOLO_EMAIL="${SOLO_EMAIL:-solo@coach.test}"
CLUB_SLUG="${CLUB_SLUG:-senayan-padel-club}"
SOLO_SLUG="${SOLO_SLUG:-solo-budi}"

# Pick any platform skill code from your seed.  PADEL_TECH_BANDEJA exists
# in apps/api/data/skills_padel.json by default.
SKILL_CODE="${SKILL_CODE:-PADEL_TECH_BANDEJA}"
TIER_CODE="${TIER_CODE:-TIER_3}"

bold()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
fail()  { printf '  \033[31m✗\033[0m %s\n' "$*"; exit 1; }

need_jq() {
  command -v jq >/dev/null || fail "jq is required — brew install jq"
}
need_jq

login() {
  local email="$1" slug="${2:-}"
  local body
  body=$(jq -nc --arg e "$email" --arg s "$slug" \
    'if $s == "" then {email:$e} else {email:$e, workspace_slug:$s} end')
  curl -fsS -X POST "$API/auth/dev-login" \
    -H 'Content-Type: application/json' \
    -d "$body" | jq -r .access_token
}

bold "1. Mint dev tokens"
ADMIN_JWT=$(login "$ADMIN_EMAIL" "$CLUB_SLUG") && ok "admin token"
COACH_JWT=$(login "$COACH_EMAIL" "$CLUB_SLUG") && ok "coach token"
SOLO_JWT=$(login "$SOLO_EMAIL"  "$SOLO_SLUG")  && ok "solo token"

bold "2. GET /curriculum/skills — admin sees merged list"
curl -fsS -H "Authorization: Bearer $ADMIN_JWT" \
  "$API/curriculum/skills" | jq '.skills[0:3]' && ok "admin list"

bold "3. GET /curriculum/skills — coach also sees it (read-only view)"
curl -fsS -H "Authorization: Bearer $COACH_JWT" \
  "$API/curriculum/skills" | jq '.skills | length' && ok "coach list"

bold "4. PATCH skill — admin disables a skill (201/200 expected)"
curl -fsS -X PATCH \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"is_enabled":false}' \
  "$API/curriculum/skills/$SKILL_CODE" | jq '{code,is_enabled,is_override}' && ok "disable"

bold "5. PATCH skill — coach forbidden (expect 403)"
status=$(curl -s -o /dev/null -w '%{http_code}' -X PATCH \
  -H "Authorization: Bearer $COACH_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"is_enabled":false}' \
  "$API/curriculum/skills/$SKILL_CODE")
[[ "$status" == "403" ]] && ok "coach got 403" || fail "expected 403, got $status"

bold "6. GET impact — count of affected trainees"
curl -fsS -H "Authorization: Bearer $ADMIN_JWT" \
  "$API/curriculum/skills/$SKILL_CODE/impact" | jq && ok "impact"

bold "7. PATCH skill — admin re-enables (override row is dropped)"
curl -fsS -X PATCH \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"is_enabled":true}' \
  "$API/curriculum/skills/$SKILL_CODE" | jq '{code,is_enabled,is_override}' && ok "re-enable"

bold "8. GET tiers — list with overrides merged"
curl -fsS -H "Authorization: Bearer $ADMIN_JWT" \
  "$API/curriculum/tiers" | jq '.tiers | map({code, name_skill_en, name_custom_en, is_override})' \
  && ok "tier list"

bold "9. PATCH tier — admin sets a custom name"
curl -fsS -X PATCH \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"name_custom_en":"Match player","name_custom_id":"Pemain match"}' \
  "$API/curriculum/tiers/$TIER_CODE" | jq '{code, name_custom_en, name_custom_id, is_override}' \
  && ok "rename tier"

bold "10. POST feedback — coach sends note (expect 201)"
curl -fsS -X POST \
  -H "Authorization: Bearer $COACH_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"body":"Bandeja level 3 descriptor is too vague — could we split it?"}' \
  "$API/curriculum/feedback" | jq '{id, body, created_at}' && ok "send feedback"

bold "11. POST feedback — admin forbidden (expect 409)"
status=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"body":"self-send not allowed"}' \
  "$API/curriculum/feedback")
[[ "$status" == "409" ]] && ok "admin got 409" || fail "expected 409, got $status"

bold "12. GET feedback — admin reads inbox"
INBOX=$(curl -fsS -H "Authorization: Bearer $ADMIN_JWT" "$API/curriculum/feedback")
echo "$INBOX" | jq '{unread:.unread_count, count:(.notes|length)}' && ok "inbox"
NOTE_ID=$(echo "$INBOX" | jq -r '.notes[0].id')

bold "13. GET feedback — coach forbidden (expect 403)"
status=$(curl -s -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $COACH_JWT" \
  "$API/curriculum/feedback")
[[ "$status" == "403" ]] && ok "coach got 403" || fail "expected 403, got $status"

bold "14. POST mark-read — admin"
curl -fsS -X POST -H "Authorization: Bearer $ADMIN_JWT" \
  "$API/curriculum/feedback/$NOTE_ID/read" | jq '{id, read_at}' && ok "mark read"

bold "15. Solo workspace — owner writes succeed"
curl -fsS -X PATCH \
  -H "Authorization: Bearer $SOLO_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"is_enabled":false}' \
  "$API/curriculum/skills/$SKILL_CODE" | jq '{code,is_enabled,is_override}' && ok "solo disable"
curl -fsS -X PATCH \
  -H "Authorization: Bearer $SOLO_JWT" \
  -H 'Content-Type: application/json' \
  -d '{"is_enabled":true}' \
  "$API/curriculum/skills/$SKILL_CODE" >/dev/null && ok "solo re-enable"

bold "All curriculum endpoints look healthy ✓"
