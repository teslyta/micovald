#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

mkdir -p data media/products media/about
[ -f integrations.txt ] || printf "YOOKASSA_SHOP_ID=\nYOOKASSA_SECRET_KEY=\nPOCHTA_WIDGET_ID=\nPOCHTA_API_TOKEN=\nVK_SERVICE_TOKEN=\nVK_GROUP_DOMAIN=\n" > integrations.txt

docker compose up -d
sleep 2
docker compose exec -T web python3 -c "from security import load_users; load_users()" >/dev/null 2>&1 || true
docker compose exec -T web python3 /app/test_site.py

echo "=== Сайт MICOVALD запущен: http://localhost:8888 ==="
docker compose ps
