#!/bin/bash
set -euo pipefail
umask 077
if [ "${1:-}" != --locked ]; then
    exec 9>/run/lock/studio-deployment.lock
    flock -n 9 || { echo 'Another release or backup is running'; exit 1; }
fi
mountpoint -q /srv/studio
RELEASE=$(studio-host current)
test -n "$RELEASE"
export STUDIO_IMAGE=studio-copilot:$(basename "$RELEASE")
export STUDIO_DOMAIN
STUDIO_DOMAIN=$(python3 -c 'import json; print(json.load(open("/etc/studio-host.json"))["domain"])')
compose() { docker compose --env-file /srv/studio/config/app.env -f "$RELEASE/deployment/ec2/compose.yaml" "$@"; }
STAMP=$(date -u +%Y%m%dT%H%M%S)-$(cat /proc/sys/kernel/random/uuid)
TEMP=$(mktemp -d /srv/studio/backups/.backup-XXXXXX)
WAS_RUNNING=$(compose ps --status running --services | grep -x app || true)
cleanup() {
    if [ -n "$WAS_RUNNING" ]; then compose start app; fi
    rm -rf "$TEMP"
}
trap cleanup EXIT
compose stop app
compose exec -T db pg_dump --username=copilot --dbname=studio_copilot --format=custom > "$TEMP/database.dump"
studio-host snapshot "$TEMP"
printf '%s\n' "$(basename "$RELEASE")" > "$TEMP/release.txt"
ARCHIVE=/srv/studio/backups/$STAMP.tar.gz
tar -C "$TEMP" -czf "$ARCHIVE" .
studio-host upload "$ARCHIVE" "backups/$STAMP.tar.gz"
# Remove local backups only after successful off-host upload; retain the newest week.
find /srv/studio/backups -maxdepth 1 -type f -name '*.tar.gz' -mtime +7 -delete
echo "Backup uploaded: $STAMP"
