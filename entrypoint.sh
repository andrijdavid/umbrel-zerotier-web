#!/bin/sh
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Read the daemon token as root before dropping privileges.
# authtoken.secret is created by zerotier with mode 0600 (root-owned).
if [ -n "$ZT_AUTHTOKEN_PATH" ] && [ -f "$ZT_AUTHTOKEN_PATH" ]; then
    ZT_AUTHTOKEN="$(cat "$ZT_AUTHTOKEN_PATH")"
    export ZT_AUTHTOKEN
fi

exec su-exec "${PUID}:${PGID}" "$@"
