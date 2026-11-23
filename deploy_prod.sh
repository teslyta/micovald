#!/bin/bash
set -e
DOMAIN="${1:-micovald.ru}"
echo "=== Развёртывание MICOVALD на боевом сервере для домена: $DOMAIN ==="

if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://docker.com | sh
fi
systemctl enable docker && systemctl start docker

cat << CADDY > Caddyfile
$DOMAIN, www.$DOMAIN {
    reverse_proxy web:8000
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }
}
CADDY

chmod 600 integrations.txt data/users.json 2>/dev/null || true
chmod +x start.sh
./start.sh
echo "=== УСПЕШНО! Сайт доступен по адресу: https://$DOMAIN ==="
