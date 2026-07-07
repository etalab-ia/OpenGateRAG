#!/usr/bin/env bash
set -euo pipefail

login_token="$(
  curl -sf -X POST "http://localhost:8000/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin","password":"changeme"}' \
    | jq -r '.value // .key'
)"

admin_api_key="$(
  curl -sf -X POST "http://localhost:8000/v1/me/keys" \
    -H "Authorization: Bearer ${login_token}" \
    -H "Content-Type: application/json" \
    -d '{"name":"e2e-admin-key"}' \
    | jq -r '.key // .token'
)"

router_id="$(
  curl -sf "http://localhost:8000/v1/admin/routers?limit=100" \
    -H "Authorization: Bearer ${admin_api_key}" \
    | jq -r '.data[] | select(.name == "BAAI/bge-m3") | .id' \
    | head -n1
)"

role_id="$(
  curl -sf -X POST "http://localhost:8000/v1/admin/roles" \
    -H "Authorization: Bearer ${admin_api_key}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"user\",\"permissions\":[],\"limits\":[{\"router_id\":${router_id},\"type\":\"tpm\",\"value\":0}]}" \
    | jq -r '.id'
)"

user_id="$(
  curl -sf -X POST "http://localhost:8000/v1/admin/users" \
    -H "Authorization: Bearer ${admin_api_key}" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"user\",\"name\":\"user\",\"password\":\"changeme\",\"role\":${role_id}}" \
    | jq -r '.id'
)"

user_api_key="$(
  curl -sf -X POST "http://localhost:8000/v1/admin/tokens" \
    -H "Authorization: Bearer ${admin_api_key}" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"e2e-user-key\",\"user\":${user_id}}" \
    | jq -r '.key // .token'
)"

{
  echo "OPENGATELLM_ADMIN_API_KEY=${admin_api_key}"
  echo "OPENGATELLM_USER_API_KEY=${user_api_key}"
} >>"${GITHUB_ENV:-/dev/stdout}"
