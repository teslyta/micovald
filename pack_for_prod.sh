#!/bin/bash
set -e
echo "=== 1. Очистка кэша и упаковка чистого пакета для боевого сервера ==="
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
cd .. && tar --exclude='mikovald/backups/*.tar.gz' -czf micovald_prod.tar.gz mikovald/
echo "✓ Готово! Архив создан: ~/micovald_prod.tar.gz"
