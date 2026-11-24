#!/bin/bash
set -e
MSG="${1:-Update project}"
mkdir -p backups
docker compose exec -T web tar -czf - -C /app data integrations.txt > "backups/backup_$(date +%F_%H-%M).tar.gz"
git add .
git commit -m "$MSG" || echo "Нет новых изменений для коммита"
git push
echo "✓ Бэкап сохранён в backups/ и код отправлен на GitHub!"
