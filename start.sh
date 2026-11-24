#!/bin/bash
set -e
docker compose up -d --build
if [ ! -f /usr/local/share/ca-certificates/caddy-local.crt ] && grep -q "localhost" Caddyfile; then
    docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt /tmp/caddy-local.crt 2>/dev/null || true
    if [ -f /tmp/caddy-local.crt ]; then
        sudo mv /tmp/caddy-local.crt /usr/local/share/ca-certificates/caddy-local.crt && sudo update-ca-certificates >/dev/null 2>&1 || true
        sudo mkdir -p /etc/firefox/policies && echo '{"policies":{"Certificates":{"ImportEnterpriseRoots":true}}}' | sudo tee /etc/firefox/policies/policies.json >/dev/null 2>&1 || true
    fi
fi
docker compose exec -T web python3 /app/test_site.py
echo "=== Сайт MICOVALD запущен: https://localhost:8888 ==="
docker compose ps
