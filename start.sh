#!/bin/bash
set -e
docker compose up -d --build
docker compose exec -T web python3 /app/test_site.py
echo "=== Сайт MICOVALD запущен: https://localhost:8888 ==="
docker compose ps
