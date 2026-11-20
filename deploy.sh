#!/usr/bin/env bash
set -euo pipefail

cd /opt/my-vps

PREV_COMMIT=$(git rev-parse HEAD)
docker tag my-vps-app:latest my-vps-app:rollback 2>/dev/null || true

rollback() {
  echo "Deploy falhou! Executando rollback para $PREV_COMMIT..."
  git reset --hard "$PREV_COMMIT"
  if docker image inspect my-vps-app:rollback >/dev/null 2>&1; then
    docker tag my-vps-app:rollback my-vps-app:latest
    docker compose up -d --no-build
  else
    docker compose up -d --build
  fi
  exit 1
}

trap rollback ERR

git reset --hard origin/deploy

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

docker compose up -d --build

echo "Aguardando inicialização do MyVPS..."
STATUS="000"
for i in $(seq 1 15); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 || echo "000")
  if [ "$STATUS" = "200" ] || [ "$STATUS" = "401" ]; then
    echo "MyVPS saudável (HTTP $STATUS)."
    docker image rm my-vps-app:rollback 2>/dev/null || true
    docker image prune -f
    exit 0
  fi
  sleep 2
done

echo "Healthcheck falhou após 30s (HTTP $STATUS)."
false
