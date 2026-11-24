#!/bin/bash
set -e
DOMAIN="${1:-micovald.ru}"
EMAIL="${2:-micovald@yandex.ru}"
echo "=== Развёртывание MICOVALD на боевом сервере: https://$DOMAIN ==="

if ! command -v docker &> /dev/null; then
    curl -fsSL https://docker.com | sh
fi
systemctl enable docker && systemctl start docker

if command -v ufw &> /dev/null; then
    ufw allow 80/tcp >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
fi

cat << CADDY > Caddyfile
{
    email $EMAIL
}
$DOMAIN, www.$DOMAIN {
    reverse_proxy web:8000
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }
}
CADDY

sed -i 's/"8888:443"/"443:443"/g' docker-compose.yml
grep -q '"80:80"' docker-compose.yml || sed -i 's/"443:443"/"80:80"\n      - "443:443"/g' docker-compose.yml

chmod 600 integrations.txt data/users.json 2>/dev/null || true
chmod +x start.sh
./start.sh
echo "=== ГОТОВО! Официальный SSL-сертификат Let's Encrypt активен для всех посетителей: https://$DOMAIN ==="
