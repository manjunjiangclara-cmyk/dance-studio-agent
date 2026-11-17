#!/bin/bash
set -euo pipefail
umask 077
if [ "${STUDIO_RELEASE_LOCKED:-}" != 1 ]; then
    exec 9>/run/lock/studio-deployment.lock
    flock -n 9 || { echo 'Another release or backup is running'; exit 1; }
    export STUDIO_RELEASE_LOCKED=1
fi
SHA=$1
CHECKSUM=$2
[[ "$SHA" =~ ^[0-9a-f]{40}$ && "$CHECKSUM" =~ ^[0-9a-f]{64}$ ]]
mountpoint -q /srv/studio
test -f /srv/studio/host-ready
studio-host download "$SHA" "$CHECKSUM"
RELEASE=/srv/studio/releases/$SHA
# Validated release archives also deliver host fixes; cloud-init runs only once.
if [ "${STUDIO_RELEASE_HELPERS:-}" != "$SHA" ]; then
    install -m 700 "$RELEASE/deployment/ec2/host.py" /usr/local/bin/studio-host
    install -m 700 "$RELEASE/deployment/ec2/verify_restore.py" /usr/local/bin/studio-verify-restore
    install -m 700 "$RELEASE/deployment/ec2/backup.sh" /usr/local/bin/studio-backup
    install -m 700 "$RELEASE/deployment/ec2/release.sh" /usr/local/bin/studio-release
    export STUDIO_RELEASE_HELPERS=$SHA
    exec /usr/local/bin/studio-release "$SHA" "$CHECKSUM"
fi
studio-host configure
IMAGE=studio-copilot:$SHA
export STUDIO_IMAGE=$IMAGE
export STUDIO_DOMAIN
STUDIO_DOMAIN=$(cat /srv/studio/config/domain)
compose() { docker compose --env-file /srv/studio/config/app.env -f "$RELEASE/deployment/ec2/compose.yaml" "$@"; }
# Secret files are outside the image build context.
if ! docker buildx version >/dev/null 2>&1; then
    apt-get -o Acquire::Retries=3 update -qq
    apt-get -o Acquire::Retries=3 install -y docker-buildx
fi
if ! docker buildx inspect studio-application >/dev/null 2>&1; then
    docker buildx create --name studio-application --driver docker-container
fi
# Bootstrap creates the dedicated builder container before its first prune.
docker buildx inspect --bootstrap studio-application
# Scope cache retention to this application's builder.
docker buildx prune --builder studio-application --force --keep-storage 3GB
docker buildx build --builder studio-application --load --pull --tag "$IMAGE" --file "$RELEASE/deployment/ec2/Dockerfile" "$RELEASE"
if [ ! -f /srv/studio/policy/studio.yaml ]; then
    install -o 10001 -g 10001 -m 600 "$RELEASE/backend/policies/studio.yaml" /srv/studio/policy/studio.yaml
fi
PREVIOUS=$(studio-host current)
if [ -n "$PREVIOUS" ]; then studio-backup --locked; fi
compose up -d --wait db
# Keep the previous image and backup. Database downgrades are never automatic.
FAILED=1
failed_release() {
    if [ "$FAILED" = 1 ]; then
        compose stop app proxy || true
        printf 'failed %s\n' "$SHA" > /srv/studio/deployment-status
        echo 'Release failed and stopped. Use the retained backup/prior image after checking schema compatibility.'
    fi
}
trap failed_release EXIT
printf 'deploying %s\n' "$SHA" > /srv/studio/deployment-status
compose stop app proxy
compose run --rm --no-deps app alembic upgrade head
compose run --rm --no-deps app alembic check
compose run --rm --no-deps app python -m studio_copilot.agent.persistence.checkpoints
# A newly provisioned demo uses fictional fixtures; subsequent releases preserve edits.
if [ ! -f /srv/studio/initialized ]; then
    compose run --rm --no-deps app python -m studio_copilot.demo
fi
compose up -d --wait --wait-timeout 180
# Verify more than the shallow database health check, without making model calls.
compose exec -T app python - <<'PY'
import json
import urllib.request
from studio_copilot.documents.chunking import Tokenizer
from studio_copilot.documents.reranking.runtime import verify_model
from pathlib import Path
Tokenizer(Path('/app/assets/tokenizer'))
verify_model('/app/assets/reranker', 'cross-encoder/ms-marco-MiniLM-L6-v2')
for path in ('/health', '/demo', '/workspace', '/auth/me'):
    with urllib.request.urlopen('http://localhost:8000' + path, timeout=10) as response:
        body = response.read()
        if path == '/auth/me':
            assert json.loads(body)['login_available'] is True
PY
if [ -n "$PREVIOUS" ]; then ln -sfn "$PREVIOUS" /srv/studio/previous; fi
ln -sfn "$RELEASE" /srv/studio/current
printf 'ready %s\n' "$SHA" > /srv/studio/deployment-status
printf '%s\n' "$SHA" > /srv/studio/initialized
# Keep only deployment-owned current/previous images; never prune other projects.
for image in $(docker images studio-copilot --format '{{.Repository}}:{{.Tag}}'); do
    if [ "$image" != "$IMAGE" ] && [ "$image" != "studio-copilot:$(basename "${PREVIOUS:-none}")" ]; then
        docker image rm "$image" || true
    fi
done
FAILED=0
echo "Release ready: $SHA"
