#!/usr/bin/env bash
set -euo pipefail

NETWORK="${FORGE_DOCKER_NETWORK:-bridge}"
FORGE_HOST="${FORGE_DOCKER_HOST:-forge}"
FORGE_PORT="${FORGE_DOCKER_PORT:-2222}"
SECRETS_DIR="./secrets"
KEY_PATH="${SECRETS_DIR}/forge_deploy_key"
KNOWN_HOSTS_PATH="${SECRETS_DIR}/forge_known_hosts"

mkdir -p "${SECRETS_DIR}"
chmod 700 "${SECRETS_DIR}"

if [[ -e "${KEY_PATH}" || -e "${KEY_PATH}.pub" ]]; then
  echo "Deploy key already exists at ${KEY_PATH}; refusing to overwrite." >&2
  exit 1
fi

ssh-keygen -t ed25519 -N "" -C "forge-ingest@local" -f "${KEY_PATH}"
chmod 600 "${KEY_PATH}"
chmod 644 "${KEY_PATH}.pub"

echo
echo "Public deploy key. Paste this into your Git forge as a read-only deploy key on each repo forge-ingest may read:"
echo
cat "${KEY_PATH}.pub"
echo

tmp_hosts="$(mktemp)"
docker run --rm --network "${NETWORK}" alpine:3.20 sh -c \
  "apk add --no-cache openssh-client >/dev/null && ssh-keyscan -p ${FORGE_PORT} ${FORGE_HOST}" > "${tmp_hosts}"

echo "Forge SSH host key fingerprints seen from Docker network ${NETWORK}:"
ssh-keygen -lf "${tmp_hosts}"
read -r -p "Type yes after verifying these fingerprints with the forge administrator: " answer
if [[ "${answer}" != "yes" ]]; then
  rm -f "${tmp_hosts}"
  echo "Host key not confirmed; known_hosts not written." >&2
  exit 1
fi

mv "${tmp_hosts}" "${KNOWN_HOSTS_PATH}"
chmod 644 "${KNOWN_HOSTS_PATH}"
echo "Pinned host key written to ${KNOWN_HOSTS_PATH}."
