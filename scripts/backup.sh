#!/usr/bin/env bash
# Backs up the RBM TASK Postgres database and MinIO files.
# Run from the repo root (where docker-compose.yml lives), or via cron with an absolute path.
#
# Usage: ./scripts/backup.sh
# Env overrides: BACKUP_DIR, RETENTION_DAYS, POSTGRES_CONTAINER, MINIO_CONTAINER,
#                POSTGRES_USER, POSTGRES_DB, RCLONE_REMOTE (optional off-site copy)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/rbm-task}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-rbm_postgres}"
MINIO_CONTAINER="${MINIO_CONTAINER:-rbm_minio}"
POSTGRES_USER="${POSTGRES_USER:-rbm}"
POSTGRES_DB="${POSTGRES_DB:-rbmtask}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Iniciando backup em $BACKUP_DIR"

DB_BACKUP_FILE="$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$DB_BACKUP_FILE"
echo "[$(date)] Banco salvo em $DB_BACKUP_FILE"

MINIO_BACKUP_FILE="$BACKUP_DIR/minio_${TIMESTAMP}.tar.gz"
docker run --rm --volumes-from "$MINIO_CONTAINER" -v "$BACKUP_DIR:/backup" alpine \
  tar czf "/backup/minio_${TIMESTAMP}.tar.gz" -C / data
echo "[$(date)] Arquivos MinIO salvos em $MINIO_BACKUP_FILE"

if [ -n "${RCLONE_REMOTE:-}" ]; then
  rclone copy "$DB_BACKUP_FILE" "$RCLONE_REMOTE" && rclone copy "$MINIO_BACKUP_FILE" "$RCLONE_REMOTE"
  echo "[$(date)] Cópia externa enviada para $RCLONE_REMOTE"
else
  echo "[$(date)] RCLONE_REMOTE não configurado — backup ficou só local (regra 3-2-1 incompleta, veja o README)"
fi

echo "[$(date)] Removendo backups locais com mais de $RETENTION_DAYS dias"
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name "minio_*.tar.gz" -mtime "+$RETENTION_DAYS" -delete

echo "[$(date)] Backup concluído com sucesso"
